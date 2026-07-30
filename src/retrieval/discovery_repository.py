"""MongoDB source and hydration for paper-level discovery."""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
from collections.abc import Iterator
from typing import Any

from pymongo import ASCENDING, MongoClient

from src.analysis.identity import normalize_arxiv_id
from src.retrieval.discovery_models import DiscoverySearchHit, DiscoverySearchResponse

_MATCH_POLICY_VERSION = "papers-base-id-intersection-v1"


class KaggleDiscoveryRepository:
    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        db_name: str = "arxiv_papers",
        collection_name: str = "arxiv_kaggle",
        *,
        eligibility_collection_name: str = "papers",
        eligibility_id_field: str = "base_arxiv_id",
        database: Any | None = None,
    ):
        self._client: MongoClient[dict[str, Any]] | None = None
        if database is None:
            self._client = MongoClient(connection_string)
            database = self._client[db_name]
        self.db = database
        self.collection = database[collection_name]
        self.collection_name = collection_name
        self.eligibility_collection = database[eligibility_collection_name]
        self.eligibility_collection_name = eligibility_collection_name
        self.eligibility_id_field = eligibility_id_field
        self._eligible_ids_cache: tuple[str, ...] | None = None
        self._matched_ids_cache: tuple[str, ...] | None = None

    def count(self) -> int:
        return len(self._matched_ids())

    def snapshot_identity(self) -> dict[str, Any]:
        first = self.collection.find_one(
            {},
            {
                "_id": 0,
                "corpus_run_id": 1,
                "retention_policy_hash": 1,
                "category_codes": 1,
                "update_date": 1,
            },
        )
        candidate_count = int(self.collection.count_documents({}))
        eligible_ids = self._eligible_ids()
        matched_ids = self._matched_ids()
        matched_ids_hash = hashlib.sha256(
            "\n".join(matched_ids).encode("utf-8")
        ).hexdigest()
        if first and first.get("corpus_run_id"):
            corpus_token = str(first["corpus_run_id"])
        else:
            corpus_token = (
                f"{candidate_count}:"
                f"{(first or {}).get('update_date', '')}:"
                f"{(first or {}).get('retention_policy_hash', '')}"
            )
        snapshot_payload = {
            "corpus_token": corpus_token,
            "eligibility_collection": self.eligibility_collection_name,
            "eligibility_id_field": self.eligibility_id_field,
            "match_policy": _MATCH_POLICY_VERSION,
            "matched_ids_hash": matched_ids_hash,
        }
        snapshot_token = hashlib.sha256(
            json.dumps(
                snapshot_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:12]
        return {
            "corpus_run_id": (
                str(first.get("corpus_run_id"))
                if first and first.get("corpus_run_id")
                else None
            ),
            "retention_policy_hash": (
                str(first.get("retention_policy_hash"))
                if first and first.get("retention_policy_hash")
                else None
            ),
            "documents": len(matched_ids),
            "candidate_documents": candidate_count,
            "eligibility_documents": len(eligible_ids),
            "eligibility_collection": self.eligibility_collection_name,
            "eligibility_id_field": self.eligibility_id_field,
            "match_policy": _MATCH_POLICY_VERSION,
            "matched_ids_hash": matched_ids_hash,
            "snapshot_token": snapshot_token,
            "prepared": bool(
                first
                and first.get("corpus_run_id")
                and isinstance(first.get("category_codes"), list)
            ),
        }

    def _eligible_ids(self) -> tuple[str, ...]:
        if self._eligible_ids_cache is not None:
            return self._eligible_ids_cache
        values: set[str] = set()
        for document in self.eligibility_collection.find(
            {self.eligibility_id_field: {"$type": "string"}},
            {
                "_id": 0,
                self.eligibility_id_field: 1,
            },
        ):
            value = document.get(self.eligibility_id_field)
            if not value:
                continue
            try:
                values.add(normalize_arxiv_id(str(value)).base_id)
            except ValueError:
                continue
        self._eligible_ids_cache = tuple(sorted(values))
        return self._eligible_ids_cache

    def _matched_ids(self) -> tuple[str, ...]:
        if self._matched_ids_cache is not None:
            return self._matched_ids_cache
        eligible_ids = self._eligible_ids()
        matched: set[str] = set()
        for offset in range(0, len(eligible_ids), 5_000):
            selected_ids = eligible_ids[offset : offset + 5_000]
            for document in self.collection.find(
                {"id": {"$in": list(selected_ids)}},
                {
                    "_id": 0,
                    "id": 1,
                },
            ):
                paper_id = document.get("id")
                if paper_id:
                    matched.add(str(paper_id))
        self._matched_ids_cache = tuple(sorted(matched))
        return self._matched_ids_cache

    def iter_batches(
        self,
        *,
        batch_size: int,
        after_id: str | None = None,
        limit: int | None = None,
    ) -> Iterator[list[dict[str, Any]]]:
        emitted = 0
        matched_ids = self._matched_ids()
        position = bisect_right(matched_ids, after_id) if after_id else 0
        projection = {
            "_id": 0,
            "id": 1,
            "title": 1,
            "abstract": 1,
            "category_codes": 1,
            "categories": 1,
            "primary_category": 1,
            "update_date": 1,
            "update_year": 1,
            "latest_version": 1,
            "versions": 1,
            "corpus_run_id": 1,
        }
        while position < len(matched_ids) and (limit is None or emitted < limit):
            selected_size = min(
                batch_size,
                limit - emitted if limit is not None else batch_size,
            )
            selected_ids = matched_ids[position : position + selected_size]
            batch = list(
                self.collection.find(
                    {"id": {"$in": list(selected_ids)}},
                    projection,
                )
                .sort("id", ASCENDING)
            )
            if len(batch) != len(selected_ids):
                raise RuntimeError(
                    "arxiv_kaggle changed after the discovery source snapshot; "
                    "restart so a new physical collection can be selected"
                )
            yield batch
            emitted += len(batch)
            position += len(selected_ids)

    def hydrate(
        self,
        response: DiscoverySearchResponse,
    ) -> DiscoverySearchResponse:
        if not response.hits:
            return response
        paper_ids = list(dict.fromkeys(hit.paper_id for hit in response.hits))
        documents = {
            str(document["id"]): document
            for document in self.collection.find(
                {"id": {"$in": paper_ids}},
                {
                    "_id": 0,
                    "id": 1,
                    "abstract": 1,
                    "authors": 1,
                    "doi": 1,
                    "journal-ref": 1,
                    "license": 1,
                    "comments": 1,
                },
            )
        }
        hydrated: list[DiscoverySearchHit] = []
        for hit in response.hits:
            document = documents.get(hit.paper_id, {})
            hydrated.append(
                hit.model_copy(
                    update={
                        "abstract": document.get("abstract"),
                        "authors": document.get("authors"),
                        "doi": document.get("doi"),
                        "journal_ref": document.get("journal-ref"),
                        "license": document.get("license"),
                        "comments": document.get("comments"),
                    }
                )
            )
        return response.model_copy(update={"hits": hydrated})

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def __enter__(self) -> "KaggleDiscoveryRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
