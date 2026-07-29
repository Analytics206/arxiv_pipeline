"""Filter an imported Kaggle arXiv collection with an atomic replacement."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import yaml
from pymongo import MongoClient

from src.ingestion.kaggle_corpus import KaggleCorpusCleaner, KaggleRetentionPolicy


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Retain selected exact arXiv category tokens in arxiv_kaggle. "
            "The default is a read-only dry run."
        )
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--category",
        action="append",
        dest="categories",
        help=(
            "Exact category token to retain; repeat to override configured "
            "retained_categories"
        ),
    )
    parser.add_argument(
        "--collection",
        help="Legacy shorthand overriding both source and target collection",
    )
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
        help=(
            "Build, validate, index, and atomically install the filtered "
            "collection; without this flag no writes occur"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    mongo = config.get("mongo", {})
    settings = config.get("kaggle_corpus", {})
    policy = KaggleRetentionPolicy.from_config(
        settings,
        categories=args.categories,
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
            args.collection
            or args.target_collection
            or settings.get("collection_name")
            or "arxiv_kaggle"
        )
        report = KaggleCorpusCleaner(database).clean(
            source_collection=str(
                args.collection
                or args.source_collection
                or settings.get("import_collection")
                or target_collection
            ),
            target_collection=target_collection,
            policy=policy,
            apply=args.apply,
        )
        print(json.dumps(report, indent=2, default=str))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
