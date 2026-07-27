"""Download a bounded, resumable PDF corpus from MongoDB metadata."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pymongo import MongoClient

from src.analysis.identity import normalize_arxiv_id
from src.ingestion.pdf_download import (
    PdfDownloadError,
    download_paper_pdf,
    resolve_pdf_directory,
)
from src.storage.mongo import MongoStorage

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download the configured PDF test corpus from stored metadata"
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--limit-per-category",
        type=int,
        help="Override pdf_storage.papers_per_category (0 means unlimited)",
    )
    parser.add_argument(
        "--request-interval",
        type=float,
        help="Seconds between new PDF downloads",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_mongo_uri(config: dict[str, Any]) -> str:
    mongo = config.get("mongo", {})
    return (
        os.getenv("MONGO_CONNECTION_STRING")
        or os.getenv("MONGO_URI")
        or (
            mongo.get("connection_string")
            if os.path.exists("/.dockerenv")
            else mongo.get("connection_string_local")
        )
        or "mongodb://localhost:27017/"
    )


def build_paper_query(config: dict[str, Any], category: str) -> dict[str, Any]:
    storage = config.get("pdf_storage", {})
    date_filter = storage.get("download_date_filter", {})
    query: dict[str, Any] = {
        "pdf_url": {"$exists": True, "$ne": ""},
        "categories": category,
    }
    if date_filter.get("enabled"):
        published: dict[str, str] = {}
        if date_filter.get("start_date"):
            published["$gte"] = f"{date_filter['start_date']}T00:00:00"
        if date_filter.get("end_date"):
            published["$lte"] = f"{date_filter['end_date']}T23:59:59Z"
        if published:
            query["published"] = published
    return query


def select_papers(
    collection: Any,
    config: dict[str, Any],
    *,
    limit_per_category: int | None = None,
) -> list[dict[str, Any]]:
    """Select a deterministic, de-duplicated set for each configured category."""

    storage = config.get("pdf_storage", {})
    categories = list(storage.get("process_categories") or [])
    if not categories:
        categories = list(config.get("arxiv", {}).get("categories") or [])
    configured_limit = int(storage.get("papers_per_category", 0))
    limit = configured_limit if limit_per_category is None else limit_per_category
    sort_order = (
        -1 if storage.get("download_date_filter", {}).get("sort_by_date", False) else 1
    )

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category in categories:
        cursor = collection.find(build_paper_query(config, category)).sort(
            "published", sort_order
        )
        category_count = 0
        for paper in cursor:
            key = str(paper.get("id") or paper.get("pdf_url") or paper.get("_id"))
            if key in seen:
                continue
            seen.add(key)
            paper["_selected_category"] = category
            selected.append(paper)
            category_count += 1
            if limit > 0 and category_count >= limit:
                break
    return selected


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config(args.config)
    storage_config = config.get("pdf_storage", {})
    request_interval = (
        float(args.request_interval)
        if args.request_interval is not None
        else float(storage_config.get("request_interval_seconds", 1.0))
    )
    pdf_directory, portable_directory = resolve_pdf_directory(config)
    mongo_uri = resolve_mongo_uri(config)
    db_name = os.getenv(
        "MONGO_DB",
        config.get("mongo", {}).get("db_name", "arxiv_papers"),
    )

    client = MongoClient(mongo_uri)
    db = client[db_name]
    papers = select_papers(
        db["papers"],
        config,
        limit_per_category=args.limit_per_category,
    )
    selected_by_category = Counter(paper["_selected_category"] for paper in papers)
    logger.info(
        "Selected %d unique papers for %s",
        len(papers),
        ", ".join(
            f"{category}={count}" for category, count in selected_by_category.items()
        ),
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry-run",
                    "selected": len(papers),
                    "selected_by_category": dict(selected_by_category),
                    "pdf_directory": str(pdf_directory),
                },
                indent=2,
            )
        )
        client.close()
        return 0

    counts: Counter[str] = Counter()
    failures: list[dict[str, str]] = []
    mongo_storage = MongoStorage(
        connection_string=mongo_uri,
        db_name=db_name,
    )
    try:
        for position, paper in enumerate(papers, start=1):
            paper.pop("_selected_category", None)
            try:
                identity = normalize_arxiv_id(
                    str(paper.get("id") or paper.get("pdf_url"))
                )
                result = download_paper_pdf(
                    paper,
                    identity,
                    directory=pdf_directory,
                    portable_directory=portable_directory,
                )
                mongo_storage.record_pdf(
                    paper_id=str(paper["id"]),
                    arxiv_id=identity.version_id,
                    local_pdf_path=result.storage_path,
                    document_hash=result.sha256,
                    size_bytes=result.size_bytes,
                )
                counts[result.status] += 1
                logger.info(
                    "[%d/%d] %s: %s",
                    position,
                    len(papers),
                    identity.version_id,
                    result.status,
                )
                if result.status == "downloaded" and request_interval > 0:
                    time.sleep(request_interval)
            except (PdfDownloadError, OSError, ValueError, KeyError) as error:
                counts["failed"] += 1
                paper_id = str(paper.get("id") or paper.get("pdf_url") or "unknown")
                failures.append({"paper_id": paper_id, "error": str(error)})
                db["invalid_pdfs"].update_one(
                    {"paper_id": paper_id},
                    {
                        "$set": {
                            "paper_id": paper_id,
                            "url": paper.get("pdf_url"),
                            "timestamp": datetime.now(timezone.utc),
                            "error": str(error),
                        }
                    },
                    upsert=True,
                )
                logger.error(
                    "[%d/%d] %s: %s",
                    position,
                    len(papers),
                    paper_id,
                    error,
                )
    finally:
        mongo_storage.close()
        client.close()

    summary = {
        "status": "complete" if not failures else "complete-with-errors",
        "selected": len(papers),
        "selected_by_category": dict(selected_by_category),
        "results": dict(counts),
        "failure_count": len(failures),
        "failures": failures[:20],
        "pdf_directory": str(pdf_directory),
    }
    print(json.dumps(summary, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
