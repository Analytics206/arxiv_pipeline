"""Evaluation contracts for the canonical paper-centric search."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from src.retrieval.curated_models import CuratedResearchSearchResponse


class EvaluationContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CuratedSearchCase(EvaluationContract):
    case_id: str
    query: str
    case_type: Literal["positive", "negative"] = "positive"
    expected_paper_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=8, ge=1, le=50)
    categories: list[str] = Field(default_factory=list)
    start_year: int | None = Field(default=None, ge=1990, le=2100)
    end_year: int | None = Field(default=None, ge=1990, le=2100)


class CuratedSearchSuite(EvaluationContract):
    suite_id: str
    description: str
    cases: list[CuratedSearchCase]


class CuratedCaseResult(EvaluationContract):
    case_id: str
    passed: bool
    returned_paper_ids: list[str]
    expected_ranks: dict[str, int | None]
    recall_at_limit: float = Field(ge=0, le=1)
    reciprocal_rank: float = Field(ge=0, le=1)
    duplicate_free: bool
    budget_compliant: bool
    tier_contract_valid: bool
    both_sources_reported: bool
    trace_identifiers_valid: bool


class CuratedEvaluationReport(EvaluationContract):
    contract: Literal["curated-search-evaluation"] = "curated-search-evaluation"
    suite_id: str
    cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)
    mean_recall_at_limit: float = Field(ge=0, le=1)
    mean_reciprocal_rank: float = Field(ge=0, le=1)
    results: list[CuratedCaseResult]


class CuratedSearcher(Protocol):
    def search(self, query: str, **kwargs) -> CuratedResearchSearchResponse: ...


def evaluate_curated_search(
    service: CuratedSearcher,
    suite: CuratedSearchSuite,
) -> CuratedEvaluationReport:
    results: list[CuratedCaseResult] = []
    for case in suite.cases:
        response = service.search(
            case.query,
            limit=case.limit,
            categories=case.categories or None,
            start_year=case.start_year,
            end_year=case.end_year,
        )
        returned_ids = [paper.paper_id for paper in response.papers]
        ranks = {
            paper_id: (
                returned_ids.index(paper_id) + 1 if paper_id in returned_ids else None
            )
            for paper_id in case.expected_paper_ids
        }
        found = sum(rank is not None for rank in ranks.values())
        recall = (
            found / len(case.expected_paper_ids) if case.expected_paper_ids else 1.0
        )
        first_rank = min((rank for rank in ranks.values() if rank), default=None)
        reciprocal_rank = 1 / first_rank if first_rank else 0.0
        duplicate_free = len(returned_ids) == len(set(returned_ids))
        budget_compliant = (
            response.budget.estimated_tokens <= response.budget.requested_tokens
        )
        tier_contract_valid = all(
            (
                paper.tier == "evidence_backed"
                and bool(paper.research_items)
                and all(item.evidence_ids for item in paper.research_items)
            )
            or (paper.tier == "metadata_only" and not paper.research_items)
            for paper in response.papers
        )
        both_sources_reported = {
            source.source for source in response.coverage.sources
        } == {"evidence", "discovery"}
        trace_identifiers_valid = (
            response.request_id.startswith("rs_")
            and response.generated_at.tzinfo is not None
        )
        if case.case_type == "negative":
            semantic_pass = not returned_ids
            recall = 1.0 if semantic_pass else 0.0
            reciprocal_rank = 1.0 if semantic_pass else 0.0
        else:
            semantic_pass = recall == 1.0
        passed = all(
            (
                semantic_pass,
                duplicate_free,
                budget_compliant,
                tier_contract_valid,
                both_sources_reported,
                trace_identifiers_valid,
            )
        )
        results.append(
            CuratedCaseResult(
                case_id=case.case_id,
                passed=passed,
                returned_paper_ids=returned_ids,
                expected_ranks=ranks,
                recall_at_limit=recall,
                reciprocal_rank=reciprocal_rank,
                duplicate_free=duplicate_free,
                budget_compliant=budget_compliant,
                tier_contract_valid=tier_contract_valid,
                both_sources_reported=both_sources_reported,
                trace_identifiers_valid=trace_identifiers_valid,
            )
        )
    count = len(results)
    return CuratedEvaluationReport(
        suite_id=suite.suite_id,
        cases=count,
        passed_cases=sum(result.passed for result in results),
        pass_rate=sum(result.passed for result in results) / count if count else 1.0,
        mean_recall_at_limit=(
            sum(result.recall_at_limit for result in results) / count if count else 1.0
        ),
        mean_reciprocal_rank=(
            sum(result.reciprocal_rank for result in results) / count if count else 1.0
        ),
        results=results,
    )
