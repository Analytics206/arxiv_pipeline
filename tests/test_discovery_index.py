from types import SimpleNamespace

import pytest
from qdrant_client import models

from src.retrieval.qdrant_discovery import (
    DiscoveryIndexError,
    QdrantDiscoveryIndex,
    build_discovery_point,
)
from src.retrieval.qdrant_index import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME

DOCUMENT = {
    "id": "2607.12345",
    "title": "  Retrieval   for Agents ",
    "abstract": " A hybrid system combines semantic and lexical search. ",
    "category_codes": ["cs.AI", "cs.LG"],
    "primary_category": "cs.AI",
    "update_date": "2026-07-20",
    "update_year": 2026,
    "latest_version": "v2",
    "corpus_run_id": "run-1",
}


class FakeEmbedder:
    model_name = "test-embedding"

    def embed_documents(self, texts):
        return [[0.1, 0.2] for _ in texts]

    def embed_query(self, query):
        return [0.1, 0.2]


class FakeQdrant:
    def __init__(self, *, existing_collection=None):
        self.created = None
        self.payload_indexes = []
        self.upserted = None
        self.query = None
        self.query_results = []
        self.alias_operations = None
        self.existing_collection = existing_collection

    def collection_exists(self, collection_name):
        return self.existing_collection is not None

    def get_collection(self, collection_name):
        return self.existing_collection

    def create_collection(self, **kwargs):
        self.created = kwargs

    def create_payload_index(self, **kwargs):
        self.payload_indexes.append(kwargs)

    def upsert(self, **kwargs):
        self.upserted = kwargs

    def query_points(self, **kwargs):
        self.query = kwargs
        return SimpleNamespace(points=self.query_results)

    def count(self, **kwargs):
        return SimpleNamespace(count=1)

    def get_aliases(self):
        return SimpleNamespace(
            aliases=[SimpleNamespace(alias_name="arxiv_discovery_current")]
        )

    def update_collection_aliases(self, **kwargs):
        self.alias_operations = kwargs["change_aliases_operations"]


def make_index(client):
    return QdrantDiscoveryIndex(
        url="http://unused",
        collection_name="arxiv_discovery_hybrid_v1_run",
        alias_name="arxiv_discovery_current",
        embedder=FakeEmbedder(),
        client=client,
    )


def test_discovery_point_is_stable_and_keeps_embedding_payload_lean():
    first = build_discovery_point(
        DOCUMENT,
        embedding_model=FakeEmbedder.model_name,
    )
    second = build_discovery_point(
        DOCUMENT,
        embedding_model=FakeEmbedder.model_name,
    )

    assert first.point_id == second.point_id
    assert first.paper_id == "2607.12345"
    assert first.title == "Retrieval for Agents"
    assert first.embedding_text.startswith("Title: Retrieval for Agents")
    assert "abstract" not in first.payload()
    assert "embedding_text" not in first.payload()
    assert first.categories == ["cs.AI", "cs.LG"]


def test_discovery_index_uses_hybrid_vectors_and_filterable_payloads():
    client = FakeQdrant()
    index = make_index(client)

    result = index.index_documents([DOCUMENT])

    assert result["points"] == 1
    assert set(client.created["vectors_config"]) == {DENSE_VECTOR_NAME}
    assert set(client.created["sparse_vectors_config"]) == {SPARSE_VECTOR_NAME}
    assert {item["field_name"] for item in client.payload_indexes} == {
        "paper_id",
        "categories",
        "primary_category",
        "update_year",
        "source",
    }
    point = client.upserted["points"][0]
    assert set(point.vector) == {DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME}
    assert point.payload["paper_id"] == "2607.12345"


def test_discovery_search_uses_category_and_year_filters():
    client = FakeQdrant()
    payload = build_discovery_point(
        DOCUMENT,
        embedding_model=FakeEmbedder.model_name,
    ).payload()
    client.query_results = [SimpleNamespace(id="point-1", score=0.9, payload=payload)]
    index = make_index(client)

    response = index.search(
        "hybrid agent retrieval",
        categories=["cs.AI"],
        start_year=2025,
        limit=5,
    )

    assert response.result_status == "matches"
    assert response.hits[0].tier == "metadata_only"
    query_filter = client.query["prefetch"][0].filter
    assert len(query_filter.must) == 2
    assert isinstance(query_filter.must[0].match, models.MatchAny)
    assert query_filter.must[1].range.gte == 2025


def test_alias_activation_deletes_previous_alias_and_creates_current():
    client = FakeQdrant()
    index = make_index(client)

    index.activate_alias()

    assert len(client.alias_operations) == 2
    assert isinstance(client.alias_operations[0], models.DeleteAliasOperation)
    assert isinstance(client.alias_operations[1], models.CreateAliasOperation)


def test_resume_rejects_collection_without_sparse_vector_contract():
    existing = SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(
                vectors={
                    DENSE_VECTOR_NAME: SimpleNamespace(size=2),
                },
                sparse_vectors={},
            )
        )
    )
    index = make_index(FakeQdrant(existing_collection=existing))

    with pytest.raises(DiscoveryIndexError, match="missing"):
        index.index_documents([DOCUMENT])
