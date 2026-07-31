"""Run the canonical multi-source search evaluation against live services."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pymongo import MongoClient

from src.retrieval.curated_evaluation import (
    CuratedSearchSuite,
    evaluate_curated_search,
)
from src.retrieval.curated_service import CuratedResearchService
from src.retrieval.discovery_repository import KaggleDiscoveryRepository
from src.retrieval.factory import (
    create_discovery_index,
    create_research_index,
    load_project_config,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate the canonical paper-centric research search"
    )
    parser.add_argument(
        "--suite",
        default="evals/retrieval/curated_research.json",
    )
    parser.add_argument("--output")
    parser.add_argument("--config", default="config/default.yaml")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_project_config(args.config)
    suite = CuratedSearchSuite.model_validate_json(
        Path(args.suite).read_text(encoding="utf-8")
    )
    mongo = config.get("mongo", {})
    discovery = config.get("discovery_index", {})
    connection_string = (
        os.getenv("MONGO_CONNECTION_STRING")
        or (
            mongo.get("connection_string")
            if os.path.exists("/.dockerenv")
            else mongo.get("connection_string_local")
        )
        or "mongodb://localhost:27017/"
    )
    client: MongoClient = MongoClient(connection_string)
    repository = KaggleDiscoveryRepository(
        database=client[os.getenv("MONGO_DB", mongo.get("db_name", "arxiv_papers"))],
        collection_name=str(discovery.get("source_collection") or "arxiv_kaggle"),
        eligibility_collection_name=str(
            discovery.get("eligibility_collection") or "papers"
        ),
        eligibility_id_field=str(
            discovery.get("eligibility_id_field") or "base_arxiv_id"
        ),
    )
    settings = config.get("research_search", {})
    try:
        service = CuratedResearchService(
            research_index=create_research_index(config),
            discovery_index=create_discovery_index(config),
            metadata_repository=repository,
            candidate_multiplier=int(settings.get("candidate_multiplier", 6)),
            candidate_minimum=int(settings.get("candidate_minimum", 50)),
            evidence_weight=float(settings.get("evidence_weight", 1.0)),
            discovery_weight=float(settings.get("discovery_weight", 1.0)),
            rrf_k=int(settings.get("rrf_k", 60)),
            default_evidence_items_per_paper=int(
                settings.get("evidence_items_per_paper", 3)
            ),
            default_token_budget=int(settings.get("token_budget", 12000)),
            maximum_abstract_chars=int(settings.get("maximum_abstract_chars", 2400)),
        )
        report = evaluate_curated_search(service, suite)
        document = report.model_dump_json(indent=2)
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(document + "\n", encoding="utf-8")
        print(document)
        return 0 if report.pass_rate == 1.0 else 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
