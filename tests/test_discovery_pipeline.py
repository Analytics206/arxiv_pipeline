import pytest

import src.pipeline.index_arxiv_discovery as discovery_pipeline
from src.pipeline.index_arxiv_discovery import build_parser as build_index_parser
from src.pipeline.index_arxiv_discovery import (
    physical_collection_name,
    run_discovery_index,
)
from src.pipeline.prepare_kaggle_corpus import build_parser as build_prepare_parser


class FakeCheckpointCollection:
    def __init__(self):
        self.document = None

    def find_one(self, query):
        if self.document and self.document["_id"] == query["_id"]:
            return dict(self.document)
        return None

    def update_one(self, query, update, upsert=False):
        document = dict(self.document or {"_id": query["_id"]})
        document.update(update.get("$setOnInsert", {}))
        document.update(update.get("$set", {}))
        self.document = document


class FakeDatabase:
    def __init__(self):
        self.checkpoints = FakeCheckpointCollection()

    def __getitem__(self, name):
        assert name == "discovery_index_runs"
        return self.checkpoints


class FakeRepository:
    def __init__(self, prepared=True, documents=2):
        self.prepared = prepared
        self.documents = documents
        self.batch_calls = []

    def snapshot_identity(self):
        return {
            "corpus_run_id": "run-1" if self.prepared else None,
            "retention_policy_hash": "hash",
            "documents": self.documents,
            "candidate_documents": 10,
            "eligibility_documents": self.documents,
            "eligibility_collection": "papers",
            "eligibility_id_field": "base_arxiv_id",
            "snapshot_token": "snapshot",
            "prepared": self.prepared,
        }

    def iter_batches(self, **kwargs):
        self.batch_calls.append(kwargs)
        documents = [
            {"id": str(position)}
            for position in range(1, self.documents + 1)
        ]
        if kwargs.get("after_id"):
            documents = [
                document
                for document in documents
                if document["id"] > kwargs["after_id"]
            ]
        limit = kwargs.get("limit")
        if limit is not None:
            documents = documents[:limit]
        batch_size = kwargs["batch_size"]
        for offset in range(0, len(documents), batch_size):
            yield documents[offset : offset + batch_size]


class FakeIndex:
    def __init__(self, *, exists=False, points=0):
        self.batch_size = 32
        self.collection_exists = exists
        self.points = points
        self.activated = False

    def index_documents(self, documents):
        self.collection_exists = True
        self.points += len(documents)
        return {"points": len(documents)}

    def count(self):
        return self.points

    def exists(self):
        return self.collection_exists

    def activate_alias(self):
        self.activated = True


CONFIG = {
    "research_index": {"embedding_model": "model"},
    "discovery_index": {
        "collection_prefix": "discovery_v1",
        "alias_name": "discovery_current",
        "schema_version": "1.0",
        "embedding_batch_size": 32,
        "checkpoint_collection": "discovery_index_runs",
    },
}


def test_physical_collection_changes_with_snapshot_or_model():
    first = physical_collection_name(
        prefix="discovery_v1",
        snapshot_token="one",
        embedding_model="model-a",
        schema_version="1.0",
    )
    second = physical_collection_name(
        prefix="discovery_v1",
        snapshot_token="two",
        embedding_model="model-a",
        schema_version="1.0",
    )

    assert first.startswith("discovery_v1_")
    assert first != second


def test_index_dry_run_does_not_require_prepared_source_or_services():
    report = run_discovery_index(
        CONFIG,
        repository=FakeRepository(prepared=False),
        database=FakeDatabase(),
        dry_run=True,
    )

    assert report["status"] == "dry-run"
    assert report["source_documents"] == 2
    assert report["candidate_documents"] == 10
    assert report["eligibility_collection"] == "papers"


def test_unprepared_source_is_rejected_before_index_creation():
    with pytest.raises(RuntimeError, match="cleanup output"):
        run_discovery_index(
            CONFIG,
            repository=FakeRepository(prepared=False),
            database=FakeDatabase(),
        )


def test_empty_papers_intersection_is_rejected_before_index_creation():
    with pytest.raises(RuntimeError, match="nothing is eligible"):
        run_discovery_index(
            CONFIG,
            repository=FakeRepository(documents=0),
            database=FakeDatabase(),
        )


def test_complete_index_activates_alias_and_persists_checkpoint(monkeypatch):
    repository = FakeRepository()
    database = FakeDatabase()
    index = FakeIndex()
    monkeypatch.setattr(
        discovery_pipeline,
        "create_discovery_index",
        lambda *args, **kwargs: index,
    )

    report = run_discovery_index(
        CONFIG,
        repository=repository,
        database=database,
    )

    assert report["status"] == "complete"
    assert report["points"] == 2
    assert report["alias_activated"] is True
    assert index.activated is True
    assert database.checkpoints.document["status"] == "complete"


def test_missing_qdrant_collection_restarts_stale_checkpoint(monkeypatch):
    repository = FakeRepository()
    database = FakeDatabase()
    database.checkpoints.document = {
        "_id": physical_collection_name(
            prefix="discovery_v1",
            snapshot_token="snapshot",
            embedding_model="model",
            schema_version="1.0",
        ),
        "processed": 1,
        "last_id": "1",
    }
    index = FakeIndex(exists=False)
    monkeypatch.setattr(
        discovery_pipeline,
        "create_discovery_index",
        lambda *args, **kwargs: index,
    )

    report = run_discovery_index(
        CONFIG,
        repository=repository,
        database=database,
    )

    assert report["processed"] == 2
    assert repository.batch_calls[0]["after_id"] is None


def test_run_papers_limits_only_this_invocation_and_keeps_alias_inactive(
    monkeypatch,
):
    repository = FakeRepository(documents=3)
    database = FakeDatabase()
    index = FakeIndex()
    monkeypatch.setattr(
        discovery_pipeline,
        "create_discovery_index",
        lambda *args, **kwargs: index,
    )

    first = run_discovery_index(
        CONFIG,
        repository=repository,
        database=database,
        run_papers=1,
    )
    second = run_discovery_index(
        CONFIG,
        repository=repository,
        database=database,
        run_papers=1,
    )

    assert first["status"] == "partial"
    assert first["run_processed"] == 1
    assert first["remaining_documents"] == 2
    assert first["alias_activated"] is False
    assert second["processed"] == 2
    assert second["run_started_processed"] == 1
    assert second["run_processed"] == 1
    assert second["remaining_documents"] == 1
    assert index.activated is False


def test_run_minutes_stops_at_a_batch_boundary(monkeypatch):
    repository = FakeRepository(documents=3)
    database = FakeDatabase()
    index = FakeIndex()
    clock = iter([0.0, 61.0, 61.0])
    monkeypatch.setattr(
        discovery_pipeline,
        "create_discovery_index",
        lambda *args, **kwargs: index,
    )
    monkeypatch.setattr(
        discovery_pipeline,
        "perf_counter",
        lambda: next(clock),
    )

    report = run_discovery_index(
        CONFIG,
        repository=repository,
        database=database,
        batch_size=1,
        run_minutes=1,
    )

    assert report["status"] == "partial"
    assert report["run_processed"] == 1
    assert report["run_elapsed_seconds"] == 61
    assert report["remaining_documents"] == 2
    assert report["alias_activated"] is False


def test_index_and_prepare_clis_are_import_safe():
    index_args = build_index_parser().parse_args(
        ["--dry-run", "--run-minutes", "75"]
    )
    prepare_args = build_prepare_parser().parse_args(
        ["--apply", "--index", "--max-papers", "10"]
    )

    assert index_args.dry_run is True
    assert index_args.run_minutes == 75
    assert prepare_args.apply is True
    assert prepare_args.index is True
    assert prepare_args.max_papers == 10
