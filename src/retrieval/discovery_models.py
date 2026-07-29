"""Contracts for metadata-only arXiv paper discovery."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.retrieval.models import ResearchSearchResponse


class DiscoveryContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiscoveryIndexPoint(DiscoveryContract):
    contract: Literal["arxiv-discovery-index-point"] = "arxiv-discovery-index-point"
    index_schema_version: str
    point_id: str
    paper_id: str
    title: str
    embedding_text: str
    categories: list[str] = Field(default_factory=list)
    primary_category: str | None = None
    update_date: str | None = None
    update_year: int | None = None
    latest_version: str | None = None
    source: Literal["arxiv_kaggle"] = "arxiv_kaggle"
    corpus_run_id: str | None = None
    metadata_hash: str
    embedding_model: str

    def payload(self) -> dict:
        return self.model_dump(mode="json", exclude={"embedding_text"})


class DiscoverySearchHit(DiscoveryContract):
    point_id: str
    score: float
    relevance: float = Field(ge=0, le=1)
    tier: Literal["metadata_only"] = "metadata_only"
    paper_id: str
    title: str
    abstract: str | None = None
    authors: str | None = None
    categories: list[str] = Field(default_factory=list)
    primary_category: str | None = None
    update_date: str | None = None
    update_year: int | None = None
    latest_version: str | None = None
    doi: str | None = None
    journal_ref: str | None = None
    license: str | None = None
    comments: str | None = None
    source: Literal["arxiv_kaggle"] = "arxiv_kaggle"
    corpus_run_id: str | None = None
    metadata_hash: str


class DiscoveryCorpusCoverage(DiscoveryContract):
    collection: str
    eligible_points: int | None = Field(default=None, ge=0)
    returned_hits: int = Field(ge=0)


class DiscoverySearchResponse(DiscoveryContract):
    contract: Literal["arxiv-discovery-results"] = "arxiv-discovery-results"
    query: str
    limit: int
    embedding_model: str
    retrieval_mode: Literal["hybrid"] = "hybrid"
    score_semantics: Literal["rrf"] = "rrf"
    result_status: Literal["matches", "no_match"]
    no_match_reason: str | None = None
    coverage: DiscoveryCorpusCoverage
    hits: list[DiscoverySearchHit]


class FederatedResearchSearchResponse(DiscoveryContract):
    contract: Literal["federated-research-search"] = "federated-research-search"
    query: str
    evidence_backed: ResearchSearchResponse
    metadata_only: DiscoverySearchResponse
