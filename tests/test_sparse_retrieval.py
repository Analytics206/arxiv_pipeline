from types import SimpleNamespace

from qdrant_client import models

from src.retrieval.qdrant_index import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    QdrantResearchIndex,
    _rerank_for_paper_diversity,
    build_analysis_points,
)
from src.retrieval.sparse import encode_sparse_text
from src.retrieval.strategy_benchmark import load_strategy_matrix
from tests.test_research_index import make_analysis


class FakeEmbedder:
    model_name = "test-embedding"

    def embed_documents(self, texts):
        return [[0.1, 0.2] for _ in texts]

    def embed_query(self, query):
        return [0.1, 0.2]


class FakeQdrant:
    def __init__(self):
        self.created = None
        self.upserted = None
        self.query = None
        self.query_results = []

    def collection_exists(self, collection_name):
        return False

    def create_collection(self, **kwargs):
        self.created = kwargs

    def create_payload_index(self, **kwargs):
        pass

    def upsert(self, **kwargs):
        self.upserted = kwargs

    def delete(self, **kwargs):
        pass

    def query_points(self, **kwargs):
        self.query = kwargs
        return SimpleNamespace(points=self.query_results)


def test_sparse_features_are_stable_and_keep_term_frequency():
    first = encode_sparse_text("agents validate agents externally")
    second = encode_sparse_text("agents validate agents externally")
    single = encode_sparse_text("agents validate externally")

    assert first == second
    assert first.indices == sorted(first.indices)
    assert len(first.indices) == 3
    assert max(first.values) > max(single.values)


def test_hybrid_index_uses_named_dense_and_idf_sparse_vectors():
    client = FakeQdrant()
    index = QdrantResearchIndex(
        url="http://unused",
        collection_name="hybrid",
        embedder=FakeEmbedder(),
        retrieval_mode="hybrid",
        index_schema_version="2.0",
        client=client,
    )

    result = index.index_analysis(make_analysis())

    assert result["retrieval_mode"] == "hybrid"
    assert DENSE_VECTOR_NAME in client.created["vectors_config"]
    sparse_config = client.created["sparse_vectors_config"][SPARSE_VECTOR_NAME]
    assert sparse_config.modifier == models.Modifier.IDF
    assert all(
        set(point.vector) == {DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME}
        for point in client.upserted["points"]
    )
    assert all(
        point.vector[SPARSE_VECTOR_NAME].indices for point in client.upserted["points"]
    )


def test_hybrid_search_uses_weighted_rrf_and_returns_mode():
    analysis_point = make_analysis()
    payload = build_analysis_points(
        analysis_point,
        embedding_model=FakeEmbedder.model_name,
        index_schema_version="2.0",
    )[0].payload()
    client = FakeQdrant()
    client.query_results = [SimpleNamespace(id="point-a", score=0.9, payload=payload)]
    index = QdrantResearchIndex(
        url="http://unused",
        collection_name="hybrid",
        embedder=FakeEmbedder(),
        retrieval_mode="hybrid",
        rrf_dense_weight=2.0,
        rrf_sparse_weight=1.0,
        client=client,
    )

    response = index.search("external validation", limit=5)

    assert response.retrieval_mode == "hybrid"
    assert response.score_semantics == "rrf"
    assert len(client.query["prefetch"]) == 2
    assert all(item.limit == 50 for item in client.query["prefetch"])
    assert [item.using for item in client.query["prefetch"]] == [
        DENSE_VECTOR_NAME,
        SPARSE_VECTOR_NAME,
    ]
    assert client.query["query"].rrf.weights == [2.0, 1.0]
    assert response.hits[0].point_id == "point-a"


def test_diversity_reranker_can_promote_a_second_paper():
    points = [
        SimpleNamespace(score=1.0, payload={"paper_id": "paper-a"}),
        SimpleNamespace(score=0.90, payload={"paper_id": "paper-a"}),
        SimpleNamespace(score=0.89, payload={"paper_id": "paper-b"}),
        SimpleNamespace(score=0.88, payload={"paper_id": "paper-c"}),
    ]

    reranked = _rerank_for_paper_diversity(points, limit=3, penalty=0.2)

    assert [point.payload["paper_id"] for point in reranked] == [
        "paper-a",
        "paper-b",
        "paper-c",
    ]


def test_strategy_matrix_identifies_the_promoted_hybrid_strategy():
    matrix = load_strategy_matrix("evals/retrieval/hybrid_strategies_v1.json")
    selected = next(
        strategy
        for strategy in matrix.strategies
        if strategy.strategy_id == matrix.selected_strategy_id
    )

    assert selected.strategy_id == "hybrid-dense-110-diverse-20"
    assert selected.retrieval_mode == "hybrid"
    assert selected.dense_weight == 1.1
    assert selected.sparse_weight == 1.0
    assert selected.paper_diversity_penalty == 0.2
