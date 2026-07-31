"""MongoDB persistence for complete canonical research-search traces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from pymongo import ASCENDING, DESCENDING, MongoClient, TEXT

from src.retrieval.curated_models import CuratedResearchSearchResponse

SEARCH_HISTORY_SCHEMA_VERSION = "research-search-history-v1"


class SearchHistoryRecorder(Protocol):
    """Storage boundary used by retrieval without depending on MongoDB details."""

    def start_search(
        self,
        *,
        request_id: str,
        created_at: datetime,
        request: dict[str, Any],
        client: dict[str, Any],
    ) -> None: ...

    def save_source_pulls(
        self,
        *,
        request_id: str,
        created_at: datetime,
        pulls: list[dict[str, Any]],
    ) -> None: ...

    def complete_search(
        self,
        *,
        request_id: str,
        response: CuratedResearchSearchResponse,
        duration_ms: int,
        warnings: list[str],
    ) -> None: ...

    def fail_search(
        self,
        *,
        request_id: str,
        stage: str,
        error: str,
        duration_ms: int,
    ) -> None: ...


class MongoSearchHistoryRepository:
    """Persist request, raw source pulls, and exact output as linked documents."""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        db_name: str = "arxiv_papers",
        *,
        runs_collection: str = "research_search_runs",
        source_pulls_collection: str = "research_search_source_pulls",
        outputs_collection: str = "research_search_outputs",
        database: Any | None = None,
    ):
        self._client: MongoClient[dict[str, Any]] | None = None
        if database is None:
            self._client = MongoClient(connection_string)
            database = self._client[db_name]
        self.db = database
        self.runs = database[runs_collection]
        self.source_pulls = database[source_pulls_collection]
        self.outputs = database[outputs_collection]
        self.collection_names = {
            "runs": runs_collection,
            "source_pulls": source_pulls_collection,
            "outputs": outputs_collection,
        }
        self._setup_indexes()

    def _setup_indexes(self) -> None:
        self.runs.create_index(
            [("created_at", DESCENDING)],
            name="search_runs_created",
        )
        self.runs.create_index(
            [("status", ASCENDING), ("created_at", DESCENDING)],
            name="search_runs_status",
        )
        self.runs.create_index(
            [("request.query", TEXT)],
            name="search_runs_query_text",
        )
        self.runs.create_index(
            [("feedback_targets.paper_ids", ASCENDING)],
            name="search_runs_feedback_papers",
        )
        self.runs.create_index(
            [("feedback_targets.point_ids", ASCENDING)],
            name="search_runs_feedback_points",
        )
        self.source_pulls.create_index(
            [("request_id", ASCENDING), ("source", ASCENDING)],
            unique=True,
            name="search_pull_identity",
        )
        self.source_pulls.create_index(
            [("created_at", DESCENDING)],
            name="search_pulls_created",
        )
        self.outputs.create_index(
            [("request_id", ASCENDING)],
            unique=True,
            name="search_output_request",
        )
        self.outputs.create_index(
            [("created_at", DESCENDING)],
            name="search_outputs_created",
        )

    def start_search(
        self,
        *,
        request_id: str,
        created_at: datetime,
        request: dict[str, Any],
        client: dict[str, Any],
    ) -> None:
        self.runs.insert_one(
            {
                "_id": request_id,
                "request_id": request_id,
                "schema_version": SEARCH_HISTORY_SCHEMA_VERSION,
                "status": "running",
                "created_at": created_at,
                "updated_at": created_at,
                "request": request,
                "client": client,
                "source_pull_count": 0,
                "warnings": [],
            }
        )

    def save_source_pulls(
        self,
        *,
        request_id: str,
        created_at: datetime,
        pulls: list[dict[str, Any]],
    ) -> None:
        saved_at = _utc_now()
        for pull in pulls:
            source = str(pull["source"])
            document = {
                "_id": f"{request_id}:{source}",
                "request_id": request_id,
                "schema_version": SEARCH_HISTORY_SCHEMA_VERSION,
                "created_at": created_at,
                "saved_at": saved_at,
                **pull,
            }
            self.source_pulls.replace_one(
                {"_id": document["_id"]},
                document,
                upsert=True,
            )
        self.runs.update_one(
            {"_id": request_id},
            {
                "$set": {
                    "source_pull_count": len(pulls),
                    "sources_saved_at": saved_at,
                    "updated_at": saved_at,
                }
            },
        )

    def complete_search(
        self,
        *,
        request_id: str,
        response: CuratedResearchSearchResponse,
        duration_ms: int,
        warnings: list[str],
    ) -> None:
        completed_at = _utc_now()
        response_document = response.model_dump(mode="json")
        self.outputs.replace_one(
            {"_id": request_id},
            {
                "_id": request_id,
                "request_id": request_id,
                "schema_version": SEARCH_HISTORY_SCHEMA_VERSION,
                "created_at": response.generated_at,
                "saved_at": completed_at,
                "response": response_document,
            },
            upsert=True,
        )
        feedback_targets = build_feedback_targets(response)
        self.runs.update_one(
            {"_id": request_id},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": completed_at,
                    "updated_at": completed_at,
                    "duration_ms": duration_ms,
                    "result_status": response.result_status,
                    "returned_papers": len(response.papers),
                    "warnings": warnings,
                    "output_saved": True,
                    "feedback_targets": feedback_targets,
                }
            },
        )

    def fail_search(
        self,
        *,
        request_id: str,
        stage: str,
        error: str,
        duration_ms: int,
    ) -> None:
        failed_at = _utc_now()
        self.runs.update_one(
            {"_id": request_id},
            {
                "$set": {
                    "status": "failed",
                    "failed_at": failed_at,
                    "updated_at": failed_at,
                    "duration_ms": duration_ms,
                    "failure": {
                        "stage": stage,
                        "error": error,
                    },
                }
            },
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()


def build_feedback_targets(
    response: CuratedResearchSearchResponse,
) -> dict[str, Any]:
    """Summarize stable response identifiers without defining feedback meaning."""

    papers: list[dict[str, Any]] = []
    point_ids: list[str] = []
    for paper in response.papers:
        paper_points = [item.point_id for item in paper.research_items]
        point_ids.extend(paper_points)
        papers.append(
            {
                "paper_id": paper.paper_id,
                "rank": paper.rank,
                "tier": paper.tier,
                "point_ids": paper_points,
            }
        )
    return {
        "paper_ids": [paper.paper_id for paper in response.papers],
        "point_ids": list(dict.fromkeys(point_ids)),
        "papers": papers,
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
