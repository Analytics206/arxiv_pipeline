"""Paper-centric contracts for the canonical multi-source research search."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.retrieval.models import ResearchSearchHit


class CuratedContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaperSearchMetadata(CuratedContract):
    paper_id: str
    title: str
    abstract: str | None = None
    abstract_truncated: bool = False
    authors: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    primary_category: str | None = None
    published: str | None = None
    updated: str | None = None
    update_date: str | None = None
    update_year: int | None = None
    latest_version: str | None = None
    doi: str | None = None
    journal_ref: str | None = None
    license: str | None = None
    comments: str | None = None
    arxiv_url: str
    pdf_url: str
    corpus_run_id: str | None = None
    metadata_sources: list[Literal["papers", "arxiv_kaggle"]] = Field(
        default_factory=list
    )


class PaperSourceScore(CuratedContract):
    source: Literal["evidence", "discovery"]
    rank: int = Field(ge=1)
    relevance: float = Field(ge=0, le=1)
    raw_score: float


class CuratedPaperResult(CuratedContract):
    rank: int = Field(ge=1)
    paper_id: str
    resource_uri: str
    tier: Literal["evidence_backed", "metadata_only"]
    relevance: float = Field(ge=0, le=1)
    source_scores: list[PaperSourceScore]
    metadata: PaperSearchMetadata
    research_items: list[ResearchSearchHit] = Field(default_factory=list)


class CuratedSourceCoverage(CuratedContract):
    source: Literal["evidence", "discovery"]
    collection: str
    status: Literal["matches", "no_match", "unavailable"]
    returned_candidates: int = Field(ge=0)
    eligible_papers: int | None = Field(default=None, ge=0)
    eligible_points: int | None = Field(default=None, ge=0)
    error: str | None = None


class CuratedSearchCoverage(CuratedContract):
    sources: list[CuratedSourceCoverage]
    source_candidates: int = Field(ge=0)
    unique_candidate_papers: int = Field(ge=0)
    returned_papers: int = Field(ge=0)
    evidence_backed_papers: int = Field(ge=0)
    metadata_only_papers: int = Field(ge=0)
    partial: bool = False


class CuratedSearchBudget(CuratedContract):
    requested_tokens: int = Field(ge=1)
    estimated_tokens: int = Field(ge=1)
    requested_papers: int = Field(ge=1)
    returned_papers: int = Field(ge=0)
    evidence_items_per_paper: int = Field(ge=1)
    omitted_papers: int = Field(ge=0)
    truncated: bool = False
    estimator: Literal["utf8-bytes-div-4"] = "utf8-bytes-div-4"


class CuratedResearchSearchResponse(CuratedContract):
    contract: Literal["curated-research-results"] = "curated-research-results"
    request_id: str
    generated_at: datetime
    query: str
    result_status: Literal["matches", "no_match"]
    no_match_reason: str | None = None
    ranking: Literal[
        "weighted-paper-rrf",
        "weighted-paper-rrf-recency",
    ] = "weighted-paper-rrf"
    coverage: CuratedSearchCoverage
    budget: CuratedSearchBudget
    papers: list[CuratedPaperResult]
