"""Analyze and index a bounded, resumable batch of downloaded papers."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import os
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient

from src.analysis.identity import normalize_arxiv_id
from src.pipeline.process_paper import main as process_paper
from src.retrieval.factory import load_project_config
from src.utils.ai_services import resolve_ollama_model
from src.utils.download_pdfs import build_paper_query, resolve_mongo_uri

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze and index a configured batch of downloaded papers"
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--limit-per-category",
        type=int,
        help="Override research_processing.papers_per_category",
    )
    parser.add_argument("--max-papers", type=int)
    parser.add_argument("--categories", nargs="+")
    parser.add_argument("--force-analysis", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def select_downloaded_papers(
    collection: Any,
    config: dict[str, Any],
    *,
    analyses_collection: Any | None = None,
    skip_matching_analyses: bool = True,
    categories: list[str] | None = None,
    limit_per_category: int | None = None,
    max_papers: int | None = None,
) -> list[dict[str, Any]]:
    processing = config.get("research_processing", {})
    target_categories = (
        categories
        or list(processing.get("process_categories") or [])
        or list(config.get("pdf_storage", {}).get("process_categories") or [])
    )
    configured_limit = int(processing.get("papers_per_category", 1))
    category_limit = (
        configured_limit if limit_per_category is None else limit_per_category
    )
    completed_analysis_keys = (
        _matching_analysis_keys(analyses_collection, config)
        if skip_matching_analyses
        else set()
    )
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category in target_categories:
        query = build_paper_query(config, category)
        query["local_pdf_path"] = {"$exists": True, "$ne": ""}
        cursor = collection.find(query).sort("published", -1)
        category_count = 0
        for paper in cursor:
            key = str(paper.get("id"))
            if not key or key in seen:
                continue
            seen.add(key)
            analysis_key = _paper_analysis_key(paper)
            if analysis_key is not None and analysis_key in completed_analysis_keys:
                continue
            paper["_selected_category"] = category
            selected.append(paper)
            category_count += 1
            if max_papers and len(selected) >= max_papers:
                return selected
            if category_limit > 0 and category_count >= category_limit:
                break
    return selected


def _matching_analysis_keys(
    analyses_collection: Any | None,
    config: dict[str, Any],
) -> set[tuple[str, str]]:
    if analyses_collection is None:
        return set()
    analysis = config.get("analysis", {})
    query = {
        "schema_version": str(analysis.get("schema_version", "1.0")),
        "prompt_version": analysis.get("prompt_version", "agent-paper-v5"),
        "model": resolve_ollama_model(config),
    }
    projection = {
        "paper_id": 1,
        "document_hash": 1,
    }
    keys: set[tuple[str, str]] = set()
    for document in analyses_collection.find(query, projection):
        paper_id = document.get("paper_id")
        document_hash = document.get("document_hash")
        if not paper_id or not document_hash:
            continue
        try:
            paper_id = normalize_arxiv_id(str(paper_id)).base_id
        except ValueError:
            paper_id = str(paper_id)
        keys.add((paper_id, str(document_hash)))
    return keys


def _paper_analysis_key(paper: dict[str, Any]) -> tuple[str, str] | None:
    document_hash = paper.get("pdf_document_hash")
    if not document_hash:
        return None
    for field_name in ("arxiv_id", "base_arxiv_id", "id"):
        paper_id = paper.get(field_name)
        if not paper_id:
            continue
        try:
            return normalize_arxiv_id(str(paper_id)).base_id, str(document_hash)
        except ValueError:
            continue
    return None


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_project_config(Path(args.config))
    mongo_uri = resolve_mongo_uri(config)
    db_name = os.getenv(
        "MONGO_DB",
        config.get("mongo", {}).get("db_name", "arxiv_papers"),
    )
    client = MongoClient(mongo_uri)
    try:
        database = client[db_name]
        papers = select_downloaded_papers(
            database["papers"],
            config,
            analyses_collection=database[
                config.get("analysis", {}).get(
                    "collection_name",
                    "paper_analyses",
                )
            ],
            skip_matching_analyses=not args.force_analysis,
            categories=args.categories,
            limit_per_category=args.limit_per_category,
            max_papers=args.max_papers,
        )
    finally:
        client.close()

    selected_by_category = Counter(paper["_selected_category"] for paper in papers)
    manifest = [
        {
            "paper_id": paper.get("id"),
            "title": paper.get("title"),
            "selected_category": paper["_selected_category"],
            "local_pdf_path": paper.get("local_pdf_path"),
        }
        for paper in papers
    ]
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry-run",
                    "selected": len(papers),
                    "skips_matching_analysis": not args.force_analysis,
                    "selected_by_category": dict(selected_by_category),
                    "papers": manifest,
                },
                indent=2,
            )
        )
        return 0

    completed: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for position, paper in enumerate(papers, start=1):
        paper_id = str(paper["id"])
        arguments = [
            "--paper-id",
            paper_id,
            "--config",
            args.config,
        ]
        if args.force_analysis:
            arguments.append("--force-analysis")
        if args.no_cache:
            arguments.append("--no-cache")
        if args.skip_index:
            arguments.append("--skip-index")
        logger.info(
            "[%d/%d] Processing %s",
            position,
            len(papers),
            paper_id,
        )
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                process_paper(arguments)
            result = json.loads(output.getvalue())
            completed.append(result)
            logger.info(
                "[%d/%d] Complete: %s",
                position,
                len(papers),
                result["paper_version_id"],
            )
        except Exception as error:
            failures.append({"paper_id": paper_id, "error": str(error)})
            logger.exception(
                "[%d/%d] Failed: %s",
                position,
                len(papers),
                paper_id,
            )

    print(
        json.dumps(
            {
                "status": "complete" if not failures else "complete-with-errors",
                "selected": len(papers),
                "selected_by_category": dict(selected_by_category),
                "completed": len(completed),
                "failed": len(failures),
                "results": completed,
                "failures": failures,
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
