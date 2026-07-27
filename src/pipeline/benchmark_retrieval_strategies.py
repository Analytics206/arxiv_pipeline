"""Build one hybrid index and evaluate a matrix of retrieval strategies."""

from __future__ import annotations

import argparse
import json
import os

from src.analysis.repository import AnalysisRepository
from src.retrieval.evaluation import load_evaluation_suite
from src.retrieval.factory import (
    load_project_config,
    resolve_qdrant_url,
)
from src.retrieval.strategy_benchmark import (
    load_strategy_matrix,
    run_strategy_benchmark,
    save_strategy_report,
)
from src.utils.ai_services import resolve_ollama_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare dense, hybrid, and diversity-reranked retrieval over "
            "the same reviewed evidence judgments"
        )
    )
    parser.add_argument(
        "--suite",
        default="evals/retrieval/agent_research_v2.json",
    )
    parser.add_argument(
        "--matrix",
        default="evals/retrieval/hybrid_strategies_v1.json",
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--output",
        default="data/retrieval_evals/hybrid_strategies_v1.json",
    )
    parser.add_argument(
        "--skip-index",
        action="store_true",
        help="Reuse an already populated hybrid collection",
    )
    parser.add_argument("--qdrant-url")
    parser.add_argument("--ollama-url")
    parser.add_argument("--max-papers", type=int, default=100)
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print aggregate strategy metrics instead of every case",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_project_config(args.config)
    suite = load_evaluation_suite(args.suite)
    matrix = load_strategy_matrix(args.matrix)
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
        report = run_strategy_benchmark(
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
            skip_index=args.skip_index,
        )
        save_strategy_report(report, args.output)
        payload = report.model_dump(mode="json")
        if args.summary_only:
            payload = {
                "benchmark_id": report.benchmark_id,
                "suite_id": report.suite_id,
                "selected_strategy_id": report.selected_strategy_id,
                "index_duration_ms": report.index_duration_ms,
                "point_count": report.point_count,
                "results": [
                    {
                        "strategy_id": result.strategy_id,
                        "retrieval_mode": result.retrieval_mode,
                        "candidate_multiplier": result.candidate_multiplier,
                        "candidate_minimum": result.candidate_minimum,
                        "dense_weight": result.dense_weight,
                        "sparse_weight": result.sparse_weight,
                        "paper_diversity_penalty": (result.paper_diversity_penalty),
                        "recall_at_limit": (result.evaluation.recall_at_limit),
                        "mean_reciprocal_rank": (
                            result.evaluation.mean_reciprocal_rank
                        ),
                        "group_recall_at_limit": (
                            result.evaluation.group_recall_at_limit
                        ),
                        "full_group_recall_at_limit": (
                            result.evaluation.full_group_recall_at_limit
                        ),
                        "group_recall_at_5": (result.evaluation.group_recall_at_5),
                        "group_recall_at_8": (result.evaluation.group_recall_at_8),
                        "full_group_recall_at_5": (
                            result.evaluation.full_group_recall_at_5
                        ),
                        "full_group_recall_at_8": (
                            result.evaluation.full_group_recall_at_8
                        ),
                        "mean_latency_ms": (result.evaluation.mean_latency_ms),
                        "p95_latency_ms": result.evaluation.p95_latency_ms,
                    }
                    for result in report.results
                ],
            }
        print(json.dumps(payload, indent=2))
    finally:
        repository.close()


if __name__ == "__main__":
    main()
