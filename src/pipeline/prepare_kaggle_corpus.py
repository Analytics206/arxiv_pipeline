"""Sequence Kaggle retention and optional discovery indexing."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pymongo import MongoClient

from src.ingestion.kaggle_corpus import (
    KaggleCorpusCleaner,
    KaggleRetentionPolicy,
    retained_categories_from_env,
)
from src.pipeline.index_arxiv_discovery import run_discovery_index
from src.retrieval.discovery_repository import KaggleDiscoveryRepository


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate/filter arxiv_kaggle and optionally build the current "
            "paper-discovery index"
        )
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--source-collection",
        help="Full imported collection to read",
    )
    parser.add_argument(
        "--target-collection",
        help="Filtered production collection to atomically replace",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Atomically install the filtered MongoDB collection",
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Build and activate discovery only after cleanup succeeds",
    )
    run_limit = parser.add_mutually_exclusive_group()
    run_limit.add_argument("--max-papers", type=int)
    run_limit.add_argument("--run-papers", type=int)
    run_limit.add_argument("--run-minutes", type=float)
    parser.add_argument("--qdrant-url")
    parser.add_argument("--ollama-url")
    parser.add_argument("--embedding-model")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)
    if args.index and not args.apply:
        raise SystemExit("--index requires --apply")
    config = load_config(args.config)
    mongo = config.get("mongo", {})
    corpus_settings = config.get("kaggle_corpus", {})
    discovery_settings = config.get("discovery_index", {})
    policy = KaggleRetentionPolicy.from_config(
        corpus_settings,
        categories=retained_categories_from_env(),
    )
    connection_string = (
        os.getenv("MONGO_CONNECTION_STRING")
        or os.getenv("MONGO_URI")
        or (
            mongo.get("connection_string")
            if os.path.exists("/.dockerenv")
            else mongo.get("connection_string_local")
        )
        or "mongodb://localhost:27017/"
    )
    client: MongoClient[dict[str, Any]] = MongoClient(connection_string)
    try:
        database = client[os.getenv("MONGO_DB", mongo.get("db_name", "arxiv_papers"))]
        target_collection = str(
            args.target_collection
            or corpus_settings.get("collection_name")
            or "arxiv_kaggle"
        )
        source_collection = str(
            args.source_collection
            or corpus_settings.get("import_collection")
            or target_collection
        )
        cleanup = KaggleCorpusCleaner(database).clean(
            source_collection=source_collection,
            target_collection=target_collection,
            policy=policy,
            apply=args.apply,
        )
        indexing: dict[str, Any] = {
            "status": "not-requested",
        }
        if args.index:
            repository = KaggleDiscoveryRepository(
                database=database,
                collection_name=str(
                    discovery_settings.get("source_collection") or target_collection
                ),
                eligibility_collection_name=str(
                    discovery_settings.get("eligibility_collection") or "papers"
                ),
                eligibility_id_field=str(
                    discovery_settings.get("eligibility_id_field")
                    or "base_arxiv_id"
                ),
            )
            indexing = run_discovery_index(
                config,
                repository=repository,
                database=database,
                qdrant_url=args.qdrant_url,
                ollama_url=args.ollama_url,
                embedding_model=args.embedding_model,
                max_papers=args.max_papers,
                run_papers=args.run_papers,
                run_minutes=args.run_minutes,
            )
        print(
            json.dumps(
                {
                    "status": "complete",
                    "cleanup": cleanup,
                    "indexing": indexing,
                },
                indent=2,
                default=str,
            )
        )
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
