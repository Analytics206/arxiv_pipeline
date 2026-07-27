"""Configuration helpers for the research retrieval service."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from src.retrieval.ollama_embeddings import OllamaEmbeddingModel
from src.retrieval.models import RetrievalMode
from src.retrieval.qdrant_index import QdrantResearchIndex
from src.utils.ai_services import (
    resolve_ollama_embedding_model,
    resolve_ollama_url,
)

DEFAULT_CONFIG_PATH = Path("config/default.yaml")


def load_project_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def create_research_index(
    config: dict[str, Any],
    *,
    qdrant_url: str | None = None,
    ollama_url: str | None = None,
    embedding_model: str | None = None,
    collection_name: str | None = None,
    query_prefix: str | None = None,
    document_prefix: str | None = None,
    retrieval_mode: RetrievalMode | None = None,
    hybrid_candidate_multiplier: int | None = None,
    hybrid_candidate_minimum: int | None = None,
    rrf_dense_weight: float | None = None,
    rrf_sparse_weight: float | None = None,
    rrf_k: int | None = None,
    paper_diversity_penalty: float | None = None,
    index_schema_version: str | None = None,
) -> QdrantResearchIndex:
    settings = config.get("research_index", {})
    selected_embedding_model = resolve_ollama_embedding_model(
        config,
        explicit_model=embedding_model,
    )
    hybrid_settings = settings.get("hybrid", {})
    embedder = OllamaEmbeddingModel(
        model_name=selected_embedding_model,
        host=resolve_ollama_url(config, explicit_url=ollama_url),
        query_prefix=(
            query_prefix
            if query_prefix is not None
            else settings.get(
                "query_prefix",
                "Represent this sentence for searching relevant passages: ",
            )
        ),
        document_prefix=(
            document_prefix
            if document_prefix is not None
            else settings.get("document_prefix", "")
        ),
    )
    return QdrantResearchIndex(
        url=resolve_qdrant_url(config, explicit_url=qdrant_url),
        collection_name=(
            collection_name
            or os.getenv("QDRANT_RESEARCH_COLLECTION")
            or settings.get("collection_name")
            or "research_knowledge_hybrid_v1"
        ),
        embedder=embedder,
        index_schema_version=str(
            index_schema_version
            if index_schema_version is not None
            else settings.get("schema_version", "1.0")
        ),
        batch_size=int(settings.get("embedding_batch_size", 32)),
        retrieval_mode=(
            retrieval_mode
            if retrieval_mode is not None
            else settings.get("retrieval_mode", "dense")
        ),
        hybrid_candidate_multiplier=int(
            hybrid_candidate_multiplier
            if hybrid_candidate_multiplier is not None
            else hybrid_settings.get("candidate_multiplier", 4)
        ),
        hybrid_candidate_minimum=int(
            hybrid_candidate_minimum
            if hybrid_candidate_minimum is not None
            else hybrid_settings.get("candidate_minimum", 50)
        ),
        rrf_dense_weight=float(
            rrf_dense_weight
            if rrf_dense_weight is not None
            else hybrid_settings.get("dense_weight", 1.0)
        ),
        rrf_sparse_weight=float(
            rrf_sparse_weight
            if rrf_sparse_weight is not None
            else hybrid_settings.get("sparse_weight", 1.0)
        ),
        rrf_k=int(rrf_k if rrf_k is not None else hybrid_settings.get("rrf_k", 60)),
        paper_diversity_penalty=float(
            paper_diversity_penalty
            if paper_diversity_penalty is not None
            else hybrid_settings.get("paper_diversity_penalty", 0.0)
        ),
    )


def resolve_qdrant_url(
    config: dict[str, Any],
    *,
    explicit_url: str | None = None,
) -> str:
    direct = explicit_url or os.getenv("QDRANT_URL")
    if direct:
        return direct.rstrip("/")
    host = os.getenv("QDRANT_HOST")
    if host:
        port = os.getenv("QDRANT_PORT", "6333")
        if "://" not in host:
            host = f"http://{host}"
        return f"{host.rstrip('/')}:{port}"

    qdrant = config.get("qdrant", {})
    if os.path.exists("/.dockerenv"):
        return str(qdrant.get("url", "http://qdrant:6333")).rstrip("/")
    return str(
        qdrant.get("url_local") or qdrant.get("url") or "http://localhost:6333"
    ).rstrip("/")
