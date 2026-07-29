from types import SimpleNamespace

import pytest

from src.ingestion.kaggle_corpus import (
    KaggleCorpusCleaner,
    KaggleCorpusError,
    KaggleRetentionPolicy,
    build_filter_pipeline,
    build_retention_query,
    document_matches_policy,
    normalize_category_tokens,
)
from src.pipeline.clean_kaggle_collection import build_parser


def make_policy(**updates):
    values = {
        "retained_categories": ("cs.AI", "cs.LG", "cs.CV"),
        "minimum_fraction": 0.01,
        "maximum_fraction": 0.30,
    }
    values.update(updates)
    return KaggleRetentionPolicy(**values)


def test_category_tokens_are_exact_and_deduplicated():
    assert normalize_category_tokens("cs.AI  cs.LG cs.AI") == [
        "cs.AI",
        "cs.LG",
    ]
    assert document_matches_policy(
        {"categories": "math.OC cs.AI"},
        make_policy(),
    )
    assert not document_matches_policy(
        {"categories": "cs.AI2 math.OC"},
        make_policy(),
    )


def test_any_and_all_category_modes_are_distinct():
    document = {"categories": "cs.AI cs.LG"}

    assert document_matches_policy(document, make_policy())
    assert not document_matches_policy(
        document,
        make_policy(category_match="all"),
    )


def test_optional_date_window_is_applied_after_categories():
    policy = make_policy(start_date="2021-01-01", end_date="2025-12-31")

    assert document_matches_policy(
        {"categories": "cs.CV", "update_date": "2025-01-01"},
        policy,
    )
    assert not document_matches_policy(
        {"categories": "cs.CV", "update_date": "2026-01-01"},
        policy,
    )


def test_policy_requires_categories_and_valid_guardrails():
    with pytest.raises(ValueError, match="At least one"):
        KaggleRetentionPolicy(retained_categories=())
    with pytest.raises(ValueError, match="minimum_fraction"):
        make_policy(minimum_fraction=0.5, maximum_fraction=0.1)


def test_mongodb_pipeline_filters_then_normalizes_then_outputs():
    policy = make_policy()

    query = build_retention_query(policy)
    pipeline = build_filter_pipeline(
        policy,
        output_collection="arxiv_kaggle__filtered_test",
    )

    assert "$expr" in query
    assert pipeline[0] == {"$match": query}
    assert set(pipeline[1]["$set"]) == {
        "category_codes",
        "primary_category",
        "version_count",
        "latest_version",
        "update_year",
        "retention_policy_hash",
    }
    assert pipeline[-1] == {"$out": "arxiv_kaggle__filtered_test"}


class FakeCollection:
    def __init__(self, total, retained):
        self.total = total
        self.retained = retained
        self.count_queries = []

    def count_documents(self, query, **kwargs):
        self.count_queries.append((query, kwargs))
        return self.total if not query else self.retained


class FakeDatabase:
    name = "arxiv_papers"

    def __init__(self, collection):
        self.collection = collection
        self.client = SimpleNamespace(admin=None)

    def list_collection_names(self):
        return ["arxiv_kaggle"]

    def __getitem__(self, name):
        assert name == "arxiv_kaggle"
        return self.collection


def test_cleaner_dry_run_is_read_only_and_reports_guard_status():
    collection = FakeCollection(total=100, retained=17)
    cleaner = KaggleCorpusCleaner(FakeDatabase(collection))

    report = cleaner.clean(
        source_collection="arxiv_kaggle",
        policy=make_policy(),
    )

    assert report["dry_run"] is True
    assert report["status"] == "ready"
    assert report["documents_retained"] == 17
    assert report["documents_removed"] == 83
    assert report["retention_fraction"] == 0.17
    assert len(collection.count_queries) == 2


def test_apply_is_rejected_before_writes_when_retention_is_surprising():
    collection = FakeCollection(total=100, retained=80)
    cleaner = KaggleCorpusCleaner(FakeDatabase(collection))

    with pytest.raises(KaggleCorpusError, match="Retention guard"):
        cleaner.clean(
            source_collection="arxiv_kaggle",
            policy=make_policy(),
            apply=True,
        )


def test_cleanup_cli_is_dry_run_by_default():
    default = build_parser().parse_args([])
    applied = build_parser().parse_args(
        [
            "--category",
            "cs.AI",
            "--category",
            "cs.LG",
            "--source-collection",
            "arxiv_kaggle_import",
            "--target-collection",
            "arxiv_kaggle",
            "--apply",
        ]
    )

    assert default.apply is False
    assert applied.apply is True
    assert applied.categories == ["cs.AI", "cs.LG"]
    assert applied.source_collection == "arxiv_kaggle_import"
    assert applied.target_collection == "arxiv_kaggle"


class ApplyCollection:
    def __init__(self, database, *, source=False):
        self.database = database
        self.source = source
        self.indexes = []

    def count_documents(self, query, **kwargs):
        if self.source:
            return 100 if not query else 17
        if not query:
            return 17
        return 0

    def aggregate(self, pipeline, **kwargs):
        if self.source:
            output_name = pipeline[-1]["$out"]
            self.database.collections[output_name] = ApplyCollection(self.database)
        return []

    def create_index(self, keys, **kwargs):
        self.indexes.append((keys, kwargs))


class ApplyStats:
    def __init__(self):
        self.documents = {}

    def update_one(self, query, update, upsert=False):
        document = dict(self.documents.get(query["_id"], {"_id": query["_id"]}))
        document.update(update.get("$setOnInsert", {}))
        document.update(update.get("$set", {}))
        self.documents[query["_id"]] = document


class ApplyAdmin:
    def __init__(self, database):
        self.database = database
        self.commands = []

    def command(self, command):
        self.commands.append(command)
        temporary = command["renameCollection"].split(".", 1)[1]
        target = command["to"].split(".", 1)[1]
        self.database.collections[target] = self.database.collections.pop(temporary)


class ApplyDatabase:
    name = "arxiv_papers"

    def __init__(self):
        self.collections = {}
        self.collections["arxiv_kaggle"] = ApplyCollection(self, source=True)
        self.stats = ApplyStats()
        self.client = SimpleNamespace(admin=ApplyAdmin(self))

    def list_collection_names(self):
        return list(self.collections)

    def __getitem__(self, name):
        if name == "ingestion_stats":
            return self.stats
        return self.collections[name]


def test_apply_indexes_temporary_then_atomically_replaces_source():
    database = ApplyDatabase()
    database.collections["arxiv_kaggle_import"] = database.collections.pop(
        "arxiv_kaggle"
    )
    database.collections["arxiv_kaggle"] = ApplyCollection(database)

    report = KaggleCorpusCleaner(database).clean(
        source_collection="arxiv_kaggle_import",
        target_collection="arxiv_kaggle",
        policy=make_policy(),
        apply=True,
        run_id="test-run",
    )

    assert report["status"] == "complete"
    assert report["source_collection"] == "arxiv_kaggle_import"
    assert report["target_collection"] == "arxiv_kaggle"
    assert report["validation"]["documents"] == 17
    assert len(database["arxiv_kaggle"].indexes) == 3
    command = database.client.admin.commands[0]
    assert command["dropTarget"] is True
    assert command["renameCollection"].endswith(".arxiv_kaggle__filtered_test-run")
    assert command["to"] == "arxiv_papers.arxiv_kaggle"
    run = database.stats.documents["kaggle-cleanup:test-run"]
    assert run["run_id"] == "test-run"
    assert run["status"] == "complete"
