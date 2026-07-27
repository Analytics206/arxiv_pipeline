"""Index the latest canonical analysis for one paper in Qdrant."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.analysis.repository import AnalysisRepository
from src.retrieval.factory import create_research_index, load_project_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Index one paper analysis for agent semantic retrieval"
    )
    parser.add_argument(
        "--paper-id",
        required=True,
        help="Raw arXiv ID or arXiv URL",
    )
    parser.add_argument(
        "--config",
        default="config/default.yaml",
        help="Project YAML configuration path",
    )
    parser.add_argument("--qdrant-url")
    parser.add_argument("--ollama-url")
    parser.add_argument("--embedding-model")
    parser.add_argument(
        "--collection",
        help="Versioned Qdrant collection; required when comparing models",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_project_config(Path(args.config))
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
        analysis = repository.get_latest_analysis(args.paper_id)
        if analysis is None:
            raise SystemExit(f"No stored analysis found for {args.paper_id!r}")
        index = create_research_index(
            config,
            qdrant_url=args.qdrant_url,
            ollama_url=args.ollama_url,
            embedding_model=args.embedding_model,
            collection_name=args.collection,
        )
        result = index.index_analysis(analysis)
        print(json.dumps(result, indent=2))
    finally:
        repository.close()


if __name__ == "__main__":
    main()
