"""Idempotent Qdrant index built from canonical MongoDB paper analyses."""

from __future__ import annotations

import hashlib
import uuid
from collections import Counter
from collections.abc import Sequence
from typing import Any, Protocol

from qdrant_client import QdrantClient, models

from src.analysis.idea_quality import (
    canonical_idea_text,
    normalize_implementation_idea,
)
from src.analysis.models import EvidenceRef, PaperAnalysis
from src.retrieval.models import (
    EvidenceSnippet,
    ImplementationIdeaFields,
    ResearchIndexPoint,
    ResearchPointKind,
    RetrievalMode,
    SearchCorpusCoverage,
    SearchScoreCalibration,
    ResearchSearchHit,
    ResearchSearchResponse,
)
from src.retrieval.sparse import SPARSE_ENCODER_VERSION, encode_sparse_text

_POINT_NAMESPACE = uuid.UUID("d2e115ed-80dd-47e4-a875-20aad852ad20")
DEFAULT_INDEX_SCHEMA_VERSION = "1.0"
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "lexical"


class EmbeddingModel(Protocol):
    model_name: str

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class ResearchIndexError(RuntimeError):
    """Raised when the index cannot preserve its schema or provenance."""


class QdrantResearchIndex:
    """Maintain and search one versioned research-knowledge collection."""

    def __init__(
        self,
        *,
        url: str,
        collection_name: str,
        embedder: EmbeddingModel,
        index_schema_version: str = DEFAULT_INDEX_SCHEMA_VERSION,
        batch_size: int = 32,
        retrieval_mode: RetrievalMode = "dense",
        hybrid_candidate_multiplier: int = 4,
        hybrid_candidate_minimum: int = 50,
        rrf_dense_weight: float = 1.0,
        rrf_sparse_weight: float = 1.0,
        rrf_k: int = 60,
        paper_diversity_penalty: float = 0.0,
        default_min_relevance: float = 0.05,
        client: Any | None = None,
    ):
        if retrieval_mode not in {"dense", "hybrid"}:
            raise ValueError("retrieval_mode must be 'dense' or 'hybrid'")
        if hybrid_candidate_multiplier < 1:
            raise ValueError("hybrid_candidate_multiplier must be at least 1")
        if hybrid_candidate_minimum < 1:
            raise ValueError("hybrid_candidate_minimum must be at least 1")
        if rrf_dense_weight <= 0 or rrf_sparse_weight <= 0:
            raise ValueError("RRF weights must be positive")
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        if not 0 <= paper_diversity_penalty <= 1:
            raise ValueError("paper_diversity_penalty must be between 0 and 1")
        if not 0 <= default_min_relevance <= 1:
            raise ValueError("default_min_relevance must be between 0 and 1")
        self.collection_name = collection_name
        self.embedder = embedder
        self.index_schema_version = index_schema_version
        self.batch_size = batch_size
        self.retrieval_mode = retrieval_mode
        self.hybrid_candidate_multiplier = hybrid_candidate_multiplier
        self.hybrid_candidate_minimum = hybrid_candidate_minimum
        self.rrf_dense_weight = rrf_dense_weight
        self.rrf_sparse_weight = rrf_sparse_weight
        self.rrf_k = rrf_k
        self.paper_diversity_penalty = paper_diversity_penalty
        self.default_min_relevance = default_min_relevance
        self.client = client or QdrantClient(url=url, timeout=60)

    def index_analysis(self, analysis: PaperAnalysis) -> dict[str, Any]:
        """Upsert current points, then remove older versions for this paper."""

        points = build_analysis_points(
            analysis,
            embedding_model=self.embedder.model_name,
            index_schema_version=self.index_schema_version,
        )
        if not points:
            raise ResearchIndexError("Analysis produced no indexable research points")

        analysis_key = points[0].analysis_key
        if self.client.collection_exists(self.collection_name):
            existing_count = self.client.count(
                collection_name=self.collection_name,
                count_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="analysis_key",
                            match=models.MatchValue(value=analysis_key),
                        )
                    ]
                ),
                exact=True,
            ).count
            if existing_count == len(points):
                dimensions = _collection_vector_size(
                    self.client.get_collection(self.collection_name),
                    vector_name=(
                        DENSE_VECTOR_NAME if self.retrieval_mode == "hybrid" else None
                    ),
                )
                return _index_result(
                    status="unchanged",
                    collection_name=self.collection_name,
                    analysis=analysis,
                    analysis_key=analysis_key,
                    embedding_model=self.embedder.model_name,
                    dimensions=dimensions,
                    points=points,
                    retrieval_mode=self.retrieval_mode,
                )

        vectors: list[list[float]] = []
        for start in range(0, len(points), self.batch_size):
            batch = points[start : start + self.batch_size]
            vectors.extend(
                self.embedder.embed_documents([point.embedding_text for point in batch])
            )
        if len(vectors) != len(points):
            raise ResearchIndexError("Embedding count does not match point count")

        dimensions = _validate_vector_dimensions(vectors)
        self._ensure_collection(dimensions)
        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=[
                models.PointStruct(
                    id=point.point_id,
                    vector=(
                        {
                            DENSE_VECTOR_NAME: vector,
                            SPARSE_VECTOR_NAME: _qdrant_sparse_vector(
                                point.embedding_text
                            ),
                        }
                        if self.retrieval_mode == "hybrid"
                        else vector
                    ),
                    payload=point.payload(),
                )
                for point, vector in zip(points, vectors, strict=True)
            ],
        )

        self.client.delete(
            collection_name=self.collection_name,
            wait=True,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="paper_id",
                            match=models.MatchValue(value=analysis.paper_id),
                        )
                    ],
                    must_not=[
                        models.FieldCondition(
                            key="analysis_key",
                            match=models.MatchValue(value=analysis_key),
                        )
                    ],
                )
            ),
        )
        return _index_result(
            status="indexed",
            collection_name=self.collection_name,
            analysis=analysis,
            analysis_key=analysis_key,
            embedding_model=self.embedder.model_name,
            dimensions=dimensions,
            points=points,
            retrieval_mode=self.retrieval_mode,
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        paper_id: str | None = None,
        kinds: Sequence[ResearchPointKind] | None = None,
        min_relevance: float | None = None,
        query_vector: Sequence[float] | None = None,
    ) -> ResearchSearchResponse:
        effective_min_relevance = (
            self.default_min_relevance
            if min_relevance is None
            else float(min_relevance)
        )
        if not 0 <= effective_min_relevance <= 1:
            raise ValueError("min_relevance must be between 0 and 1")
        query_filter = _search_filter(paper_id=paper_id, kinds=kinds)
        if self.retrieval_mode == "hybrid":
            points = self._hybrid_query(
                query,
                limit=limit,
                query_filter=query_filter,
                query_vector=query_vector,
            )
        else:
            candidate_limit = min(
                200,
                max(limit, self.hybrid_candidate_minimum, limit * 4),
            )
            result = self.client.query_points(
                collection_name=self.collection_name,
                query=(
                    list(query_vector)
                    if query_vector is not None
                    else self.embedder.embed_query(query)
                ),
                query_filter=query_filter,
                limit=candidate_limit,
                with_payload=True,
            )
            points = result.points
        candidates = [
            _search_hit(
                point,
                relevance=self._relevance(float(point.score)),
            )
            for point in points
            if point.payload is not None
        ]
        hits = [hit for hit in candidates if hit.relevance >= effective_min_relevance][
            :limit
        ]
        calibration = self._score_calibration(effective_min_relevance)
        coverage = self._corpus_coverage(
            query_filter=query_filter,
            returned_hits=len(hits),
        )
        no_match_reason = None
        if not hits:
            top_relevance = max(
                (candidate.relevance for candidate in candidates),
                default=0.0,
            )
            no_match_reason = (
                "No indexed candidate met the normalized relevance threshold "
                f"{effective_min_relevance:.3f}; top candidate relevance was "
                f"{top_relevance:.3f}. RRF relevance reflects dense/lexical "
                "retriever agreement, not a probability of topical relevance."
            )
        return ResearchSearchResponse(
            query=query,
            limit=limit,
            embedding_model=self.embedder.model_name,
            retrieval_mode=self.retrieval_mode,
            score_semantics=(
                "rrf" if self.retrieval_mode == "hybrid" else "cosine_similarity"
            ),
            score_calibration=calibration,
            result_status="matches" if hits else "no_match",
            no_match_reason=no_match_reason,
            coverage=coverage,
            hits=hits,
        )

    def _hybrid_query(
        self,
        query: str,
        *,
        limit: int,
        query_filter: models.Filter | None,
        query_vector: Sequence[float] | None = None,
    ) -> list[Any]:
        candidate_limit = min(
            200,
            max(
                limit,
                self.hybrid_candidate_minimum,
                limit * self.hybrid_candidate_multiplier,
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
                    query=_qdrant_sparse_vector(query),
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
        candidates = [point for point in result.points if point.payload is not None]
        return _rerank_for_paper_diversity(
            candidates,
            limit=candidate_limit,
            penalty=self.paper_diversity_penalty,
        )

    def _relevance(self, score: float) -> float:
        if self.retrieval_mode != "hybrid":
            return min(1.0, max(0.0, score))
        floor, ceiling = self._rrf_relevance_bounds()
        if ceiling <= floor:
            return 0.0
        return min(1.0, max(0.0, (score - floor) / (ceiling - floor)))

    def _rrf_relevance_bounds(self) -> tuple[float, float]:
        first_rank_denominator = self.rrf_k + 1
        floor = max(self.rrf_dense_weight, self.rrf_sparse_weight) / (
            first_rank_denominator
        )
        ceiling = (self.rrf_dense_weight + self.rrf_sparse_weight) / (
            first_rank_denominator
        )
        return floor, ceiling

    def _score_calibration(
        self,
        minimum_relevance: float,
    ) -> SearchScoreCalibration:
        if self.retrieval_mode == "hybrid":
            floor, ceiling = self._rrf_relevance_bounds()
            return SearchScoreCalibration(
                raw_score="rrf",
                relevance="rrf_retriever_agreement_v1",
                floor=floor,
                ceiling=ceiling,
                minimum_relevance=minimum_relevance,
                description=(
                    "Weighted reciprocal-rank fusion over dense and lexical "
                    "rankings. Scores at or below the strongest possible "
                    "single-retriever rank-one contribution map to relevance "
                    "0; the ideal dual-retriever rank-one score maps to 1. "
                    "Relevance measures retriever agreement, not topical "
                    "probability."
                ),
            )
        return SearchScoreCalibration(
            raw_score="cosine_similarity",
            relevance="cosine_clamped_v1",
            floor=0.0,
            ceiling=1.0,
            minimum_relevance=minimum_relevance,
            description=(
                "Cosine similarity clamped to the 0-1 interval. It is a "
                "ranking signal, not a calibrated topical probability."
            ),
        )

    def _corpus_coverage(
        self,
        *,
        query_filter: models.Filter | None,
        returned_hits: int,
    ) -> SearchCorpusCoverage:
        points = _safe_count(self.client, self.collection_name, None)
        papers = _safe_paper_count(self.client, self.collection_name, None)
        eligible_points = (
            points
            if query_filter is None
            else _safe_count(self.client, self.collection_name, query_filter)
        )
        eligible_papers = (
            papers
            if query_filter is None
            else _safe_paper_count(
                self.client,
                self.collection_name,
                query_filter,
            )
        )
        return SearchCorpusCoverage(
            collection=self.collection_name,
            papers=papers,
            points=points,
            eligible_papers=eligible_papers,
            eligible_points=eligible_points,
            returned_hits=returned_hits,
        )

    def _ensure_collection(self, dimensions: int) -> None:
        if not self.client.collection_exists(self.collection_name):
            vectors_config: Any = models.VectorParams(
                size=dimensions,
                distance=models.Distance.COSINE,
            )
            sparse_vectors_config = None
            if self.retrieval_mode == "hybrid":
                vectors_config = {
                    DENSE_VECTOR_NAME: models.VectorParams(
                        size=dimensions,
                        distance=models.Distance.COSINE,
                    )
                }
                sparse_vectors_config = {
                    SPARSE_VECTOR_NAME: models.SparseVectorParams(
                        modifier=models.Modifier.IDF,
                    )
                }
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=vectors_config,
                sparse_vectors_config=sparse_vectors_config,
            )
            for field_name in (
                "paper_id",
                "kind",
                "category",
                "analysis_key",
                "document_hash",
            ):
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                    wait=True,
                )
            return

        collection = self.client.get_collection(self.collection_name)
        configured_size = _collection_vector_size(
            collection,
            vector_name=(
                DENSE_VECTOR_NAME if self.retrieval_mode == "hybrid" else None
            ),
        )
        if configured_size != dimensions:
            raise ResearchIndexError(
                f"Collection {self.collection_name!r} expects "
                f"{configured_size}-dimensional vectors, but "
                f"{self.embedder.model_name!r} returned {dimensions}. Use a "
                "new versioned collection name when changing embedding models."
            )
        if self.retrieval_mode == "hybrid":
            sparse_vectors = collection.config.params.sparse_vectors or {}
            if SPARSE_VECTOR_NAME not in sparse_vectors:
                raise ResearchIndexError(
                    f"Collection {self.collection_name!r} has no "
                    f"{SPARSE_VECTOR_NAME!r} sparse vector. Use a new "
                    "versioned collection for hybrid retrieval."
                )


def build_analysis_points(
    analysis: PaperAnalysis,
    *,
    embedding_model: str,
    index_schema_version: str = DEFAULT_INDEX_SCHEMA_VERSION,
) -> list[ResearchIndexPoint]:
    """Convert an immutable analysis into deterministic retrieval points."""

    evidence_by_id = {item.evidence_id: item for item in analysis.evidence}
    analysis_key = _analysis_key(
        analysis,
        embedding_model=embedding_model,
        index_schema_version=index_schema_version,
    )
    points: list[ResearchIndexPoint] = []

    def add_point(
        *,
        kind: ResearchPointKind,
        category: str,
        text: str,
        evidence_ids: Sequence[str],
        implementation_idea: ImplementationIdeaFields | None = None,
    ) -> None:
        normalized_ids = list(
            dict.fromkeys(
                evidence_id
                for evidence_id in evidence_ids
                if evidence_id in evidence_by_id
                and not evidence_by_id[evidence_id].truncated
            )
        )
        if not normalized_ids:
            return
        snippets = [
            _evidence_snippet(evidence_by_id[evidence_id])
            for evidence_id in normalized_ids
        ]
        pages = sorted({snippet.page for snippet in snippets})
        identity = ":".join(
            [
                analysis_key,
                kind,
                category,
                hashlib.sha256(
                    (text.strip() + "\n" + "\n".join(sorted(normalized_ids))).encode(
                        "utf-8"
                    )
                ).hexdigest(),
            ]
        )
        point_id = str(uuid.uuid5(_POINT_NAMESPACE, identity))
        quote_context = "\n".join(
            f"Page {snippet.page}: {snippet.quote}" for snippet in snippets
        )
        embedding_text = (
            f"Paper: {analysis.title}\n"
            f"Type: {kind}\n"
            f"Category: {category}\n"
            f"{text.strip()}"
        )
        if quote_context:
            embedding_text += f"\nSource evidence:\n{quote_context}"
        points.append(
            ResearchIndexPoint(
                index_schema_version=index_schema_version,
                point_id=point_id,
                analysis_key=analysis_key,
                paper_id=analysis.paper_id,
                paper_version_id=analysis.paper_version_id,
                resource_uri=analysis.resource_uri,
                title=analysis.title,
                kind=kind,
                category=category,
                text=text.strip(),
                embedding_text=embedding_text,
                pages=pages,
                evidence_ids=normalized_ids,
                evidence=snippets,
                implementation_idea=implementation_idea,
                document_hash=analysis.document_hash,
                analysis_schema_version=analysis.schema_version,
                prompt_version=analysis.prompt_version,
                analysis_model=analysis.model,
                embedding_model=embedding_model,
            )
        )

    for source in analysis.evidence:
        if source.truncated:
            continue
        add_point(
            kind="evidence",
            category=source.section or "source_evidence",
            text=source.quote,
            evidence_ids=[source.evidence_id],
        )

    add_point(
        kind="claim",
        category="tldr",
        text=analysis.tldr.statement,
        evidence_ids=analysis.tldr.evidence_ids,
    )
    for category in (
        "problem",
        "contributions",
        "methods",
        "results",
        "limitations",
    ):
        for claim in getattr(analysis, category):
            add_point(
                kind="claim",
                category=category,
                text=claim.statement,
                evidence_ids=claim.evidence_ids,
            )

    for idea in analysis.implementation_ideas:
        normalized_idea = normalize_implementation_idea(idea)
        add_point(
            kind="implementation_idea",
            category="implementation_idea",
            text=canonical_idea_text(normalized_idea),
            implementation_idea=ImplementationIdeaFields(
                title=normalized_idea.title,
                description=normalized_idea.description,
                agent_use=normalized_idea.agent_use,
                expected_benefit=normalized_idea.expected_benefit,
                risks=normalized_idea.risks,
            ),
            evidence_ids=normalized_idea.evidence_ids,
        )
    return points


def _analysis_key(
    analysis: PaperAnalysis,
    *,
    embedding_model: str,
    index_schema_version: str,
) -> str:
    raw = ":".join(
        [
            analysis.paper_id,
            analysis.document_hash,
            analysis.schema_version,
            analysis.prompt_version,
            analysis.model,
            embedding_model,
            index_schema_version,
        ]
    ).encode("utf-8")
    return f"research_{hashlib.sha256(raw).hexdigest()}"


def _index_result(
    *,
    status: str,
    collection_name: str,
    analysis: PaperAnalysis,
    analysis_key: str,
    embedding_model: str,
    dimensions: int,
    points: Sequence[ResearchIndexPoint],
    retrieval_mode: RetrievalMode,
) -> dict[str, Any]:
    return {
        "status": status,
        "collection": collection_name,
        "paper_id": analysis.paper_id,
        "analysis_key": analysis_key,
        "embedding_model": embedding_model,
        "retrieval_mode": retrieval_mode,
        "sparse_encoder": (
            SPARSE_ENCODER_VERSION if retrieval_mode == "hybrid" else None
        ),
        "vector_size": dimensions,
        "points": len(points),
        "kinds": {
            kind: sum(point.kind == kind for point in points)
            for kind in ("evidence", "claim", "implementation_idea")
        },
    }


def _evidence_snippet(source: EvidenceRef) -> EvidenceSnippet:
    return EvidenceSnippet(
        evidence_id=source.evidence_id,
        page=source.page,
        quote=source.quote,
        supporting_quote=source.supporting_quote,
        truncated=source.truncated,
        section=source.section,
    )


def _validate_vector_dimensions(vectors: Sequence[Sequence[float]]) -> int:
    if not vectors or not vectors[0]:
        raise ResearchIndexError("Embedding model returned no vectors")
    dimensions = len(vectors[0])
    if any(len(vector) != dimensions for vector in vectors):
        raise ResearchIndexError("Embedding vectors have inconsistent dimensions")
    return dimensions


def _collection_vector_size(
    collection: Any,
    *,
    vector_name: str | None = None,
) -> int:
    vectors = collection.config.params.vectors
    if hasattr(vectors, "size"):
        if vector_name is not None:
            raise ResearchIndexError(
                "Collection uses an unnamed dense vector, not a hybrid schema"
            )
        return int(vectors.size)
    if isinstance(vectors, dict):
        if vector_name is not None and vector_name in vectors:
            return int(vectors[vector_name].size)
        if vector_name is None and len(vectors) == 1:
            return int(next(iter(vectors.values())).size)
    raise ResearchIndexError("Research collection has an unsupported vector layout")


def _qdrant_sparse_vector(text: str) -> models.SparseVector:
    vector = encode_sparse_text(text)
    return models.SparseVector(
        indices=vector.indices,
        values=vector.values,
    )


def _rerank_for_paper_diversity(
    points: Sequence[Any],
    *,
    limit: int,
    penalty: float,
) -> list[Any]:
    if penalty <= 0 or len(points) <= 1:
        return list(points[:limit])

    scores = [float(point.score) for point in points]
    maximum = max(scores)
    minimum = min(scores)
    span = maximum - minimum
    normalized = [(score - minimum) / span if span > 0 else 1.0 for score in scores]
    remaining = list(range(len(points)))
    selected: list[int] = []
    paper_counts: Counter[str] = Counter()
    while remaining and len(selected) < limit:
        best = max(
            remaining,
            key=lambda index: (
                normalized[index]
                - penalty
                * paper_counts[str(points[index].payload.get("paper_id", ""))],
                -index,
            ),
        )
        selected.append(best)
        paper_counts[str(points[best].payload.get("paper_id", ""))] += 1
        remaining.remove(best)
    return [points[index] for index in selected]


def _search_filter(
    *,
    paper_id: str | None,
    kinds: Sequence[ResearchPointKind] | None,
) -> models.Filter | None:
    conditions: list[models.FieldCondition] = []
    if paper_id:
        conditions.append(
            models.FieldCondition(
                key="paper_id",
                match=models.MatchValue(value=paper_id),
            )
        )
    if kinds:
        conditions.append(
            models.FieldCondition(
                key="kind",
                match=models.MatchAny(any=list(dict.fromkeys(kinds))),
            )
        )
    return models.Filter(must=conditions) if conditions else None


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


def _safe_paper_count(
    client: Any,
    collection_name: str,
    query_filter: models.Filter | None,
) -> int | None:
    try:
        response = client.facet(
            collection_name=collection_name,
            key="paper_id",
            facet_filter=query_filter,
            limit=1_000,
            exact=True,
        )
        return len(response.hits)
    except Exception:
        return None


def _search_hit(point: Any, *, relevance: float) -> ResearchSearchHit:
    payload = point.payload
    return ResearchSearchHit(
        point_id=str(point.id),
        score=float(point.score),
        relevance=relevance,
        paper_id=payload["paper_id"],
        paper_version_id=payload["paper_version_id"],
        resource_uri=payload["resource_uri"],
        title=payload["title"],
        kind=payload["kind"],
        category=payload["category"],
        text=payload["text"],
        pages=payload.get("pages", []),
        evidence_ids=payload.get("evidence_ids", []),
        evidence=payload.get("evidence", []),
        implementation_idea=payload.get("implementation_idea"),
        document_hash=payload["document_hash"],
        prompt_version=payload["prompt_version"],
        analysis_model=payload["analysis_model"],
        embedding_model=payload["embedding_model"],
    )
