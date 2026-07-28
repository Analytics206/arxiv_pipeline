"""Versioned data contracts for evidence-backed paper analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Strict base model used for persisted and model-generated contracts."""

    model_config = ConfigDict(extra="forbid")


class EvidenceQuote(ContractModel):
    """A quote proposed by the model before source validation."""

    page: int = Field(ge=1)
    quote: str = Field(max_length=1200)
    section: str | None = Field(default=None, max_length=200)


class EvidenceRef(ContractModel):
    """A source quote that has been verified against extracted page text."""

    evidence_id: str
    chunk_id: str
    page: int = Field(ge=1)
    quote: str = Field(min_length=8, max_length=1200)
    supporting_quote: str | None = Field(default=None, min_length=8, max_length=1200)
    truncated: bool = False
    section: str | None = Field(default=None, max_length=200)


class DraftClaim(ContractModel):
    """A claim produced during chunk analysis."""

    statement: str = Field(min_length=8, max_length=2000)
    evidence: list[EvidenceQuote] = Field(min_length=1, max_length=5)


class DraftImplementationIdea(ContractModel):
    """An implementation idea before its citations are normalized."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=8, max_length=3000)
    agent_use: str = Field(min_length=8, max_length=2000)
    expected_benefit: str = Field(min_length=3, max_length=1000)
    risks: list[str] = Field(default_factory=list, max_length=8)
    evidence: list[EvidenceQuote] = Field(min_length=1, max_length=5)


class ChunkAnalysisDraft(ContractModel):
    """Structured map-stage output for one group of PDF pages."""

    problem: list[DraftClaim] = Field(default_factory=list, max_length=2)
    contributions: list[DraftClaim] = Field(default_factory=list, max_length=2)
    methods: list[DraftClaim] = Field(default_factory=list, max_length=2)
    results: list[DraftClaim] = Field(default_factory=list, max_length=2)
    limitations: list[DraftClaim] = Field(default_factory=list, max_length=2)
    implementation_ideas: list[DraftImplementationIdea] = Field(
        default_factory=list, max_length=1
    )
    concepts: list[str] = Field(default_factory=list, max_length=5)


class SupportedClaim(ContractModel):
    """A synthesized claim with verified evidence references."""

    statement: str = Field(min_length=8, max_length=3000)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)


class ImplementationIdea(ContractModel):
    """An engineering idea derived from the paper, not a paper-authored fact."""

    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=8, max_length=4000)
    agent_use: str = Field(min_length=8, max_length=3000)
    expected_benefit: str = Field(min_length=3, max_length=1500)
    risks: list[str] = Field(default_factory=list, max_length=10)
    evidence_ids: list[str] = Field(min_length=1, max_length=12)


class SynthesisDraft(ContractModel):
    """Reduce-stage output. Evidence IDs are validated after generation."""

    tldr: SupportedClaim
    problem: list[SupportedClaim] = Field(default_factory=list, max_length=8)
    contributions: list[SupportedClaim] = Field(default_factory=list, max_length=12)
    methods: list[SupportedClaim] = Field(default_factory=list, max_length=12)
    results: list[SupportedClaim] = Field(default_factory=list, max_length=12)
    limitations: list[SupportedClaim] = Field(default_factory=list, max_length=12)
    implementation_ideas: list[ImplementationIdea] = Field(
        default_factory=list, max_length=12
    )
    concepts: list[str] = Field(default_factory=list, max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=30)


class PaperAnalysis(ContractModel):
    """Canonical, versioned analysis returned to research clients."""

    contract: Literal["agent-paper-analysis"] = "agent-paper-analysis"
    schema_version: str
    prompt_version: str
    paper_id: str
    paper_version_id: str
    resource_uri: str
    title: str
    document_hash: str
    page_count: int = Field(ge=1)
    model: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tldr: SupportedClaim
    problem: list[SupportedClaim] = Field(default_factory=list)
    contributions: list[SupportedClaim] = Field(default_factory=list)
    methods: list[SupportedClaim] = Field(default_factory=list)
    results: list[SupportedClaim] = Field(default_factory=list)
    limitations: list[SupportedClaim] = Field(default_factory=list)
    implementation_ideas: list[ImplementationIdea] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(min_length=1)


class AgentPaperContext(ContractModel):
    """Complete read contract shared by REST and future MCP adapters."""

    contract: Literal["agent-paper-context"] = "agent-paper-context"
    resource_uri: str
    paper: dict
    analysis: PaperAnalysis


class ContextPackagePaper(ContractModel):
    """Stable paper identity without storage-specific or long abstract fields."""

    paper_id: str
    paper_version_id: str
    resource_uri: str
    title: str
    arxiv_url: str
    pdf_url: str


class ContextPackageProvenance(ContractModel):
    """Analysis provenance required to judge and reproduce a context package."""

    document_hash: str
    page_count: int = Field(ge=1)
    analysis_schema_version: str
    prompt_version: str
    analysis_model: str
    generated_at: datetime


class ContextContentCounts(ContractModel):
    """Counts for every independently selectable context content kind."""

    tldr: int = Field(default=1, ge=0)
    problem: int = Field(default=0, ge=0)
    contributions: int = Field(default=0, ge=0)
    methods: int = Field(default=0, ge=0)
    results: int = Field(default=0, ge=0)
    limitations: int = Field(default=0, ge=0)
    implementation_ideas: int = Field(default=0, ge=0)
    concepts: int = Field(default=0, ge=0)
    tags: int = Field(default=0, ge=0)
    evidence: int = Field(default=0, ge=0)


class ContextPackageBudget(ContractModel):
    """Auditable budget and selection information for an agent context."""

    requested_tokens: int = Field(ge=1)
    estimated_tokens: int = Field(ge=1)
    estimator: Literal["utf8-bytes-div-4-v1"] = "utf8-bytes-div-4-v1"
    profile: Literal["brief", "standard", "deep", "custom"]
    budget_source: Literal["profile", "explicit"]
    selection_policy: Literal["coding-agent-v1"] = "coding-agent-v1"
    truncated: bool
    available: ContextContentCounts
    included: ContextContentCounts
    omitted: ContextContentCounts


class BudgetedPaperAnalysis(ContractModel):
    """A deterministic subset of one canonical paper analysis."""

    tldr: SupportedClaim
    implementation_ideas: list[ImplementationIdea] = Field(default_factory=list)
    methods: list[SupportedClaim] = Field(default_factory=list)
    results: list[SupportedClaim] = Field(default_factory=list)
    limitations: list[SupportedClaim] = Field(default_factory=list)
    contributions: list[SupportedClaim] = Field(default_factory=list)
    problem: list[SupportedClaim] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(min_length=1)


class AgentContextPackage(ContractModel):
    """Token-budgeted, evidence-closed context for coding and AI agents."""

    contract: Literal["agent-context-package"] = "agent-context-package"
    schema_version: Literal["1.0"] = "1.0"
    paper: ContextPackagePaper
    provenance: ContextPackageProvenance
    budget: ContextPackageBudget
    analysis: BudgetedPaperAnalysis


class PaperCatalogItem(ContractModel):
    """Compact discovery record for one currently curated paper."""

    paper_id: str
    paper_version_id: str
    resource_uri: str
    title: str
    generated_at: datetime
    model: str
    page_count: int = Field(ge=1)
    concepts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    evidence_count: int = Field(ge=0)
    claim_count: int = Field(ge=0)
    implementation_idea_count: int = Field(ge=0)


class PaperCatalogResponse(ContractModel):
    """Paginated list of papers with a current evidence-backed analysis."""

    contract: Literal["research-paper-catalog"] = "research-paper-catalog"
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    papers: list[PaperCatalogItem] = Field(default_factory=list)


class EvidenceResource(ContractModel):
    """One verified quote with enough provenance for an external agent."""

    contract: Literal["research-evidence"] = "research-evidence"
    evidence_uri: str
    paper_resource_uri: str
    paper_id: str
    paper_version_id: str
    title: str
    document_hash: str
    prompt_version: str
    analysis_model: str
    evidence: EvidenceRef
