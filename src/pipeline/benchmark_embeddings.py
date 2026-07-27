"""Index and evaluate an isolated collection for each embedding candidate."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.analysis.repository import AnalysisRepository
from src.retrieval.benchmark import (
    load_benchmark_report,
    load_benchmark_matrix,
    merge_benchmark_reports,
    run_embedding_benchmark,
    save_benchmark_report,
)
from src.retrieval.evaluation import load_evaluation_suite
from src.retrieval.factory import (
    load_project_config,
    resolve_qdrant_url,
)
from src.utils.ai_services import resolve_ollama_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Index current analyses into isolated per-model Qdrant collections "
            "and compare retrieval quality"
        )
    )
    parser.add_argument(
        "--suite",
        default="evals/retrieval/agent_research_v2.json",
    )
    parser.add_argument(
        "--matrix",
        default="evals/retrieval/embedding_models_v2.json",
    )
    parser.add_argument(
        "--config",
        default="config/default.yaml",
    )
    parser.add_argument(
        "--output",
        default="data/retrieval_evals/embedding_benchmark_v2.json",
    )
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Run only this exact model name; may be repeated",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Evaluate collections that have already been indexed",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Merge selected-model results into an existing output report",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print compact model metrics instead of every evaluated case",
    )
    parser.add_argument("--qdrant-url")
    parser.add_argument("--ollama-url")
    parser.add_argument(
        "--max-papers",
        type=int,
        default=100,
        help="Safety bound for current analyses loaded from MongoDB",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_project_config(args.config)
    suite = load_evaluation_suite(args.suite)
    matrix = load_benchmark_matrix(args.matrix)
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
        analyses = repository.get_current_analyses(limit=args.max_papers)
        if not analyses:
            raise SystemExit("No current analyses are available to benchmark")
        report = run_embedding_benchmark(
            config=config,
            suite=suite,
            matrix=matrix,
            analyses=analyses,
            ollama_url=resolve_ollama_url(
                config,
                explicit_url=args.ollama_url,
            ),
            qdrant_url=resolve_qdrant_url(
                config,
                explicit_url=args.qdrant_url,
            ),
            selected_models=set(args.models) if args.models else None,
            skip_index=args.skip_index,
        )
        if args.resume and Path(args.output).exists():
            report = merge_benchmark_reports(
                load_benchmark_report(args.output),
                report,
            )
        save_benchmark_report(report, args.output)
        payload = report.model_dump(mode="json")
        if args.summary_only:
            payload = {
                "benchmark_id": report.benchmark_id,
                "suite_id": report.suite_id,
                "results": [
                    {
                        "embedding_model": result.embedding_model,
                        "status": result.status,
                        "model_size_bytes": result.model_size_bytes,
                        "point_count": result.point_count,
                        "vector_size": result.vector_size,
                        "index_duration_ms": result.index_duration_ms,
                        "recall_at_limit": (
                            result.evaluation.recall_at_limit
                            if result.evaluation
                            else None
                        ),
                        "mean_reciprocal_rank": (
                            result.evaluation.mean_reciprocal_rank
                            if result.evaluation
                            else None
                        ),
                        "group_recall_at_limit": (
                            result.evaluation.group_recall_at_limit
                            if result.evaluation
                            else None
                        ),
                        "full_group_recall_at_limit": (
                            result.evaluation.full_group_recall_at_limit
                            if result.evaluation
                            else None
                        ),
                        "mean_latency_ms": (
                            result.evaluation.mean_latency_ms
                            if result.evaluation
                            else None
                        ),
                        "p95_latency_ms": (
                            result.evaluation.p95_latency_ms
                            if result.evaluation
                            else None
                        ),
                        "score_separation": (
                            result.evaluation.score_separation
                            if result.evaluation
                            else None
                        ),
                        "error": result.error,
                    }
                    for result in report.results
                ],
            }
        print(json.dumps(payload, indent=2))
        if any(result.status == "failed" for result in report.results):
            raise SystemExit(1)
    finally:
        repository.close()


if __name__ == "__main__":
    main()
