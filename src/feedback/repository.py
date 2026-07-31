"""MongoDB storage and paper-source resolution for harness feedback."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

from src.analysis.identity import normalize_arxiv_id, paper_lookup_aliases
from src.feedback.models import (
    KNOWN_REASONS,
    PROJECT_ONLY_REASONS,
    REASON_GROUPS,
)

FEEDBACK_SCHEMA_VERSION = "harness-feedback-v1"


class FeedbackTargetError(ValueError):
    """A feedback target is absent from its immutable delivered response."""


class MongoFeedbackRepository:
    """Append feedback once and retain client fields without normalization."""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        db_name: str = "arxiv_papers",
        *,
        collection_name: str = "harness_feedback",
        papers_collection: str = "papers",
        kaggle_collection: str = "arxiv_kaggle",
        analyses_collection: str = "paper_analyses",
        search_outputs_collection: str = "research_search_outputs",
        database: Any | None = None,
    ):
        self._client: MongoClient[dict[str, Any]] | None = None
        if database is None:
            self._client = MongoClient(connection_string)
            database = self._client[db_name]
        self.db = database
        self.feedback = database[collection_name]
        self.papers = database[papers_collection]
        self.kaggle = database[kaggle_collection]
        self.analyses = database[analyses_collection]
        self.search_outputs = database[search_outputs_collection]
        self.search_outputs_collection_name = search_outputs_collection
        self.collection_name = collection_name
        self.source_collections = {
            "papers": papers_collection,
            "arxiv_kaggle": kaggle_collection,
            "paper_analyses": analyses_collection,
        }
        self._setup_indexes()

    def _setup_indexes(self) -> None:
        self.feedback.create_index(
            [("feedback_id", ASCENDING)],
            unique=True,
            name="feedback_identity",
        )
        self.feedback.create_index(
            [("subject.paper_id", ASCENDING)],
            name="feedback_paper",
        )
        self.feedback.create_index(
            [("request_id", ASCENDING)],
            name="feedback_request",
        )
        self.feedback.create_index(
            [("subject.point_id", ASCENDING)],
            name="feedback_point",
        )
        self.feedback.create_index(
            [("reason", ASCENDING)],
            name="feedback_reason",
        )
        self.feedback.create_index(
            [("project.id", ASCENDING)],
            name="feedback_project",
        )
        self.feedback.create_index(
            [("occurred_at", DESCENDING)],
            name="feedback_occurred",
        )
        self.feedback.create_index(
            [
                ("resolved_ingestion_sources", ASCENDING),
                ("reason", ASCENDING),
                ("project.id", ASCENDING),
            ],
            name="feedback_source_reason_project",
        )

    def validate_archived_target(self, record: dict[str, Any]) -> None:
        """Reject request-correlated subjects absent from the delivered output."""

        feedback_id = str(record["feedback_id"])
        if self.feedback.find_one(
            {"feedback_id": feedback_id},
            {"_id": 1},
        ):
            return

        request_id = record.get("request_id")
        if not request_id:
            return
        output = self.search_outputs.find_one(
            {
                "$or": [
                    {"_id": request_id},
                    {"request_id": request_id},
                ]
            },
            {
                "_id": 0,
                "response.papers.paper_id": 1,
                "response.papers.research_items.point_id": 1,
            },
        )
        if output is None:
            raise FeedbackTargetError(
                f"request_id '{request_id}' has no archived curated output"
            )

        response = output.get("response")
        papers = response.get("papers") if isinstance(response, dict) else None
        if not isinstance(papers, list):
            raise FeedbackTargetError(
                f"request_id '{request_id}' has no usable archived curated output"
            )

        subject = record["subject"]
        paper_id = subject.get("paper_id")
        if not paper_id:
            return
        normalized_paper_id = _normalized_id_or_original(str(paper_id))
        delivered_paper = next(
            (
                paper
                for paper in papers
                if isinstance(paper, dict)
                and _normalized_id_or_original(str(paper.get("paper_id") or ""))
                == normalized_paper_id
            ),
            None,
        )
        if delivered_paper is None:
            raise FeedbackTargetError(
                f"request_id '{request_id}' did not deliver "
                f"subject.paper_id '{paper_id}'"
            )

        point_id = subject.get("point_id")
        if not point_id:
            return
        research_items = delivered_paper.get("research_items")
        delivered_point_ids = {
            str(item.get("point_id"))
            for item in research_items or []
            if isinstance(item, dict) and item.get("point_id")
        }
        if str(point_id) not in delivered_point_ids:
            raise FeedbackTargetError(
                f"request_id '{request_id}' did not deliver "
                f"subject.point_id '{point_id}' for paper '{paper_id}'"
            )

    def append(
        self,
        *,
        envelope: dict[str, Any],
        record: dict[str, Any],
    ) -> tuple[bool, bool]:
        """Return ``(inserted, paper_resolved)`` for one validated record."""

        feedback_id = str(record["feedback_id"])
        subject = record["subject"]
        paper_id = subject.get("paper_id")
        sources = self.resolve_ingestion_sources(paper_id) if paper_id else []
        received_at = datetime.now(timezone.utc)

        document = deepcopy(record)
        document.update(
            {
                "_id": feedback_id,
                "feedback_id": feedback_id,
                "schema_version": FEEDBACK_SCHEMA_VERSION,
                "received_at": received_at,
                "contract_version": envelope["contract_version"],
                "taxonomy_version": envelope["taxonomy_version"],
                "client": deepcopy(envelope["client"]),
                "project": deepcopy(envelope["project"]),
                "envelope": {
                    key: deepcopy(value)
                    for key, value in envelope.items()
                    if key != "records"
                },
                "reason_known": record["reason"] in KNOWN_REASONS,
                "reason_group": REASON_GROUPS.get(record["reason"], "unknown"),
                "signal_scope": (
                    "project_only"
                    if record["reason"] in PROJECT_ONLY_REASONS
                    else "corpus_review"
                ),
                "resolved_ingestion_sources": sources,
            }
        )
        if paper_id:
            document["resolved_paper_id"] = _normalized_id_or_original(paper_id)

        try:
            self.feedback.insert_one(document)
        except DuplicateKeyError:
            return False, bool(sources)
        return True, bool(sources)

    def resolve_ingestion_sources(self, paper_id: str) -> list[str]:
        """Resolve a feedback paper to the canonical source collections."""

        normalized = _normalized_id_or_none(paper_id)
        if normalized is None:
            return []

        sources: list[str] = []
        aliases = paper_lookup_aliases(paper_id)
        if self.papers.find_one(
            {
                "$or": [
                    {"base_arxiv_id": normalized},
                    {"arxiv_id": {"$in": aliases}},
                    {"id": {"$in": aliases}},
                ]
            },
            {"_id": 1},
        ):
            sources.append("papers")
        if self.kaggle.find_one({"id": normalized}, {"_id": 1}):
            sources.append("arxiv_kaggle")
        if self.analyses.find_one({"paper_id": normalized}, {"_id": 1}):
            sources.append("paper_analyses")
        return sources

    def close(self) -> None:
        if self._client is not None:
            self._client.close()


def _normalized_id_or_original(paper_id: str) -> str:
    return _normalized_id_or_none(paper_id) or paper_id


def _normalized_id_or_none(paper_id: str) -> str | None:
    try:
        return normalize_arxiv_id(paper_id).base_id
    except ValueError:
        return None
