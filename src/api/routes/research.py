# mypy: disable-error-code=attr-defined
"""Semantic research retrieval for agent and human clients."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from src.analysis.models import EvidenceResource
from src.api.models import ResearchCapabilities, research_capabilities
from src.api.routes.papers import Repository
from src.retrieval.curated_models import CuratedResearchSearchResponse
from src.retrieval.curated_service import (
    CuratedResearchService,
    CuratedSearchUnavailableError,
)
from src.retrieval.discovery_repository import KaggleDiscoveryRepository
from src.retrieval.factory import (
    create_discovery_index,
    create_research_index,
    load_project_config,
)
from src.retrieval.models import ResearchPointKind
from src.retrieval.qdrant_discovery import QdrantDiscoveryIndex
from src.retrieval.qdrant_index import QdrantResearchIndex
from src.retrieval.search_history import MongoSearchHistoryRepository

router = APIRouter()
SERVICE_VERSION = "0.9.0"
logger = logging.getLogger(__name__)


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
        eligibility_collection_name=str(
            discovery.get("eligibility_collection") or "papers"
        ),
        eligibility_id_field=str(
            discovery.get("eligibility_id_field") or "base_arxiv_id"
        ),
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
    response_model=CuratedResearchSearchResponse,
    operation_id="search_research",
    summary="Search and curate both complementary research collections",
)
def search_research(
    request: Request,
    response: Response,
    research_index: ResearchIndex,
    discovery_index: DiscoveryIndex,
    discovery_repository: DiscoveryRepository,
    query: Annotated[str, Query(min_length=3, max_length=2000)],
    limit: Annotated[int, Query(ge=1, le=50)] = 8,
    paper_id: Annotated[str | None, Query(min_length=3)] = None,
    kind: Annotated[list[ResearchPointKind] | None, Query()] = None,
    category: Annotated[list[str] | None, Query()] = None,
    start_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    end_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
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
    evidence_per_paper: Annotated[int, Query(ge=1, le=8)] = 3,
    token_budget: Annotated[int, Query(ge=2000, le=32768)] = 12000,
) -> CuratedResearchSearchResponse:
    if start_year is not None and end_year is not None and start_year > end_year:
        raise HTTPException(
            status_code=422,
            detail="start_year cannot be later than end_year",
        )
    try:
        config = load_project_config()
        settings = config.get("research_search", {})
        history_recorder = _create_history_recorder(
            settings=settings,
            database=discovery_repository.db,
        )
        service = CuratedResearchService(
            research_index=research_index,
            discovery_index=discovery_index,
            metadata_repository=discovery_repository,
            candidate_multiplier=int(settings.get("candidate_multiplier", 6)),
            candidate_minimum=int(settings.get("candidate_minimum", 50)),
            evidence_weight=float(settings.get("evidence_weight", 1.0)),
            discovery_weight=float(settings.get("discovery_weight", 1.0)),
            rrf_k=int(settings.get("rrf_k", 60)),
            default_evidence_items_per_paper=int(
                settings.get("evidence_items_per_paper", 3)
            ),
            default_token_budget=int(settings.get("token_budget", 12000)),
            maximum_abstract_chars=int(settings.get("maximum_abstract_chars", 2400)),
            history_recorder=history_recorder,
        )
        result = service.search(
            query,
            limit=limit,
            paper_id=paper_id,
            kinds=kind,
            categories=category,
            start_year=start_year,
            end_year=end_year,
            min_relevance=min_relevance,
            evidence_items_per_paper=evidence_per_paper,
            token_budget=token_budget,
            client=_client_context(request),
        )
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Research-Request-ID"] = result.request_id
        return result
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except CuratedSearchUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Research search unavailable: {error}",
        ) from error


def _create_history_recorder(
    *,
    settings: dict[str, Any],
    database: Any,
) -> MongoSearchHistoryRepository | None:
    history = settings.get("history", {})
    configured = history.get("enabled", True)
    enabled = _environment_bool(
        "RESEARCH_SEARCH_HISTORY_ENABLED",
        default=bool(configured),
    )
    if not enabled:
        return None
    try:
        return MongoSearchHistoryRepository(
            database=database,
            runs_collection=os.getenv(
                "MONGO_SEARCH_RUNS_COLLECTION",
                str(history.get("runs_collection") or "research_search_runs"),
            ),
            source_pulls_collection=os.getenv(
                "MONGO_SEARCH_PULLS_COLLECTION",
                str(
                    history.get("source_pulls_collection")
                    or "research_search_source_pulls"
                ),
            ),
            outputs_collection=os.getenv(
                "MONGO_SEARCH_OUTPUTS_COLLECTION",
                str(history.get("outputs_collection") or "research_search_outputs"),
            ),
        )
    except Exception:
        logger.exception("Research search history repository is unavailable")
        return None


def _client_context(request: Request) -> dict[str, str]:
    user_agent = request.headers.get("user-agent", "")
    declared = request.headers.get("x-research-client", "").strip()
    if declared:
        channel = declared[:64]
    elif user_agent.startswith("arxiv-research-mcp/"):
        channel = "mcp"
    else:
        channel = "rest"
    return {
        "channel": channel,
        "user_agent": user_agent[:512],
    }


def _environment_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
