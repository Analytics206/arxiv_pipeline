"""MongoDB source and hydration for paper-level discovery."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import Any

from pymongo import ASCENDING, MongoClient

from src.retrieval.discovery_models import DiscoverySearchHit, DiscoverySearchResponse


class KaggleDiscoveryRepository:
    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        db_name: str = "arxiv_papers",
        collection_name: str = "arxiv_kaggle",
        *,
        database: Any | None = None,
    ):
        self._client: MongoClient[dict[str, Any]] | None = None
        if database is None:
            self._client = MongoClient(connection_string)
            database = self._client[db_name]
        self.db = database
        self.collection = database[collection_name]

    def count(self) -> int:
        return int(self.collection.count_documents({}))

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
        count = self.count()
        if first and first.get("corpus_run_id"):
            token_source = str(first["corpus_run_id"])
        else:
            token_source = (
                f"{count}:"
                f"{(first or {}).get('update_date', '')}:"
                f"{(first or {}).get('retention_policy_hash', '')}"
            )
        snapshot_token = hashlib.sha256(token_source.encode("utf-8")).hexdigest()[:12]
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
            "documents": count,
            "snapshot_token": snapshot_token,
            "prepared": bool(
                first
                and first.get("corpus_run_id")
                and isinstance(first.get("category_codes"), list)
            ),
        }

    def iter_batches(
        self,
        *,
        batch_size: int,
        after_id: str | None = None,
        limit: int | None = None,
    ) -> Iterator[list[dict[str, Any]]]:
        emitted = 0
        last_id = after_id
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
        while limit is None or emitted < limit:
            query = {"id": {"$gt": last_id}} if last_id else {}
            selected_size = min(
                batch_size,
                limit - emitted if limit is not None else batch_size,
            )
            batch = list(
                self.collection.find(query, projection)
                .sort("id", ASCENDING)
                .limit(selected_size)
            )
            if not batch:
                return
            yield batch
            emitted += len(batch)
            last_id = str(batch[-1]["id"])

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
