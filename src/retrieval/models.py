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
    supporting_quote: str | None = None
    truncated: bool = False
    section: str | None = None


class ImplementationIdeaFields(RetrievalContract):
    """Structured idea fields kept separate from canonical retrieval text."""

    title: str
    description: str
    agent_use: str
    expected_benefit: str
    risks: list[str] = Field(default_factory=list)


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
    implementation_idea: ImplementationIdeaFields | None = None
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
    relevance: float = Field(ge=0, le=1)
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
    implementation_idea: ImplementationIdeaFields | None = None
    document_hash: str
    prompt_version: str
    analysis_model: str
    embedding_model: str


class SearchCorpusCoverage(RetrievalContract):
    """Size of the indexed corpus and the subset eligible for this query."""

    collection: str
    papers: int | None = Field(default=None, ge=0)
    points: int | None = Field(default=None, ge=0)
    eligible_papers: int | None = Field(default=None, ge=0)
    eligible_points: int | None = Field(default=None, ge=0)
    returned_hits: int = Field(ge=0)


class SearchScoreCalibration(RetrievalContract):
    """Machine-readable interpretation of raw and normalized search scores."""

    raw_score: Literal["cosine_similarity", "rrf"]
    relevance: Literal[
        "cosine_clamped_v1",
        "rrf_retriever_agreement_v1",
    ]
    floor: float
    ceiling: float
    minimum_relevance: float = Field(ge=0, le=1)
    description: str


class ResearchSearchResponse(RetrievalContract):
    contract: Literal["research-search-results"] = "research-search-results"
    query: str
    limit: int
    embedding_model: str
    retrieval_mode: RetrievalMode = "dense"
    score_semantics: Literal["cosine_similarity", "rrf"] = "cosine_similarity"
    score_calibration: SearchScoreCalibration
    result_status: Literal["matches", "no_match"]
    no_match_reason: str | None = None
    coverage: SearchCorpusCoverage
    hits: list[ResearchSearchHit]
