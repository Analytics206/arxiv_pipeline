"""Accurate status for the two complementary Qdrant collections."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from qdrant_client import QdrantClient

from src.retrieval.factory import load_project_config, resolve_qdrant_url

router = APIRouter()


@router.get(
    "/status",
    operation_id="get_qdrant_research_status",
    summary="Inspect active evidence and discovery collections",
)
def get_qdrant_research_status() -> dict[str, Any]:
    config = load_project_config()
    research = config.get("research_index", {})
    discovery = config.get("discovery_index", {})
    evidence_name = str(
        os.getenv("QDRANT_RESEARCH_COLLECTION")
        or research.get("collection_name")
        or "research_knowledge_hybrid_v1"
    )
    discovery_alias = str(
        os.getenv("QDRANT_DISCOVERY_ALIAS")
        or discovery.get("alias_name")
        or "arxiv_discovery_current"
    )
    client = QdrantClient(url=resolve_qdrant_url(config), timeout=10)
    try:
        aliases = {
            alias.alias_name: alias.collection_name
            for alias in client.get_aliases().aliases
        }
        collections = [
            _collection_status(
                client,
                role="evidence",
                configured_name=evidence_name,
                resolved_name=evidence_name,
            ),
            _collection_status(
                client,
                role="discovery",
                configured_name=discovery_alias,
                resolved_name=aliases.get(discovery_alias, discovery_alias),
            ),
        ]
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant status unavailable: {error}",
        ) from error
    available = sum(item["available"] for item in collections)
    return {
        "status": (
            "healthy"
            if available == len(collections)
            else "degraded" if available else "unavailable"
        ),
        "collections": collections,
    }


def _collection_status(
    client: QdrantClient,
    *,
    role: str,
    configured_name: str,
    resolved_name: str,
) -> dict[str, Any]:
    if not client.collection_exists(configured_name):
        return {
            "role": role,
            "configured_name": configured_name,
            "resolved_name": resolved_name,
            "available": False,
            "status": "missing",
            "points": 0,
            "indexed_vectors": 0,
            "dense_dimensions": None,
            "sparse_enabled": False,
        }
    collection = client.get_collection(configured_name)
    vectors = collection.config.params.vectors
    sparse_vectors = collection.config.params.sparse_vectors or {}
    return {
        "role": role,
        "configured_name": configured_name,
        "resolved_name": resolved_name,
        "available": True,
        "status": str(collection.status),
        "points": int(collection.points_count or 0),
        "indexed_vectors": int(collection.indexed_vectors_count or 0),
        "dense_dimensions": _dense_dimensions(vectors),
        "sparse_enabled": bool(sparse_vectors),
    }


def _dense_dimensions(vectors: Any) -> int | None:
    if hasattr(vectors, "size"):
        return int(vectors.size)
    if isinstance(vectors, dict):
        dense = vectors.get("dense")
        if dense is not None and hasattr(dense, "size"):
            return int(dense.size)
        if len(vectors) == 1:
            value = next(iter(vectors.values()))
            if hasattr(value, "size"):
                return int(value.size)
    return None
