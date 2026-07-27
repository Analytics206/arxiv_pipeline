"""Run the canonical agent-first paper process from arXiv through search."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import os

from dotenv import load_dotenv

from src.analysis.identity import normalize_arxiv_id
from src.analysis.repository import AnalysisRepository
from src.ingestion.fetch import ArxivClient
from src.ingestion.pdf_download import (
    download_paper_pdf,
    resolve_pdf_directory,
)
from src.pipeline.summarize_paper import main as summarize_paper
from src.retrieval.factory import create_research_index, load_project_config
from src.storage.mongo import MongoStorage
from src.utils.ai_services import resolve_ollama_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch metadata and PDF, analyze the paper, and index it for agents"
        )
    )
    parser.add_argument("--paper-id", required=True, help="arXiv ID or URL")
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--pdf-directory",
        help="Override PDF_STORAGE_DIR and pdf_storage.directory",
    )
    parser.add_argument("--model", help="Override the analysis model")
    parser.add_argument("--embedding-model")
    parser.add_argument("--collection")
    parser.add_argument("--ollama-url")
    parser.add_argument("--qdrant-url")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--force-analysis", action="store_true")
    parser.add_argument(
        "--refresh-metadata",
        action="store_true",
        help="Fetch arXiv again even when this exact version is in MongoDB",
    )
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)
    config = load_project_config(args.config)
    requested = normalize_arxiv_id(args.paper_id)
    mongo = config.get("mongo", {})
    mongo_uri = (
        os.getenv("MONGO_CONNECTION_STRING")
        or os.getenv("MONGO_URI")
        or (
            mongo.get("connection_string")
            if os.path.exists("/.dockerenv")
            else mongo.get("connection_string_local")
        )
        or "mongodb://localhost:27017/"
    )
    db_name = os.getenv("MONGO_DB", mongo.get("db_name", "arxiv_papers"))

    existing_repository = AnalysisRepository(
        connection_string=mongo_uri,
        db_name=db_name,
        collection_name=config.get("analysis", {}).get(
            "collection_name",
            "paper_analyses",
        ),
    )
    try:
        existing_paper = (
            existing_repository.find_paper(requested.version_id)
            if requested.version is not None and not args.refresh_metadata
            else None
        )
    finally:
        existing_repository.close()

    metadata_status = "reused" if existing_paper else "stored"
    paper = existing_paper
    if paper is None:
        client = ArxivClient(max_results=1)
        paper = client.fetch_paper_by_id(requested.version_id)
    identity = normalize_arxiv_id(paper["id"])
    pdf_directory, portable_directory = resolve_pdf_directory(
        config,
        explicit_directory=args.pdf_directory,
    )

    with MongoStorage(
        connection_string=mongo_uri,
        db_name=db_name,
    ) as storage:
        metadata_stats = (
            storage.store_papers([paper])
            if metadata_status == "stored"
            else {
                "inserted": 0,
                "updated": 0,
            }
        )
        pdf = download_paper_pdf(
            paper,
            identity,
            directory=pdf_directory,
            portable_directory=portable_directory,
            force=args.force_download,
        )
        storage.record_pdf(
            paper_id=paper["id"],
            arxiv_id=identity.version_id,
            local_pdf_path=pdf.storage_path,
            document_hash=pdf.sha256,
            size_bytes=pdf.size_bytes,
        )

    repository = AnalysisRepository(
        connection_string=mongo_uri,
        db_name=db_name,
        collection_name=config.get("analysis", {}).get(
            "collection_name",
            "paper_analyses",
        ),
    )
    try:
        analysis_config = config.get("analysis", {})
        model_name = resolve_ollama_model(config, explicit_model=args.model)
        analysis = (
            repository.find_matching_analysis(
                paper_id=identity.base_id,
                document_hash=pdf.sha256,
                schema_version=str(analysis_config.get("schema_version", "1.0")),
                prompt_version=analysis_config.get(
                    "prompt_version",
                    "agent-paper-v5",
                ),
                model=model_name,
            )
            if not args.force_analysis
            else None
        )
        analysis_status = "unchanged" if analysis is not None else "created"
        if analysis is None:
            summarize_arguments = [
                "--paper-id",
                identity.version_id,
                "--pdf",
                str(pdf.path),
                "--config",
                args.config,
                "--compact",
            ]
            if args.model:
                summarize_arguments.extend(["--model", args.model])
            if args.ollama_url:
                summarize_arguments.extend(["--ollama-url", args.ollama_url])
            if args.force_analysis:
                summarize_arguments.append("--force")
                analysis_status = "regenerated"
            if args.no_cache:
                summarize_arguments.append("--no-cache")
            with contextlib.redirect_stdout(io.StringIO()):
                summarize_paper(summarize_arguments)
            analysis = repository.find_matching_analysis(
                paper_id=identity.base_id,
                document_hash=pdf.sha256,
                schema_version=str(analysis_config.get("schema_version", "1.0")),
                prompt_version=analysis_config.get(
                    "prompt_version",
                    "agent-paper-v5",
                ),
                model=model_name,
            )
        if analysis is None:
            raise RuntimeError(f"Analysis was not stored for {identity.version_id}")
        index_result = None
        if not args.skip_index:
            index = create_research_index(
                config,
                qdrant_url=args.qdrant_url,
                ollama_url=args.ollama_url,
                embedding_model=args.embedding_model,
                collection_name=args.collection,
            )
            index_result = index.index_analysis(analysis)
    finally:
        repository.close()

    print(
        json.dumps(
            {
                "status": "complete",
                "paper_id": identity.base_id,
                "paper_version_id": identity.version_id,
                "resource_uri": identity.resource_uri,
                "title": paper["title"],
                "stages": {
                    "metadata": {
                        "status": metadata_status,
                        "inserted": metadata_stats["inserted"],
                        "updated": metadata_stats["updated"],
                    },
                    "pdf": {
                        "status": pdf.status,
                        "path": pdf.storage_path,
                        "size_bytes": pdf.size_bytes,
                        "sha256": pdf.sha256,
                    },
                    "analysis": {
                        "status": analysis_status,
                        "prompt_version": analysis.prompt_version,
                        "model": analysis.model,
                        "evidence_count": len(analysis.evidence),
                    },
                    "index": index_result
                    or {
                        "status": "skipped",
                    },
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
