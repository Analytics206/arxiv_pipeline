import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import ResearchCapabilities, research_capabilities
from src.api.routes.mongodb import router as mongodb_router

SERVICE_VERSION = "0.9.0"

app = FastAPI(
    title="ArXiv Research Intelligence API",
    version=SERVICE_VERSION,
    description=(
        "Read-only, evidence-backed research contracts for AI agents and "
        "human review tools."
    ),
    servers=[{"url": "/", "description": "Current research-service host"}],
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=ResearchCapabilities, include_in_schema=False)
def service_root() -> ResearchCapabilities:
    return research_capabilities(SERVICE_VERSION)


@app.get(
    "/health",
    operation_id="get_service_health",
    summary="Research service liveness",
)
def service_health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "arxiv-research-intelligence",
        "version": SERVICE_VERSION,
    }


app.include_router(mongodb_router, prefix="/metrics/mongodb", tags=["mongodb"])

from src.api.routes.qdrant import router as qdrant_router

app.include_router(qdrant_router, prefix="/metrics/qdrant", tags=["qdrant"])

from src.api.routes.neo4j import router as neo4j_router

app.include_router(neo4j_router, prefix="/neo4j", tags=["neo4j"])

from src.api.routes.papers import router as papers_router

app.include_router(
    papers_router,
    prefix="/research/papers",
    tags=["research"],
)

from src.api.routes.research import router as research_router

app.include_router(
    research_router,
    prefix="/research",
    tags=["research"],
)
