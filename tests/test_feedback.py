from copy import deepcopy

from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

from src.api.main import app
from src.api.routes.feedback import get_feedback_repository
from src.feedback.models import validate_record
from src.feedback.repository import (
    FEEDBACK_SCHEMA_VERSION,
    MongoFeedbackRepository,
)


def batch(records):
    return {
        "contract": "research-feedback-batch",
        "contract_version": "1.0",
        "taxonomy_version": "1.0",
        "client": {"name": "harness", "version": "0.9.0"},
        "project": {"id": "prj-test"},
        "records": records,
    }


def record(
    feedback_id="fb:run:triage:2607.21557:off_topic",
    *,
    paper_id="2607.21557",
    reason="off_topic",
):
    return {
        "feedback_id": feedback_id,
        "occurred_at": "2026-07-30T18:42:07Z",
        "source": "agent",
        "workflow": "research-scan",
        "run_id": "run",
        "stage": "triage",
        "subject": {"kind": "paper", "paper_id": paper_id},
        "reason": reason,
    }


class FakeFeedbackRepository:
    def __init__(self):
        self.records = {}

    def append(self, *, envelope, record):
        feedback_id = record["feedback_id"]
        resolved = record["subject"].get("paper_id") == "2607.21557"
        if feedback_id in self.records:
            return False, resolved
        self.records[feedback_id] = {
            "envelope": deepcopy(envelope),
            "record": deepcopy(record),
        }
        return True, resolved


def test_feedback_endpoint_accepts_valid_records_and_rejects_only_invalid_ones(
    monkeypatch,
):
    repository = FakeFeedbackRepository()
    app.dependency_overrides[get_feedback_repository] = lambda: repository
    monkeypatch.delenv("RESEARCH_FEEDBACK_BEARER_TOKEN", raising=False)
    client = TestClient(app)
    unknown = record(
        "fb:run:triage:0000.00000:future_signal",
        paper_id="0000.00000",
        reason="future_signal",
    )
    unknown["future_detail"] = {"preserve": True}
    invalid = record("fb:invalid")
    invalid["subject"] = {"kind": "idea", "idea_ref": "report#idea"}

    try:
        response = client.post(
            "/research/feedback",
            json=batch([record(), unknown, invalid]),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "contract": "research-feedback-ack",
        "received": 3,
        "accepted": 2,
        "duplicates": 0,
        "errors": [
            {
                "index": 2,
                "feedback_id": "fb:invalid",
                "error": "subject.paper_id must be a non-empty string",
            }
        ],
        "unknown_reasons": ["future_signal"],
        "unresolved_papers": ["0000.00000"],
    }
    assert repository.records["fb:run:triage:0000.00000:future_signal"]["record"][
        "future_detail"
    ] == {"preserve": True}


def test_feedback_endpoint_replay_is_a_successful_duplicate(monkeypatch):
    repository = FakeFeedbackRepository()
    app.dependency_overrides[get_feedback_repository] = lambda: repository
    monkeypatch.delenv("RESEARCH_FEEDBACK_BEARER_TOKEN", raising=False)
    client = TestClient(app)
    payload = batch([record()])

    try:
        first = client.post("/research/feedback", json=payload)
        replay = client.post("/research/feedback", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert first.json()["accepted"] == 1
    assert replay.status_code == 200
    assert replay.json()["accepted"] == 0
    assert replay.json()["duplicates"] == 1
    assert len(repository.records) == 1


def test_feedback_endpoint_enforces_optional_bearer_token(monkeypatch):
    repository = FakeFeedbackRepository()
    app.dependency_overrides[get_feedback_repository] = lambda: repository
    monkeypatch.setenv("RESEARCH_FEEDBACK_BEARER_TOKEN", "secret-token")
    client = TestClient(app)

    try:
        missing = client.post("/research/feedback", json=batch([record()]))
        accepted = client.post(
            "/research/feedback",
            json=batch([record()]),
            headers={"Authorization": "Bearer secret-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert accepted.status_code == 200


def test_feedback_endpoint_rejects_malformed_or_oversized_envelopes(monkeypatch):
    repository = FakeFeedbackRepository()
    app.dependency_overrides[get_feedback_repository] = lambda: repository
    monkeypatch.delenv("RESEARCH_FEEDBACK_BEARER_TOKEN", raising=False)
    client = TestClient(app)

    try:
        malformed_json = client.post(
            "/research/feedback",
            content="{",
            headers={"Content-Type": "application/json"},
        )
        malformed_envelope = client.post(
            "/research/feedback",
            json={"contract": "wrong"},
        )
        oversized = client.post(
            "/research/feedback",
            json=batch([record(f"fb:{index}") for index in range(101)]),
        )
    finally:
        app.dependency_overrides.clear()

    assert malformed_json.status_code == 400
    assert malformed_envelope.status_code == 400
    assert oversized.status_code == 413
    assert repository.records == {}


def test_outcome_follow_ups_require_a_human_source_and_pointer():
    outcome = {
        "feedback_id": "01J1YV5T9GQZ3M8R4W2K7E6D0B",
        "occurred_at": "2026-08-14T02:10:00Z",
        "source": "human",
        "stage": "human",
        "subject": {
            "kind": "idea",
            "paper_id": "2607.21557",
            "idea_ref": "reports/scan.md#idea-2",
        },
        "reason": "trial_failed",
        "follow_up_of": "fb:run:appraise:2607.21557:trial",
    }

    assert validate_record(outcome) is outcome
    missing_pointer = {
        key: value for key, value in outcome.items() if key != "follow_up_of"
    }
    try:
        validate_record(missing_pointer)
    except ValueError as error:
        assert str(error) == "reason 'trial_failed' requires follow_up_of"
    else:
        raise AssertionError("Expected a missing follow-up pointer to fail")


class FakeCollection:
    def __init__(self, documents=None):
        self.documents = deepcopy(documents or [])
        self.indexes = []

    def create_index(self, keys, **kwargs):
        self.indexes.append((keys, kwargs))
        return kwargs.get("name")

    def find_one(self, query, projection=None):
        for document in self.documents:
            if _matches(document, query):
                return deepcopy(document)
        return None

    def insert_one(self, document):
        if any(
            item.get("feedback_id") == document["feedback_id"]
            for item in self.documents
        ):
            raise DuplicateKeyError("duplicate feedback_id")
        self.documents.append(deepcopy(document))


class FakeDatabase:
    def __init__(self):
        self.collections = {
            "papers": FakeCollection([{"_id": "p1", "base_arxiv_id": "2607.21557"}]),
            "arxiv_kaggle": FakeCollection([{"_id": "k1", "id": "2607.21557"}]),
            "paper_analyses": FakeCollection([{"_id": "a1", "paper_id": "2607.21557"}]),
        }

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


def test_repository_stores_append_only_feedback_and_source_resolution():
    database = FakeDatabase()
    repository = MongoFeedbackRepository(database=database)
    envelope = batch([])
    feedback = record()
    feedback["unrecognized_extension"] = {"kept": "exactly"}

    inserted, resolved = repository.append(
        envelope=envelope,
        record=feedback,
    )
    duplicate, duplicate_resolved = repository.append(
        envelope=envelope,
        record=feedback,
    )

    assert inserted is True
    assert duplicate is False
    assert resolved is True
    assert duplicate_resolved is True
    saved = repository.feedback.documents[0]
    assert saved["schema_version"] == FEEDBACK_SCHEMA_VERSION
    assert saved["feedback_id"] == feedback["feedback_id"]
    assert saved["project"] == {"id": "prj-test"}
    assert saved["resolved_paper_id"] == "2607.21557"
    assert saved["resolved_ingestion_sources"] == [
        "papers",
        "arxiv_kaggle",
        "paper_analyses",
    ]
    assert saved["reason_group"] == "retrieval_defect"
    assert saved["signal_scope"] == "corpus_review"
    assert saved["unrecognized_extension"] == {"kept": "exactly"}
    index_names = {options["name"] for _, options in repository.feedback.indexes}
    assert {
        "feedback_identity",
        "feedback_paper",
        "feedback_reason",
        "feedback_project",
        "feedback_occurred",
        "feedback_source_reason_project",
    } <= index_names

    project_relative = record(
        "fb:run:triage:2607.21557:not_project_fit",
        reason="not_project_fit",
    )
    inserted, _ = repository.append(
        envelope=envelope,
        record=project_relative,
    )
    assert inserted is True
    assert repository.feedback.documents[-1]["signal_scope"] == "project_only"


def _matches(document, query):
    if "$or" in query:
        return any(_matches(document, item) for item in query["$or"])
    for key, expected in query.items():
        actual = document.get(key)
        if isinstance(expected, dict) and "$in" in expected:
            if actual not in expected["$in"]:
                return False
        elif actual != expected:
            return False
    return True
