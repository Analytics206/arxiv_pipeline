"""Reproducible evaluation for paper-level metadata discovery."""

from __future__ import annotations

import json
import math
from pathlib import Path
from time import perf_counter
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.retrieval.discovery_models import DiscoverySearchResponse


class DiscoveryEvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiscoveryEvaluationCase(DiscoveryEvaluationModel):
    case_id: str
    query: str
    case_type: Literal["positive", "negative"] = "positive"
    expected_paper_ids: list[str] = Field(default_factory=list)
    categories: list[str] | None = None
    start_year: int | None = None
    end_year: int | None = None
    limit: int = Field(default=8, ge=1, le=50)
    note: str | None = None

    @model_validator(mode="after")
    def validate_judgment(self) -> "DiscoveryEvaluationCase":
        if self.case_type == "positive" and not self.expected_paper_ids:
            raise ValueError("Positive cases require expected_paper_ids")
        if self.case_type == "negative" and self.expected_paper_ids:
            raise ValueError("Negative cases cannot declare expected papers")
        return self


class DiscoveryEvaluationSuite(DiscoveryEvaluationModel):
    suite_id: str
    description: str
    cases: list[DiscoveryEvaluationCase] = Field(min_length=1)


class DiscoveryCaseResult(DiscoveryEvaluationModel):
    case_id: str
    case_type: Literal["positive", "negative"]
    relevant: bool
    first_relevant_rank: int | None
    reciprocal_rank: float
    returned_hits: int
    top_paper_ids: list[str]
    latency_ms: float


class DiscoveryEvaluationReport(DiscoveryEvaluationModel):
    contract: Literal["arxiv-discovery-evaluation"] = "arxiv-discovery-evaluation"
    suite_id: str
    embedding_model: str
    case_count: int
    positive_case_count: int
    negative_case_count: int
    recall_at_limit: float
    mean_reciprocal_rank: float
    negative_no_match_rate: float
    mean_latency_ms: float
    p95_latency_ms: float
    cases: list[DiscoveryCaseResult]


class SearchableDiscoveryIndex(Protocol):
    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        categories: list[str] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> DiscoverySearchResponse: ...


def load_discovery_suite(
    path: str | Path,
) -> DiscoveryEvaluationSuite:
    return DiscoveryEvaluationSuite.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def evaluate_discovery(
    index: SearchableDiscoveryIndex,
    suite: DiscoveryEvaluationSuite,
) -> DiscoveryEvaluationReport:
    results: list[DiscoveryCaseResult] = []
    embedding_model: str | None = None
    for case in suite.cases:
        started = perf_counter()
        response = index.search(
            case.query,
            limit=case.limit,
            categories=case.categories,
            start_year=case.start_year,
            end_year=case.end_year,
        )
        latency_ms = (perf_counter() - started) * 1000
        embedding_model = embedding_model or response.embedding_model
        expected = set(case.expected_paper_ids)
        first_rank = next(
            (
                rank
                for rank, hit in enumerate(response.hits, start=1)
                if hit.paper_id in expected
            ),
            None,
        )
        results.append(
            DiscoveryCaseResult(
                case_id=case.case_id,
                case_type=case.case_type,
                relevant=first_rank is not None,
                first_relevant_rank=first_rank,
                reciprocal_rank=1 / first_rank if first_rank else 0.0,
                returned_hits=len(response.hits),
                top_paper_ids=[hit.paper_id for hit in response.hits],
                latency_ms=round(latency_ms, 3),
            )
        )
    positives = [item for item in results if item.case_type == "positive"]
    negatives = [item for item in results if item.case_type == "negative"]
    latencies = [item.latency_ms for item in results]
    return DiscoveryEvaluationReport(
        suite_id=suite.suite_id,
        embedding_model=embedding_model or "unknown",
        case_count=len(results),
        positive_case_count=len(positives),
        negative_case_count=len(negatives),
        recall_at_limit=(
            sum(item.relevant for item in positives) / len(positives)
            if positives
            else 0.0
        ),
        mean_reciprocal_rank=(
            sum(item.reciprocal_rank for item in positives) / len(positives)
            if positives
            else 0.0
        ),
        negative_no_match_rate=(
            sum(item.returned_hits == 0 for item in negatives) / len(negatives)
            if negatives
            else 0.0
        ),
        mean_latency_ms=(sum(latencies) / len(latencies) if latencies else 0.0),
        p95_latency_ms=_percentile(latencies, 0.95),
        cases=results,
    )


def save_discovery_report(
    report: DiscoveryEvaluationReport,
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[rank]
