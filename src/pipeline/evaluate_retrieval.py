"""Evaluate a configured research index against a reviewed query suite."""

from __future__ import annotations

import argparse
import json

from src.retrieval.evaluation import (
    evaluate_retrieval,
    load_evaluation_suite,
    save_evaluation_report,
)
from src.retrieval.factory import create_research_index, load_project_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate agent-oriented semantic research retrieval"
    )
    parser.add_argument(
        "--suite",
        default="evals/retrieval/openforge_v1.json",
        help="Reviewed retrieval evaluation suite",
    )
    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="Project YAML configuration path",
    )
    parser.add_argument("--output", help="Optional JSON report path")
    parser.add_argument("--qdrant-url")
    parser.add_argument("--ollama-url")
    parser.add_argument("--embedding-model")
    parser.add_argument(
        "--collection",
        help="Versioned Qdrant collection indexed by the selected model",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_project_config(args.config)
    index = create_research_index(
        config,
        qdrant_url=args.qdrant_url,
        ollama_url=args.ollama_url,
        embedding_model=args.embedding_model,
        collection_name=args.collection,
    )
    suite = load_evaluation_suite(args.suite)
    report = evaluate_retrieval(index, suite)
    if args.output:
        save_evaluation_report(report, args.output)
    print(json.dumps(report.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
