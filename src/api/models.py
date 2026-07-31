"""Machine-readable discovery contracts for research-service clients."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ApiContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResearchToolDescriptor(ApiContract):
    name: str
    method: Literal["GET"]
    path: str
    purpose: str


class ResearchCapabilities(ApiContract):
    contract: Literal["research-service-capabilities"] = "research-service-capabilities"
    service: Literal["arxiv-research-intelligence"] = "arxiv-research-intelligence"
    version: str
    read_only: bool = True
    transports: list[Literal["rest", "openapi"]]
    openapi_path: str
    docs_path: str
    stable_resource_scheme: Literal["paper://arxiv"] = "paper://arxiv"
    tools: list[ResearchToolDescriptor]


def research_capabilities(version: str) -> ResearchCapabilities:
    return ResearchCapabilities(
        version=version,
        transports=["rest", "openapi"],
        openapi_path="/openapi.json",
        docs_path="/docs",
        tools=[
            ResearchToolDescriptor(
                name="search_research",
                method="GET",
                path="/research/search",
                purpose=(
                    "Search both complementary Qdrant collections, merge each "
                    "paper with MongoDB metadata, and return one bounded, "
                    "paper-centric result set with verified evidence kept "
                    "distinct from metadata-only discovery leads. The response "
                    "includes a request ID linked to an append-only evaluation "
                    "trace."
                ),
            ),
            ResearchToolDescriptor(
                name="list_curated_papers",
                method="GET",
                path="/research/papers",
                purpose="Discover papers with a current curated analysis.",
            ),
            ResearchToolDescriptor(
                name="get_paper_context",
                method="GET",
                path="/research/papers/agent-context",
                purpose=(
                    "Get the complete structured, evidence-backed context "
                    "package for one arXiv paper."
                ),
            ),
            ResearchToolDescriptor(
                name="get_paper_context_package",
                method="GET",
                path="/research/papers/context-package",
                purpose=(
                    "Get a deterministic token-budgeted subset for one paper "
                    "with closed evidence references and omission metadata."
                ),
            ),
            ResearchToolDescriptor(
                name="get_evidence",
                method="GET",
                path="/research/evidence/{evidence_id}",
                purpose=(
                    "Resolve one verified evidence identifier to its source "
                    "quote, page, paper, and analysis provenance."
                ),
            ),
        ],
    )
