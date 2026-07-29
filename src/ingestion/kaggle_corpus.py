"""Safe, configurable retention for the imported Kaggle arXiv corpus."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, cast

from pymongo import ASCENDING, DESCENDING

CategoryMatchMode = Literal["any", "all"]
_COLLECTION_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


class KaggleCorpusError(RuntimeError):
    """Raised when the imported corpus cannot be filtered safely."""


@dataclass(frozen=True, slots=True)
class KaggleRetentionPolicy:
    """Category/date policy and destructive-operation guardrails."""

    retained_categories: tuple[str, ...]
    category_match: CategoryMatchMode = "any"
    start_date: str | None = None
    end_date: str | None = None
    minimum_fraction: float = 0.01
    maximum_fraction: float = 0.30

    def __post_init__(self) -> None:
        normalized = tuple(
            dict.fromkeys(
                category.strip()
                for category in self.retained_categories
                if category and category.strip()
            )
        )
        if not normalized:
            raise ValueError("At least one retained Kaggle category is required")
        if self.category_match not in {"any", "all"}:
            raise ValueError("category_match must be 'any' or 'all'")
        if not 0 <= self.minimum_fraction <= 1:
            raise ValueError("minimum_fraction must be between 0 and 1")
        if not 0 <= self.maximum_fraction <= 1:
            raise ValueError("maximum_fraction must be between 0 and 1")
        if self.minimum_fraction > self.maximum_fraction:
            raise ValueError("minimum_fraction cannot be greater than maximum_fraction")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be later than end_date")
        object.__setattr__(self, "retained_categories", normalized)

    @classmethod
    def from_config(
        cls,
        settings: dict[str, Any],
        *,
        categories: list[str] | None = None,
    ) -> "KaggleRetentionPolicy":
        date_filter = settings.get("date_filter", {})
        date_enabled = bool(date_filter.get("enabled", False))
        guard = settings.get("retention_guard", {})
        category_match = str(settings.get("category_match", "any"))
        if category_match not in {"any", "all"}:
            raise ValueError("category_match must be 'any' or 'all'")
        return cls(
            retained_categories=tuple(
                categories
                if categories is not None
                else settings.get("retained_categories", [])
            ),
            category_match=cast(CategoryMatchMode, category_match),
            start_date=(
                str(date_filter["start_date"])
                if date_enabled and date_filter.get("start_date")
                else None
            ),
            end_date=(
                str(date_filter["end_date"])
                if date_enabled and date_filter.get("end_date")
                else None
            ),
            minimum_fraction=float(guard.get("minimum_fraction", 0.01)),
            maximum_fraction=float(guard.get("maximum_fraction", 0.30)),
        )


def normalize_category_tokens(value: Any) -> list[str]:
    """Return exact, ordered category tokens from Kaggle or normalized data."""

    if isinstance(value, str):
        values = value.split()
    elif isinstance(value, (list, tuple)):
        values = [item for item in value if isinstance(item, str)]
    else:
        values = []
    return list(dict.fromkeys(item.strip() for item in values if item.strip()))


def document_matches_policy(
    document: dict[str, Any],
    policy: KaggleRetentionPolicy,
) -> bool:
    """Pure equivalent of the MongoDB retention predicate for tests/tools."""

    categories = set(
        normalize_category_tokens(
            document.get("category_codes", document.get("categories"))
        )
    )
    retained = set(policy.retained_categories)
    category_match = (
        bool(categories & retained)
        if policy.category_match == "any"
        else retained.issubset(categories)
    )
    if not category_match:
        return False
    update_date = str(document.get("update_date") or "")
    if policy.start_date and update_date < policy.start_date:
        return False
    if policy.end_date and update_date > policy.end_date:
        return False
    return True


def category_tokens_expression(field: str = "$categories") -> dict[str, Any]:
    """MongoDB expression that handles Kaggle strings and normalized arrays."""

    string_value = {
        "$convert": {
            "input": {"$ifNull": [field, ""]},
            "to": "string",
            "onError": "",
            "onNull": "",
        }
    }
    return {
        "$cond": [
            {"$isArray": field},
            field,
            {
                "$filter": {
                    "input": {
                        "$split": [
                            {"$trim": {"input": string_value}},
                            " ",
                        ]
                    },
                    "as": "category",
                    "cond": {"$ne": ["$$category", ""]},
                }
            },
        ]
    }


def build_retention_query(policy: KaggleRetentionPolicy) -> dict[str, Any]:
    """Build an exact-token MongoDB predicate for the selected policy."""

    categories = category_tokens_expression()
    if policy.category_match == "all":
        category_expression: dict[str, Any] = {
            "$setIsSubset": [list(policy.retained_categories), categories]
        }
    else:
        category_expression = {
            "$gt": [
                {
                    "$size": {
                        "$setIntersection": [
                            categories,
                            list(policy.retained_categories),
                        ]
                    }
                },
                0,
            ]
        }
    query: dict[str, Any] = {"$expr": category_expression}
    if policy.start_date or policy.end_date:
        date_query: dict[str, str] = {}
        if policy.start_date:
            date_query["$gte"] = policy.start_date
        if policy.end_date:
            date_query["$lte"] = policy.end_date
        query["update_date"] = date_query
    return query


def build_filter_pipeline(
    policy: KaggleRetentionPolicy,
    *,
    output_collection: str,
    corpus_run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Build the server-side filter/normalization pipeline."""

    _validate_collection_name(output_collection)
    categories = category_tokens_expression()
    versions = {
        "$cond": [
            {"$isArray": "$versions"},
            "$versions",
            [],
        ]
    }
    normalized_fields: dict[str, Any] = {
        "category_codes": categories,
        "primary_category": {"$arrayElemAt": [categories, 0]},
        "version_count": {"$size": versions},
        "latest_version": {
            "$let": {
                "vars": {
                    "latest": {"$arrayElemAt": [versions, -1]},
                },
                "in": "$$latest.version",
            }
        },
        "update_year": {
            "$convert": {
                "input": {
                    "$substrBytes": [
                        {"$ifNull": ["$update_date", ""]},
                        0,
                        4,
                    ]
                },
                "to": "int",
                "onError": None,
                "onNull": None,
            }
        },
        "retention_policy_hash": retention_policy_hash(policy),
    }
    if corpus_run_id:
        normalized_fields["corpus_run_id"] = corpus_run_id
    return [
        {"$match": build_retention_query(policy)},
        {"$set": normalized_fields},
        {"$out": output_collection},
    ]


class KaggleCorpusCleaner:
    """Rebuild and atomically replace an imported Kaggle collection."""

    def __init__(
        self,
        database: Any,
        *,
        stats_collection: str = "ingestion_stats",
        max_time_ms: int = 600_000,
    ):
        self.database = database
        self.stats_collection = stats_collection
        self.max_time_ms = max_time_ms

    def plan(
        self,
        *,
        source_collection: str,
        policy: KaggleRetentionPolicy,
    ) -> dict[str, Any]:
        _validate_collection_name(source_collection)
        if source_collection not in self.database.list_collection_names():
            raise KaggleCorpusError(
                f"Source collection {source_collection!r} does not exist"
            )
        source = self.database[source_collection]
        source_count = int(source.count_documents({}, maxTimeMS=self.max_time_ms))
        if source_count <= 0:
            raise KaggleCorpusError(f"Source collection {source_collection!r} is empty")
        retained_count = int(
            source.count_documents(
                build_retention_query(policy),
                maxTimeMS=self.max_time_ms,
            )
        )
        retention_fraction = retained_count / source_count
        guard_errors = _guard_errors(
            retained_count=retained_count,
            retention_fraction=retention_fraction,
            policy=policy,
        )
        return {
            "event": "kaggle_category_cleanup",
            "status": "ready" if not guard_errors else "guard-rejected",
            "timestamp": datetime.now(timezone.utc),
            "dry_run": True,
            "source_collection": source_collection,
            "retained_categories": list(policy.retained_categories),
            "category_match": policy.category_match,
            "start_date": policy.start_date,
            "end_date": policy.end_date,
            "documents_before": source_count,
            "documents_retained": retained_count,
            "documents_removed": source_count - retained_count,
            "retention_fraction": retention_fraction,
            "retention_guard": {
                "minimum_fraction": policy.minimum_fraction,
                "maximum_fraction": policy.maximum_fraction,
                "errors": guard_errors,
            },
        }

    def clean(
        self,
        *,
        source_collection: str,
        target_collection: str | None = None,
        policy: KaggleRetentionPolicy,
        apply: bool = False,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Return a dry-run report or atomically install a validated rebuild."""

        selected_target = target_collection or source_collection
        _validate_collection_name(selected_target)
        report = self.plan(
            source_collection=source_collection,
            policy=policy,
        )
        report["target_collection"] = selected_target
        if not apply:
            return report
        guard_errors = report["retention_guard"]["errors"]
        if guard_errors:
            raise KaggleCorpusError(
                "Retention guard rejected cleanup: " + "; ".join(guard_errors)
            )

        selected_run_id = run_id or _run_id()
        temp_collection = f"{selected_target}__filtered_{selected_run_id}"
        run_record_id = f"kaggle-cleanup:{selected_run_id}"
        _validate_collection_name(temp_collection)
        if temp_collection in self.database.list_collection_names():
            raise KaggleCorpusError(
                f"Temporary collection {temp_collection!r} already exists"
            )

        stats = self.database[self.stats_collection]
        stats.update_one(
            {"_id": run_record_id},
            {
                "$setOnInsert": {
                    **report,
                    "status": "running",
                    "dry_run": False,
                    "run_id": selected_run_id,
                    "target_collection": selected_target,
                    "temporary_collection": temp_collection,
                    "created_at": datetime.now(timezone.utc),
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc),
                },
            },
            upsert=True,
        )
        try:
            source = self.database[source_collection]
            list(
                source.aggregate(
                    build_filter_pipeline(
                        policy,
                        output_collection=temp_collection,
                        corpus_run_id=selected_run_id,
                    ),
                    allowDiskUse=True,
                    maxTimeMS=self.max_time_ms,
                )
            )
            temporary = self.database[temp_collection]
            validation = self._validate_temporary(
                temporary,
                policy=policy,
                expected_count=report["documents_retained"],
            )
            self._create_indexes(temporary)
            self._replace_collection(
                target_collection=selected_target,
                temp_collection=temp_collection,
            )
        except Exception as error:
            stats.update_one(
                {"_id": run_record_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(error),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            raise

        applied = {
            **report,
            "status": "complete",
            "dry_run": False,
            "run_id": selected_run_id,
            "run_record_id": run_record_id,
            "temporary_collection": temp_collection,
            "validation": validation,
            "indexes": [
                "id_unique",
                "category_update_date",
                "update_date_desc",
            ],
            "target_collection": selected_target,
            "replaced_collection": selected_target,
        }
        stats.update_one(
            {"_id": run_record_id},
            {
                "$set": {
                    **applied,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return applied

    def _validate_temporary(
        self,
        collection: Any,
        *,
        policy: KaggleRetentionPolicy,
        expected_count: int,
    ) -> dict[str, Any]:
        actual_count = int(collection.count_documents({}, maxTimeMS=self.max_time_ms))
        if actual_count != expected_count:
            raise KaggleCorpusError(
                "Filtered collection count changed during rebuild: "
                f"expected {expected_count}, found {actual_count}"
            )
        policy_violations = int(
            collection.count_documents(
                {"$nor": [build_retention_query(policy)]},
                maxTimeMS=self.max_time_ms,
            )
        )
        if policy_violations:
            raise KaggleCorpusError(
                f"Filtered collection has {policy_violations} policy violations"
            )
        missing_core = int(
            collection.count_documents(
                {
                    "$or": [
                        {"id": {"$exists": False}},
                        {"id": None},
                        {"id": ""},
                        {"title": {"$exists": False}},
                        {"title": None},
                        {"title": ""},
                        {"abstract": {"$exists": False}},
                        {"abstract": None},
                        {"abstract": ""},
                    ]
                },
                maxTimeMS=self.max_time_ms,
            )
        )
        if missing_core:
            raise KaggleCorpusError(
                f"Filtered collection has {missing_core} documents missing "
                "id, title, or abstract"
            )
        duplicate = list(
            collection.aggregate(
                [
                    {"$group": {"_id": "$id", "count": {"$sum": 1}}},
                    {"$match": {"count": {"$gt": 1}}},
                    {"$limit": 1},
                ],
                allowDiskUse=True,
                maxTimeMS=self.max_time_ms,
            )
        )
        if duplicate:
            raise KaggleCorpusError(
                f"Filtered collection has duplicate arXiv id {duplicate[0]['_id']!r}"
            )
        return {
            "documents": actual_count,
            "policy_violations": 0,
            "missing_core_fields": 0,
            "duplicate_ids": 0,
        }

    @staticmethod
    def _create_indexes(collection: Any) -> None:
        collection.create_index(
            [("id", ASCENDING)],
            name="id_unique",
            unique=True,
        )
        collection.create_index(
            [
                ("category_codes", ASCENDING),
                ("update_date", DESCENDING),
            ],
            name="category_update_date",
        )
        collection.create_index(
            [("update_date", DESCENDING)],
            name="update_date_desc",
        )

    def _replace_collection(
        self,
        *,
        target_collection: str,
        temp_collection: str,
    ) -> None:
        database_name = self.database.name
        self.database.client.admin.command(
            {
                "renameCollection": f"{database_name}.{temp_collection}",
                "to": f"{database_name}.{target_collection}",
                "dropTarget": True,
            }
        )


def _guard_errors(
    *,
    retained_count: int,
    retention_fraction: float,
    policy: KaggleRetentionPolicy,
) -> list[str]:
    errors: list[str] = []
    if retained_count <= 0:
        errors.append("the selected policy retains no documents")
    if retention_fraction < policy.minimum_fraction:
        errors.append(
            f"retention fraction {retention_fraction:.6f} is below "
            f"{policy.minimum_fraction:.6f}"
        )
    if retention_fraction > policy.maximum_fraction:
        errors.append(
            f"retention fraction {retention_fraction:.6f} is above "
            f"{policy.maximum_fraction:.6f}"
        )
    return errors


def _validate_collection_name(value: str) -> None:
    if not value or not _COLLECTION_NAME.fullmatch(value):
        raise ValueError(f"Unsafe MongoDB collection name: {value!r}")


def _run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{uuid.uuid4().hex[:8]}"


def retention_policy_hash(policy: KaggleRetentionPolicy) -> str:
    """Stable identity for the policy materialized into a filtered corpus."""

    payload = {
        "retained_categories": list(policy.retained_categories),
        "category_match": policy.category_match,
        "start_date": policy.start_date,
        "end_date": policy.end_date,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
