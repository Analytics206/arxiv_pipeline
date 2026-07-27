"""Small, reproducible evaluation harness for agent-oriented retrieval."""

from __future__ import annotations

import json
import math
from pathlib import Path
from time import perf_counter
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.retrieval.models import (
    ResearchPointKind,
    ResearchSearchResponse,
)


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetrievalEvaluationCase(EvaluationModel):
    case_id: str
    query: str
    case_type: Literal["positive", "negative"] = "positive"
    scope: Literal["paper", "corpus", "cross-paper", "negative"] = "paper"
    paper_id: str | None = None
    kinds: list[ResearchPointKind] | None = None
    limit: int = Field(default=5, ge=1, le=50)
    expected_evidence_ids: list[str] = Field(default_factory=list)
    expected_evidence_groups: list[list[str]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    note: str | None = None

    @model_validator(mode="after")
    def validate_relevance_judgment(self) -> "RetrievalEvaluationCase":
        groups = self.relevance_groups
        if self.case_type == "positive" and not groups:
            raise ValueError(
                "Positive cases require expected_evidence_ids or "
                "expected_evidence_groups"
            )
        if self.case_type == "negative" and groups:
            raise ValueError("Negative cases cannot declare expected evidence")
        if any(not group for group in self.expected_evidence_groups):
            raise ValueError("Evidence relevance groups cannot be empty")
        return self

    @property
    def relevance_groups(self) -> list[list[str]]:
        if self.expected_evidence_groups:
            return self.expected_evidence_groups
        if self.expected_evidence_ids:
            # The v1 format treated these IDs as acceptable alternatives.
            return [self.expected_evidence_ids]
        return []


class RetrievalEvaluationSuite(EvaluationModel):
    suite_id: str
    description: str
    document_hash: str | None = None
    document_hashes: dict[str, str] = Field(default_factory=dict)
    cases: list[RetrievalEvaluationCase] = Field(min_length=1)


class RetrievalCaseResult(EvaluationModel):
    case_id: str
    query: str
    case_type: Literal["positive", "negative"]
    scope: Literal["paper", "corpus", "cross-paper", "negative"]
    relevant: bool
    first_relevant_rank: int | None
    first_relevant_score: float | None
    reciprocal_rank: float
    expected_group_count: int
    retrieved_group_count: int
    relevant_group_ranks: list[int | None] = Field(default_factory=list)
    group_recall_at_limit: float | None
    all_groups_retrieved: bool | None
    latency_ms: float
    returned_hits: int
    provenance_complete_hits: int
    top_point_ids: list[str]
    top_paper_ids: list[str]
    top_scores: list[float]
    top_evidence_ids: list[list[str]]


class RetrievalEvaluationReport(EvaluationModel):
    contract: str = "research-retrieval-evaluation"
    suite_id: str
    embedding_model: str
    retrieval_mode: Literal["dense", "hybrid"] = "dense"
    score_semantics: Literal["cosine_similarity", "rrf"] = "cosine_similarity"
    case_count: int
    positive_case_count: int
    negative_case_count: int
    recall_at_limit: float
    mean_reciprocal_rank: float
    group_recall_at_limit: float
    full_group_recall_at_limit: float
    group_recall_at_5: float = 0.0
    group_recall_at_8: float = 0.0
    full_group_recall_at_5: float = 0.0
    full_group_recall_at_8: float = 0.0
    provenance_completeness: float
    mean_latency_ms: float
    p95_latency_ms: float
    mean_first_relevant_score: float | None
    mean_negative_top_score: float | None
    score_separation: float | None
    cases: list[RetrievalCaseResult]


class SearchableResearchIndex(Protocol):
    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        paper_id: str | None = None,
        kinds: list[ResearchPointKind] | None = None,
    ) -> ResearchSearchResponse: ...


def load_evaluation_suite(path: str | Path) -> RetrievalEvaluationSuite:
    return RetrievalEvaluationSuite.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def evaluate_retrieval(
    index: SearchableResearchIndex,
    suite: RetrievalEvaluationSuite,
) -> RetrievalEvaluationReport:
    results: list[RetrievalCaseResult] = []
    embedding_model: str | None = None
    retrieval_mode: Literal["dense", "hybrid"] | None = None
    score_semantics: Literal["cosine_similarity", "rrf"] | None = None
    total_hits = 0
    provenance_complete_hits = 0

    for case in suite.cases:
        started = perf_counter()
        response = index.search(
            case.query,
            limit=case.limit,
            paper_id=case.paper_id,
            kinds=case.kinds,
        )
        latency_ms = (perf_counter() - started) * 1000
        embedding_model = embedding_model or response.embedding_model
        retrieval_mode = retrieval_mode or response.retrieval_mode
        score_semantics = score_semantics or response.score_semantics
        relevance_groups = [set(group) for group in case.relevance_groups]
        expected = set().union(*relevance_groups) if relevance_groups else set()
        first_relevant_rank = next(
            (
                rank
                for rank, hit in enumerate(response.hits, start=1)
                if expected.intersection(hit.evidence_ids)
            ),
            None,
        )
        first_relevant_score = (
            float(response.hits[first_relevant_rank - 1].score)
            if first_relevant_rank is not None
            else None
        )
        relevant_group_ranks = [
            next(
                (
                    rank
                    for rank, hit in enumerate(response.hits, start=1)
                    if group.intersection(hit.evidence_ids)
                ),
                None,
            )
            for group in relevance_groups
        ]
        retrieved_group_count = sum(rank is not None for rank in relevant_group_ranks)
        expected_group_count = len(relevance_groups)
        group_recall = (
            retrieved_group_count / expected_group_count
            if expected_group_count
            else None
        )
        complete_count = sum(_has_complete_provenance(hit) for hit in response.hits)
        total_hits += len(response.hits)
        provenance_complete_hits += complete_count
        results.append(
            RetrievalCaseResult(
                case_id=case.case_id,
                query=case.query,
                case_type=case.case_type,
                scope=case.scope,
                relevant=first_relevant_rank is not None,
                first_relevant_rank=first_relevant_rank,
                first_relevant_score=first_relevant_score,
                reciprocal_rank=(
                    1 / first_relevant_rank if first_relevant_rank else 0.0
                ),
                expected_group_count=expected_group_count,
                retrieved_group_count=retrieved_group_count,
                relevant_group_ranks=relevant_group_ranks,
                group_recall_at_limit=group_recall,
                all_groups_retrieved=(
                    retrieved_group_count == expected_group_count
                    if expected_group_count
                    else None
                ),
                latency_ms=round(latency_ms, 3),
                returned_hits=len(response.hits),
                provenance_complete_hits=complete_count,
                top_point_ids=[hit.point_id for hit in response.hits],
                top_paper_ids=[hit.paper_id for hit in response.hits],
                top_scores=[round(float(hit.score), 6) for hit in response.hits],
                top_evidence_ids=[hit.evidence_ids for hit in response.hits],
            )
        )

    case_count = len(results)
    positive_results = [result for result in results if result.case_type == "positive"]
    negative_results = [result for result in results if result.case_type == "negative"]
    positive_count = len(positive_results)
    group_count = sum(result.expected_group_count for result in positive_results)
    first_relevant_scores = [
        result.first_relevant_score
        for result in positive_results
        if result.first_relevant_score is not None
    ]
    negative_top_scores = [
        result.top_scores[0] for result in negative_results if result.top_scores
    ]
    mean_first_relevant_score = _mean(first_relevant_scores)
    mean_negative_top_score = _mean(negative_top_scores)
    latencies = [result.latency_ms for result in results]
    return RetrievalEvaluationReport(
        suite_id=suite.suite_id,
        embedding_model=embedding_model or "unknown",
        retrieval_mode=retrieval_mode or "dense",
        score_semantics=score_semantics or "cosine_similarity",
        case_count=case_count,
        positive_case_count=positive_count,
        negative_case_count=len(negative_results),
        recall_at_limit=(
            sum(result.relevant for result in positive_results) / positive_count
            if positive_count
            else 0.0
        ),
        mean_reciprocal_rank=(
            sum(result.reciprocal_rank for result in positive_results) / positive_count
            if positive_count
            else 0.0
        ),
        group_recall_at_limit=(
            sum(result.retrieved_group_count for result in positive_results)
            / group_count
            if group_count
            else 0.0
        ),
        full_group_recall_at_limit=(
            sum(result.all_groups_retrieved is True for result in positive_results)
            / positive_count
            if positive_count
            else 0.0
        ),
        group_recall_at_5=_group_recall_at(positive_results, 5),
        group_recall_at_8=_group_recall_at(positive_results, 8),
        full_group_recall_at_5=_full_group_recall_at(
            positive_results,
            5,
        ),
        full_group_recall_at_8=_full_group_recall_at(
            positive_results,
            8,
        ),
        provenance_completeness=(
            provenance_complete_hits / total_hits if total_hits else 0.0
        ),
        mean_latency_ms=_mean(latencies) or 0.0,
        p95_latency_ms=_percentile(latencies, 0.95),
        mean_first_relevant_score=mean_first_relevant_score,
        mean_negative_top_score=mean_negative_top_score,
        score_separation=(
            mean_first_relevant_score - mean_negative_top_score
            if mean_first_relevant_score is not None
            and mean_negative_top_score is not None
            else None
        ),
        cases=results,
    )


def save_evaluation_report(
    report: RetrievalEvaluationReport,
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def _has_complete_provenance(hit) -> bool:
    if not hit.pages or not hit.evidence_ids or not hit.evidence:
        return False
    snippet_ids = {snippet.evidence_id for snippet in hit.evidence}
    return set(hit.evidence_ids).issubset(snippet_ids)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[rank]


def _group_recall_at(
    results: list[RetrievalCaseResult],
    cutoff: int,
) -> float:
    expected = sum(result.expected_group_count for result in results)
    if not expected:
        return 0.0
    retrieved = sum(
        rank is not None and rank <= cutoff
        for result in results
        for rank in result.relevant_group_ranks
    )
    return retrieved / expected


def _full_group_recall_at(
    results: list[RetrievalCaseResult],
    cutoff: int,
) -> float:
    if not results:
        return 0.0
    complete = sum(
        bool(result.relevant_group_ranks)
        and all(
            rank is not None and rank <= cutoff for rank in result.relevant_group_ranks
        )
        for result in results
    )
    return complete / len(results)
