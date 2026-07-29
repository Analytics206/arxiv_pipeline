"""Evaluate the current metadata-only paper discovery alias."""

from __future__ import annotations

import argparse
import json

from src.retrieval.discovery_evaluation import (
    evaluate_discovery,
    load_discovery_suite,
    save_discovery_report,
)
from src.retrieval.factory import create_discovery_index, load_project_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate paper-level metadata discovery"
    )
    parser.add_argument("--suite", required=True)
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--output")
    parser.add_argument("--qdrant-url")
    parser.add_argument("--ollama-url")
    parser.add_argument("--embedding-model")
    parser.add_argument("--collection")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_project_config(args.config)
    index = create_discovery_index(
        config,
        qdrant_url=args.qdrant_url,
        ollama_url=args.ollama_url,
        embedding_model=args.embedding_model,
        collection_name=args.collection,
    )
    report = evaluate_discovery(
        index,
        load_discovery_suite(args.suite),
    )
    if args.output:
        save_discovery_report(report, args.output)
    print(json.dumps(report.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
