"""Read-only research contracts for agents and human clients."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from src.analysis.context_packages import (
    ContextBudgetTooSmallError,
    build_agent_context_package,
)
from src.analysis.models import (
    AgentContextPackage,
    AgentPaperContext,
    PaperAnalysis,
    PaperCatalogResponse,
)
from src.analysis.repository import AnalysisRepository

router = APIRouter()


def get_repository() -> Iterator[AnalysisRepository]:
    repository = AnalysisRepository(
        connection_string=os.getenv(
            "MONGO_CONNECTION_STRING", "mongodb://localhost:27017/"
        ),
        db_name=os.getenv("MONGO_DB", "arxiv_papers"),
        collection_name=os.getenv("MONGO_ANALYSIS_COLLECTION", "paper_analyses"),
    )
    try:
        yield repository
    finally:
        repository.close()


Repository = Annotated[AnalysisRepository, Depends(get_repository)]
PaperId = Annotated[
    str,
    Query(
        min_length=3,
        description="Raw arXiv ID or an arXiv abs/pdf URL",
    ),
]


@router.get("/resolve")
def resolve_paper(paper_id: PaperId, repository: Repository) -> dict:
    paper = repository.find_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper metadata not found")
    return paper


@router.get(
    "",
    response_model=PaperCatalogResponse,
    operation_id="list_curated_papers",
    summary="List papers with a current curated analysis",
)
def list_curated_papers(
    repository: Repository,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PaperCatalogResponse:
    return repository.list_current_analyses(offset=offset, limit=limit)


@router.get(
    "/analysis",
    response_model=PaperAnalysis,
    operation_id="get_paper_analysis",
)
def get_latest_analysis(paper_id: PaperId, repository: Repository) -> PaperAnalysis:
    try:
        analysis = repository.get_latest_analysis(paper_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if analysis is None:
        raise HTTPException(status_code=404, detail="Paper analysis not found")
    return analysis


@router.get(
    "/agent-context",
    response_model=AgentPaperContext,
    operation_id="get_paper_context",
    summary="Get a complete evidence-backed paper context package",
)
def get_agent_context(paper_id: PaperId, repository: Repository) -> AgentPaperContext:
    try:
        context = repository.get_agent_context(paper_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if context is None:
        raise HTTPException(status_code=404, detail="Paper analysis not found")
    return context


@router.get(
    "/context-package",
    response_model=AgentContextPackage,
    operation_id="get_paper_context_package",
    summary="Get a token-budgeted, evidence-backed paper context package",
)
def get_agent_context_package(
    paper_id: PaperId,
    repository: Repository,
    profile: Annotated[
        Literal["brief", "standard", "deep"],
        Query(
            description=(
                "Reproducible budget alias: brief=1500, standard=4000, "
                "deep=8000 estimated tokens"
            )
        ),
    ] = "standard",
    token_budget: Annotated[
        int | None,
        Query(
            ge=512,
            le=32768,
            description=(
                "Explicit estimated-token budget; overrides the profile size "
                "while retaining the coding-agent selection policy"
            ),
        ),
    ] = None,
) -> AgentContextPackage:
    try:
        context = repository.get_agent_context(paper_id)
        if context is None:
            raise HTTPException(status_code=404, detail="Paper analysis not found")
        return build_agent_context_package(
            context,
            profile=profile,
            token_budget=token_budget,
        )
    except ContextBudgetTooSmallError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(error),
                "requested_tokens": error.requested_tokens,
                "minimum_required_tokens": error.minimum_required_tokens,
            },
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
