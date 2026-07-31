"""Hybrid Qdrant index for paper-level Kaggle metadata discovery."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Sequence
from typing import Any, Protocol

from qdrant_client import QdrantClient, models

from src.analysis.identity import normalize_arxiv_id
from src.ingestion.kaggle_corpus import normalize_category_tokens
from src.retrieval.discovery_models import (
    DiscoveryCorpusCoverage,
    DiscoveryIndexPoint,
    DiscoverySearchHit,
    DiscoverySearchResponse,
)
from src.retrieval.qdrant_index import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from src.retrieval.sparse import encode_sparse_text

_DISCOVERY_NAMESPACE = uuid.UUID("f5d60370-7512-45fc-a379-24f40c45aeac")
DEFAULT_DISCOVERY_SCHEMA_VERSION = "1.0"


class DiscoveryEmbeddingModel(Protocol):
    model_name: str

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class DiscoveryIndexError(RuntimeError):
    """Raised when discovery indexing cannot preserve its contract."""


def build_discovery_point(
    document: dict[str, Any],
    *,
    embedding_model: str,
    index_schema_version: str = DEFAULT_DISCOVERY_SCHEMA_VERSION,
) -> DiscoveryIndexPoint:
    """Normalize one cleaned Kaggle document into a deterministic point."""

    identity = normalize_arxiv_id(str(document.get("id") or ""))
    title = _normalize_text(document.get("title"))
    abstract = _normalize_text(document.get("abstract"))
    if not title or not abstract:
        raise ValueError(f"Paper {identity.base_id!r} requires title and abstract")
    categories = normalize_category_tokens(
        document.get("category_codes", document.get("categories"))
    )
    update_year = document.get("update_year")
    if update_year is None:
        match = re.match(r"^(\d{4})", str(document.get("update_date") or ""))
        update_year = int(match.group(1)) if match else None
    latest_version = document.get("latest_version")
    if latest_version is None:
        versions = document.get("versions")
        if isinstance(versions, list) and versions:
            latest = versions[-1]
            if isinstance(latest, dict):
                latest_version = latest.get("version")

    embedding_text = f"Title: {title}\nAbstract: {abstract}"
    metadata_values = {
        "paper_id": identity.base_id,
        "title": title,
        "abstract": abstract,
        "categories": categories,
        "update_date": document.get("update_date"),
        "latest_version": latest_version,
    }
    metadata_hash = hashlib.sha256(
        json.dumps(
            metadata_values,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return DiscoveryIndexPoint(
        index_schema_version=index_schema_version,
        point_id=str(uuid.uuid5(_DISCOVERY_NAMESPACE, identity.base_id)),
        paper_id=identity.base_id,
        title=title,
        embedding_text=embedding_text,
        categories=categories,
        primary_category=(
            str(document.get("primary_category"))
            if document.get("primary_category")
            else (categories[0] if categories else None)
        ),
        update_date=(
            str(document.get("update_date")) if document.get("update_date") else None
        ),
        update_year=int(update_year) if update_year is not None else None,
        latest_version=str(latest_version) if latest_version else None,
        corpus_run_id=(
            str(document.get("corpus_run_id"))
            if document.get("corpus_run_id")
            else None
        ),
        metadata_hash=metadata_hash,
        embedding_model=embedding_model,
    )


class QdrantDiscoveryIndex:
    """Maintain and search one paper-level hybrid discovery collection."""

    def __init__(
        self,
        *,
        url: str,
        collection_name: str,
        alias_name: str,
        embedder: DiscoveryEmbeddingModel,
        index_schema_version: str = DEFAULT_DISCOVERY_SCHEMA_VERSION,
        batch_size: int = 32,
        candidate_multiplier: int = 4,
        candidate_minimum: int = 50,
        rrf_dense_weight: float = 1.1,
        rrf_sparse_weight: float = 1.0,
        rrf_k: int = 60,
        default_min_relevance: float = 0.05,
        client: Any | None = None,
    ):
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if candidate_multiplier < 1 or candidate_minimum < 1:
            raise ValueError("candidate sizing must be positive")
        if rrf_dense_weight <= 0 or rrf_sparse_weight <= 0:
            raise ValueError("RRF weights must be positive")
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        if not 0 <= default_min_relevance <= 1:
            raise ValueError("default_min_relevance must be between 0 and 1")
        self.collection_name = collection_name
        self.alias_name = alias_name
        self.embedder = embedder
        self.index_schema_version = index_schema_version
        self.batch_size = batch_size
        self.candidate_multiplier = candidate_multiplier
        self.candidate_minimum = candidate_minimum
        self.rrf_dense_weight = rrf_dense_weight
        self.rrf_sparse_weight = rrf_sparse_weight
        self.rrf_k = rrf_k
        self.default_min_relevance = default_min_relevance
        self.client = client or QdrantClient(url=url, timeout=60)

    def index_documents(
        self,
        documents: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        """Upsert one bounded batch of cleaned metadata documents."""

        points = [
            build_discovery_point(
                document,
                embedding_model=self.embedder.model_name,
                index_schema_version=self.index_schema_version,
            )
            for document in documents
        ]
        if not points:
            return {
                "status": "empty",
                "collection": self.collection_name,
                "points": 0,
            }
        vectors: list[list[float]] = []
        for start in range(0, len(points), self.batch_size):
            batch = points[start : start + self.batch_size]
            vectors.extend(
                self.embedder.embed_documents([point.embedding_text for point in batch])
            )
        if len(vectors) != len(points):
            raise DiscoveryIndexError("Embedding count does not match point count")
        dimensions = _validate_dimensions(vectors)
        self._ensure_collection(dimensions)
        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=[
                models.PointStruct(
                    id=point.point_id,
                    vector={
                        DENSE_VECTOR_NAME: vector,
                        SPARSE_VECTOR_NAME: _sparse_vector(point.embedding_text),
                    },
                    payload=point.payload(),
                )
                for point, vector in zip(points, vectors, strict=True)
            ],
        )
        return {
            "status": "indexed",
            "collection": self.collection_name,
            "points": len(points),
            "vector_size": dimensions,
            "first_paper_id": points[0].paper_id,
            "last_paper_id": points[-1].paper_id,
        }

    def activate_alias(self) -> None:
        """Atomically make this validated physical collection current."""

        aliases = self.client.get_aliases().aliases
        operations: list[Any] = []
        if any(alias.alias_name == self.alias_name for alias in aliases):
            operations.append(
                models.DeleteAliasOperation(
                    delete_alias=models.DeleteAlias(
                        alias_name=self.alias_name,
                    )
                )
            )
        operations.append(
            models.CreateAliasOperation(
                create_alias=models.CreateAlias(
                    collection_name=self.collection_name,
                    alias_name=self.alias_name,
                )
            )
        )
        self.client.update_collection_aliases(
            change_aliases_operations=operations,
        )

    def count(self) -> int:
        return int(
            self.client.count(
                collection_name=self.collection_name,
                exact=True,
            ).count
        )

    def exists(self) -> bool:
        """Return whether the configured physical collection exists."""

        return bool(self.client.collection_exists(self.collection_name))

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        paper_id: str | None = None,
        categories: Sequence[str] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        min_relevance: float | None = None,
        query_vector: Sequence[float] | None = None,
    ) -> DiscoverySearchResponse:
        if limit < 1:
            raise ValueError("limit must be positive")
        if start_year is not None and end_year is not None and start_year > end_year:
            raise ValueError("start_year cannot be later than end_year")
        effective_minimum = (
            self.default_min_relevance
            if min_relevance is None
            else float(min_relevance)
        )
        if not 0 <= effective_minimum <= 1:
            raise ValueError("min_relevance must be between 0 and 1")
        query_filter = _discovery_filter(
            paper_id=paper_id,
            categories=categories,
            start_year=start_year,
            end_year=end_year,
        )
        candidate_limit = min(
            200,
            max(
                limit,
                self.candidate_minimum,
                limit * self.candidate_multiplier,
            ),
        )
        result = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=(
                        list(query_vector)
                        if query_vector is not None
                        else self.embedder.embed_query(query)
                    ),
                    using=DENSE_VECTOR_NAME,
                    filter=query_filter,
                    limit=candidate_limit,
                ),
                models.Prefetch(
                    query=_sparse_vector(query),
                    using=SPARSE_VECTOR_NAME,
                    filter=query_filter,
                    limit=candidate_limit,
                ),
            ],
            query=models.RrfQuery(
                rrf=models.Rrf(
                    k=self.rrf_k,
                    weights=[
                        self.rrf_dense_weight,
                        self.rrf_sparse_weight,
                    ],
                )
            ),
            limit=candidate_limit,
            with_payload=True,
        )
        candidates = [
            _discovery_hit(point, relevance=self._relevance(float(point.score)))
            for point in result.points
            if point.payload is not None
        ]
        hits = [hit for hit in candidates if hit.relevance >= effective_minimum][:limit]
        no_match_reason = None
        if not hits:
            top_relevance = max(
                (candidate.relevance for candidate in candidates),
                default=0.0,
            )
            no_match_reason = (
                "No metadata-only candidate met the normalized relevance "
                f"threshold {effective_minimum:.3f}; top candidate relevance "
                f"was {top_relevance:.3f}."
            )
        eligible = _safe_count(
            self.client,
            self.collection_name,
            query_filter,
        )
        return DiscoverySearchResponse(
            query=query,
            limit=limit,
            embedding_model=self.embedder.model_name,
            result_status="matches" if hits else "no_match",
            no_match_reason=no_match_reason,
            coverage=DiscoveryCorpusCoverage(
                collection=self.collection_name,
                eligible_points=eligible,
                returned_hits=len(hits),
            ),
            hits=hits,
        )

    def _ensure_collection(self, dimensions: int) -> None:
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    DENSE_VECTOR_NAME: models.VectorParams(
                        size=dimensions,
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    SPARSE_VECTOR_NAME: models.SparseVectorParams(
                        modifier=models.Modifier.IDF,
                    )
                },
            )
            for field_name, field_schema in (
                ("paper_id", models.PayloadSchemaType.KEYWORD),
                ("categories", models.PayloadSchemaType.KEYWORD),
                ("primary_category", models.PayloadSchemaType.KEYWORD),
                ("update_year", models.PayloadSchemaType.INTEGER),
                ("source", models.PayloadSchemaType.KEYWORD),
            ):
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                    wait=True,
                )
            return
        collection = self.client.get_collection(self.collection_name)
        configured = _dense_size(collection)
        if configured != dimensions:
            raise DiscoveryIndexError(
                f"Collection {self.collection_name!r} expects {configured} "
                f"dimensions, but {self.embedder.model_name!r} returned "
                f"{dimensions}"
            )
        sparse_vectors = getattr(
            collection.config.params,
            "sparse_vectors",
            None,
        )
        if (
            not isinstance(sparse_vectors, dict)
            or SPARSE_VECTOR_NAME not in sparse_vectors
        ):
            raise DiscoveryIndexError(
                f"Collection {self.collection_name!r} is missing the "
                f"{SPARSE_VECTOR_NAME!r} sparse vector"
            )

    def _relevance(self, score: float) -> float:
        denominator = self.rrf_k + 1
        floor = max(self.rrf_dense_weight, self.rrf_sparse_weight) / denominator
        ceiling = (self.rrf_dense_weight + self.rrf_sparse_weight) / denominator
        if ceiling <= floor:
            return 0.0
        return min(1.0, max(0.0, (score - floor) / (ceiling - floor)))


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _validate_dimensions(vectors: Sequence[Sequence[float]]) -> int:
    if not vectors or not vectors[0]:
        raise DiscoveryIndexError("Embedding model returned no vectors")
    dimensions = len(vectors[0])
    if any(len(vector) != dimensions for vector in vectors):
        raise DiscoveryIndexError("Embedding vectors have inconsistent dimensions")
    return dimensions


def _dense_size(collection: Any) -> int:
    vectors = collection.config.params.vectors
    if isinstance(vectors, dict) and DENSE_VECTOR_NAME in vectors:
        return int(vectors[DENSE_VECTOR_NAME].size)
    raise DiscoveryIndexError("Discovery collection has an unsupported vector layout")


def _sparse_vector(text: str) -> models.SparseVector:
    vector = encode_sparse_text(text)
    return models.SparseVector(
        indices=vector.indices,
        values=vector.values,
    )


def _discovery_filter(
    *,
    paper_id: str | None,
    categories: Sequence[str] | None,
    start_year: int | None,
    end_year: int | None,
) -> models.Filter | None:
    conditions: list[Any] = []
    if paper_id:
        conditions.append(
            models.FieldCondition(
                key="paper_id",
                match=models.MatchValue(value=normalize_arxiv_id(paper_id).base_id),
            )
        )
    selected_categories = [
        category.strip()
        for category in categories or []
        if category and category.strip()
    ]
    if selected_categories:
        conditions.append(
            models.FieldCondition(
                key="categories",
                match=models.MatchAny(any=list(dict.fromkeys(selected_categories))),
            )
        )
    if start_year is not None or end_year is not None:
        conditions.append(
            models.FieldCondition(
                key="update_year",
                range=models.Range(
                    gte=start_year,
                    lte=end_year,
                ),
            )
        )
    return models.Filter(must=conditions) if conditions else None


def _discovery_hit(point: Any, *, relevance: float) -> DiscoverySearchHit:
    payload = point.payload
    return DiscoverySearchHit(
        point_id=str(point.id),
        score=float(point.score),
        relevance=relevance,
        paper_id=payload["paper_id"],
        title=payload["title"],
        categories=payload.get("categories", []),
        primary_category=payload.get("primary_category"),
        update_date=payload.get("update_date"),
        update_year=payload.get("update_year"),
        latest_version=payload.get("latest_version"),
        source=payload.get("source", "arxiv_kaggle"),
        corpus_run_id=payload.get("corpus_run_id"),
        metadata_hash=payload["metadata_hash"],
    )


def _safe_count(
    client: Any,
    collection_name: str,
    query_filter: models.Filter | None,
) -> int | None:
    try:
        return int(
            client.count(
                collection_name=collection_name,
                count_filter=query_filter,
                exact=True,
            ).count
        )
    except Exception:
        return None
