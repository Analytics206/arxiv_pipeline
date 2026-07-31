"""MongoDB source and hydration for paper-level discovery."""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_right
from collections.abc import Iterator
from typing import Any

from pymongo import ASCENDING, MongoClient

from src.analysis.identity import normalize_arxiv_id
from src.retrieval.curated_models import PaperSearchMetadata
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
                ).sort("id", ASCENDING)
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

    def hydrate_paper_metadata(
        self,
        paper_ids: list[str],
    ) -> dict[str, PaperSearchMetadata]:
        """Merge canonical API-paper fields with richer Kaggle metadata."""

        normalized_ids = list(
            dict.fromkeys(
                normalize_arxiv_id(paper_id).base_id for paper_id in paper_ids
            )
        )
        if not normalized_ids:
            return {}
        paper_documents = {
            str(document[self.eligibility_id_field]): document
            for document in self.eligibility_collection.find(
                {self.eligibility_id_field: {"$in": normalized_ids}},
                {
                    "_id": 0,
                    self.eligibility_id_field: 1,
                    "title": 1,
                    "summary": 1,
                    "authors": 1,
                    "categories": 1,
                    "published": 1,
                    "updated": 1,
                    "arxiv_version": 1,
                    "arxiv_url": 1,
                    "pdf_url": 1,
                },
            )
        }
        kaggle_documents = {
            str(document["id"]): document
            for document in self.collection.find(
                {"id": {"$in": normalized_ids}},
                {
                    "_id": 0,
                    "id": 1,
                    "title": 1,
                    "abstract": 1,
                    "authors": 1,
                    "category_codes": 1,
                    "categories": 1,
                    "primary_category": 1,
                    "update_date": 1,
                    "update_year": 1,
                    "latest_version": 1,
                    "doi": 1,
                    "journal-ref": 1,
                    "license": 1,
                    "comments": 1,
                    "corpus_run_id": 1,
                },
            )
        }
        hydrated: dict[str, PaperSearchMetadata] = {}
        for paper_id in normalized_ids:
            paper = paper_documents.get(paper_id, {})
            kaggle = kaggle_documents.get(paper_id, {})
            if not paper and not kaggle:
                continue
            categories = _metadata_categories(paper, kaggle)
            latest_version = kaggle.get("latest_version") or paper.get("arxiv_version")
            sources = []
            if paper:
                sources.append("papers")
            if kaggle:
                sources.append("arxiv_kaggle")
            hydrated[paper_id] = PaperSearchMetadata(
                paper_id=paper_id,
                title=str(kaggle.get("title") or paper.get("title") or paper_id),
                abstract=_clean_text(kaggle.get("abstract") or paper.get("summary")),
                authors=_metadata_authors(
                    paper.get("authors") or kaggle.get("authors")
                ),
                categories=categories,
                primary_category=(
                    str(kaggle["primary_category"])
                    if kaggle.get("primary_category")
                    else (categories[0] if categories else None)
                ),
                published=_string_or_none(paper.get("published")),
                updated=_string_or_none(paper.get("updated")),
                update_date=_string_or_none(kaggle.get("update_date")),
                update_year=_metadata_year(paper, kaggle),
                latest_version=(
                    str(latest_version) if latest_version is not None else None
                ),
                doi=_string_or_none(kaggle.get("doi")),
                journal_ref=_string_or_none(kaggle.get("journal-ref")),
                license=_string_or_none(kaggle.get("license")),
                comments=_string_or_none(kaggle.get("comments")),
                arxiv_url=str(
                    paper.get("arxiv_url") or f"https://arxiv.org/abs/{paper_id}"
                ),
                pdf_url=str(
                    paper.get("pdf_url") or f"https://arxiv.org/pdf/{paper_id}"
                ),
                corpus_run_id=_string_or_none(kaggle.get("corpus_run_id")),
                metadata_sources=sources,
            )
        return hydrated

    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def __enter__(self) -> "KaggleDiscoveryRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def _clean_text(value: Any) -> str | None:
    text = " ".join(str(value or "").split())
    return text or None


def _string_or_none(value: Any) -> str | None:
    return str(value) if value is not None and str(value).strip() else None


def _metadata_authors(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = _clean_text(value)
    if not text:
        return []
    return [item.strip() for item in text.split(" and ") if item.strip()]


def _metadata_categories(
    paper: dict[str, Any],
    kaggle: dict[str, Any],
) -> list[str]:
    raw = kaggle.get("category_codes") or paper.get("categories")
    if isinstance(raw, list):
        return list(
            dict.fromkeys(str(item).strip() for item in raw if str(item).strip())
        )
    text = _clean_text(raw or kaggle.get("categories"))
    return list(dict.fromkeys(text.split())) if text else []


def _metadata_year(
    paper: dict[str, Any],
    kaggle: dict[str, Any],
) -> int | None:
    if kaggle.get("update_year") is not None:
        try:
            return int(kaggle["update_year"])
        except (TypeError, ValueError):
            pass
    for value in (
        kaggle.get("update_date"),
        paper.get("updated"),
        paper.get("published"),
    ):
        text = str(value or "")
        if len(text) >= 4 and text[:4].isdigit():
            return int(text[:4])
    return None
