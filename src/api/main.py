from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes.mongodb import router as mongodb_router

app = FastAPI(title="ArXiv Pipeline API")

# Enable CORS for all origins (development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mongodb_router, prefix="/metrics/mongodb", tags=["mongodb"])

from src.api.routes.qdrant import router as qdrant_router
app.include_router(qdrant_router, prefix="/metrics/qdrant", tags=["qdrant"])

from src.api.routes.neo4j import router as neo4j_router
app.include_router(neo4j_router, prefix="/neo4j", tags=["neo4j"])
