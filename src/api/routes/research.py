# mypy: disable-error-code=attr-defined
"""Semantic research retrieval for agent and human clients."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.analysis.identity import normalize_arxiv_id
from src.analysis.models import EvidenceResource
from src.api.models import ResearchCapabilities, research_capabilities
from src.api.routes.papers import Repository
from src.retrieval.discovery_models import (
    DiscoverySearchResponse,
    FederatedResearchSearchResponse,
)
from src.retrieval.discovery_repository import KaggleDiscoveryRepository
from src.retrieval.factory import (
    create_discovery_index,
    create_research_index,
    load_project_config,
)
from src.retrieval.models import ResearchPointKind, ResearchSearchResponse
from src.retrieval.qdrant_discovery import QdrantDiscoveryIndex
from src.retrieval.qdrant_index import QdrantResearchIndex

router = APIRouter()
SERVICE_VERSION = "0.9.0"


def get_research_index() -> QdrantResearchIndex:
    return create_research_index(load_project_config())


ResearchIndex = Annotated[QdrantResearchIndex, Depends(get_research_index)]


def get_discovery_index() -> QdrantDiscoveryIndex:
    return create_discovery_index(load_project_config())


def get_discovery_repository() -> Iterator[KaggleDiscoveryRepository]:
    config = load_project_config()
    mongo = config.get("mongo", {})
    discovery = config.get("discovery_index", {})
    repository = KaggleDiscoveryRepository(
        connection_string=os.getenv(
            "MONGO_CONNECTION_STRING",
            mongo.get("connection_string_local", "mongodb://localhost:27017/"),
        ),
        db_name=os.getenv(
            "MONGO_DB",
            mongo.get("db_name", "arxiv_papers"),
        ),
        collection_name=str(discovery.get("source_collection") or "arxiv_kaggle"),
    )
    try:
        yield repository
    finally:
        repository.close()


DiscoveryIndex = Annotated[QdrantDiscoveryIndex, Depends(get_discovery_index)]
DiscoveryRepository = Annotated[
    KaggleDiscoveryRepository,
    Depends(get_discovery_repository),
]


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


@router.get(
    "/discovery/search",
    response_model=DiscoverySearchResponse,
    operation_id="search_paper_discovery",
    summary="Search metadata-only title and abstract paper discovery",
)
def search_paper_discovery(
    index: DiscoveryIndex,
    repository: DiscoveryRepository,
    query: Annotated[str, Query(min_length=3, max_length=2000)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    category: Annotated[list[str] | None, Query()] = None,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    min_relevance: Annotated[float | None, Query(ge=0, le=1)] = None,
) -> DiscoverySearchResponse:
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=422,
            detail="start_year cannot be later than end_year",
        )
    try:
        response = index.search(
            query,
            limit=limit,
            categories=category,
            start_year=start_year,
            end_year=end_year,
            min_relevance=min_relevance,
        )
        return repository.hydrate(response)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Discovery index unavailable: {error}",
        ) from error


@router.get(
    "/federated-search",
    response_model=FederatedResearchSearchResponse,
    operation_id="search_federated_research",
    summary="Search evidence-backed and metadata-only corpora separately",
)
def search_federated_research(
    research_index: ResearchIndex,
    discovery_index: DiscoveryIndex,
    discovery_repository: DiscoveryRepository,
    query: Annotated[str, Query(min_length=3, max_length=2000)],
    limit: Annotated[int, Query(ge=1, le=50)] = 8,
    category: Annotated[list[str] | None, Query()] = None,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    min_relevance: Annotated[float | None, Query(ge=0, le=1)] = None,
) -> FederatedResearchSearchResponse:
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=422,
            detail="start_year cannot be later than end_year",
        )
    try:
        evidence = research_index.search(
            query,
            limit=limit,
            min_relevance=min_relevance,
        )
        discovery = discovery_repository.hydrate(
            discovery_index.search(
                query,
                limit=limit,
                categories=category,
                start_year=start_year,
                end_year=end_year,
                min_relevance=min_relevance,
            )
        )
        return federate_search_results(
            query=query,
            evidence=evidence,
            discovery=discovery,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Federated search unavailable: {error}",
        ) from error


def federate_search_results(
    *,
    query: str,
    evidence: ResearchSearchResponse,
    discovery: DiscoverySearchResponse,
) -> FederatedResearchSearchResponse:
    """Deduplicate by paper while preserving independent score semantics."""

    evidence_papers = {hit.paper_id for hit in evidence.hits}
    metadata_hits = [
        hit for hit in discovery.hits if hit.paper_id not in evidence_papers
    ]
    metadata_response = discovery.model_copy(
        update={
            "hits": metadata_hits,
            "coverage": discovery.coverage.model_copy(
                update={"returned_hits": len(metadata_hits)}
            ),
            "result_status": "matches" if metadata_hits else "no_match",
            "no_match_reason": (
                discovery.no_match_reason
                if metadata_hits or not discovery.hits
                else (
                    "All metadata-only hits were removed because the same "
                    "papers had evidence-backed results."
                )
            ),
        }
    )
    return FederatedResearchSearchResponse(
        query=query,
        evidence_backed=evidence,
        metadata_only=metadata_response,
    )
