"""Evaluate token-budgeted context packages over current MongoDB analyses."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.analysis.context_evaluation import evaluate_context_packages
from src.analysis.repository import AnalysisRepository
from src.retrieval.factory import load_project_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate agent context budget compliance, evidence closure, "
            "determinism, and monotonic selection"
        )
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--paper-id",
        action="append",
        dest="paper_ids",
        help="Limit evaluation to an arXiv ID; repeat for multiple papers",
    )
    parser.add_argument("--max-papers", type=int, default=100)
    parser.add_argument(
        "--output",
        default="data/context_evals/agent_context_packages_v1.json",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_project_config(args.config)
    mongo = config.get("mongo", {})
    connection_string = os.getenv("MONGO_CONNECTION_STRING")
    if not connection_string:
        connection_string = (
            mongo.get("connection_string")
            if os.path.exists("/.dockerenv")
            else mongo.get("connection_string_local")
        )
    repository = AnalysisRepository(
        connection_string=connection_string or "mongodb://localhost:27017/",
        db_name=os.getenv("MONGO_DB", mongo.get("db_name", "arxiv_papers")),
        collection_name=os.getenv(
            "MONGO_ANALYSIS_COLLECTION",
            config.get("analysis", {}).get(
                "collection_name",
                "paper_analyses",
            ),
        ),
    )
    try:
        analyses = repository.get_current_analyses(
            paper_ids=args.paper_ids,
            limit=args.max_papers,
        )
        contexts = [
            context
            for analysis in analyses
            if (context := repository.get_agent_context(analysis.paper_id)) is not None
        ]
        if not contexts:
            raise SystemExit("No current analyses are available to evaluate")
        report = evaluate_context_packages(contexts)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "output": str(output_path),
                    "paper_count": report["paper_count"],
                    "package_count": report["package_count"],
                    "all_passed": report["all_passed"],
                    "rates": report["rates"],
                    "profile_summaries": report["profile_summaries"],
                },
                indent=2,
            )
        )
        if not report["all_passed"]:
            raise SystemExit(1)
    finally:
        repository.close()


if __name__ == "__main__":
    main()
