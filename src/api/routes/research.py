"""Semantic research retrieval for agent and human clients."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.analysis.identity import normalize_arxiv_id
from src.analysis.models import EvidenceResource
from src.api.models import ResearchCapabilities, research_capabilities
from src.api.routes.papers import Repository
from src.retrieval.factory import create_research_index, load_project_config
from src.retrieval.models import (
    ResearchPointKind,
    ResearchSearchResponse,
)
from src.retrieval.qdrant_index import QdrantResearchIndex

router = APIRouter()
SERVICE_VERSION = "0.9.0"


def get_research_index() -> QdrantResearchIndex:
    return create_research_index(load_project_config())


ResearchIndex = Annotated[QdrantResearchIndex, Depends(get_research_index)]


@router.get(
    "/capabilities",
    response_model=ResearchCapabilities,
    operation_id="get_research_capabilities",
    summary="Discover the read-only research service contract",
)
def get_capabilities() -> ResearchCapabilities:
    return research_capabilities(SERVICE_VERSION)


@router.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceResource,
    operation_id="get_evidence",
    summary="Resolve a verified source-evidence identifier",
)
def get_evidence(
    evidence_id: str,
    repository: Repository,
) -> EvidenceResource:
    evidence = repository.get_evidence(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence


@router.get(
    "/search",
    response_model=ResearchSearchResponse,
    operation_id="search_research",
    summary="Search curated claims, evidence, and implementation ideas",
)
def search_research(
    index: ResearchIndex,
    query: Annotated[str, Query(min_length=3, max_length=2000)],
    limit: Annotated[int, Query(ge=1, le=50)] = 8,
    paper_id: Annotated[str | None, Query(min_length=3)] = None,
    kind: Annotated[list[ResearchPointKind] | None, Query()] = None,
    min_relevance: Annotated[
        float | None,
        Query(
            ge=0,
            le=1,
            description=(
                "Normalized relevance threshold; defaults to the evaluated "
                "service threshold. Set 0 to inspect all nearest candidates."
            ),
        ),
    ] = None,
) -> ResearchSearchResponse:
    try:
        normalized_paper_id = normalize_arxiv_id(paper_id).base_id if paper_id else None
        return index.search(
            query,
            limit=limit,
            paper_id=normalized_paper_id,
            kinds=kind,
            min_relevance=min_relevance,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Research index unavailable: {error}",
        ) from error
