"""Contracts for the rebuildable research-knowledge vector index."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ResearchPointKind = Literal["evidence", "claim", "implementation_idea"]
RetrievalMode = Literal["dense", "hybrid"]


class RetrievalContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSnippet(RetrievalContract):
    evidence_id: str
    page: int = Field(ge=1)
    quote: str
    section: str | None = None


class ResearchIndexPoint(RetrievalContract):
    """One independently retrievable, provenance-preserving knowledge item."""

    contract: Literal["research-index-point"] = "research-index-point"
    index_schema_version: str
    point_id: str
    analysis_key: str
    paper_id: str
    paper_version_id: str
    resource_uri: str
    title: str
    kind: ResearchPointKind
    category: str
    text: str
    embedding_text: str
    pages: list[int] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)
    document_hash: str
    analysis_schema_version: str
    prompt_version: str
    analysis_model: str
    embedding_model: str

    def payload(self) -> dict:
        """Return Qdrant payload without duplicating the embedding-only text."""

        return self.model_dump(mode="json", exclude={"embedding_text"})


class ResearchSearchHit(RetrievalContract):
    point_id: str
    score: float
    paper_id: str
    paper_version_id: str
    resource_uri: str
    title: str
    kind: ResearchPointKind
    category: str
    text: str
    pages: list[int] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSnippet] = Field(default_factory=list)
    document_hash: str
    prompt_version: str
    analysis_model: str
    embedding_model: str


class ResearchSearchResponse(RetrievalContract):
    contract: Literal["research-search-results"] = "research-search-results"
    query: str
    limit: int
    embedding_model: str
    retrieval_mode: RetrievalMode = "dense"
    score_semantics: Literal["cosine_similarity", "rrf"] = "cosine_similarity"
    hits: list[ResearchSearchHit]
