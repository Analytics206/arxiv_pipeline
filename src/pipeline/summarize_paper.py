"""Analyze one local paper PDF and persist agent-ready research context."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.analysis.cache import JsonChunkAnalysisCache
from src.analysis.identity import PaperIdentity, normalize_arxiv_id
from src.analysis.ollama_summarizer import (
    EvidenceAwareSummarizer,
    OllamaStructuredModel,
)
from src.analysis.pdf_parser import parse_pdf
from src.analysis.repository import AnalysisRepository
from src.utils.ai_services import resolve_ollama_model, resolve_ollama_url


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Create a versioned, evidence-backed analysis of one arXiv paper")
    )
    parser.add_argument(
        "--paper-id",
        help="arXiv ID or URL; inferred from the PDF filename when omitted",
    )
    parser.add_argument("--pdf", help="Explicit path to a local PDF")
    parser.add_argument("--title", help="Override the paper title")
    parser.add_argument(
        "--config", default="config/default.yaml", help="YAML configuration path"
    )
    parser.add_argument("--model", help="Override the configured Ollama model")
    parser.add_argument("--ollama-url", help="Override the shared Ollama URL")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run the model again even when this exact analysis already exists",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not read or write resumable chunk-analysis cache files",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print only status and analysis identity instead of the full analysis",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    analysis_config = config.get("analysis", {})
    mongo_config = config.get("mongo", {})

    connection_string = (
        os.getenv("MONGO_URI")
        or os.getenv("MONGO_CONNECTION_STRING")
        or mongo_config.get("connection_string_local")
        or "mongodb://localhost:27017/"
    )
    db_name = os.getenv("MONGO_DB", mongo_config.get("db_name", "arxiv_papers"))
    collection_name = analysis_config.get("collection_name", "paper_analyses")

    with AnalysisRepository(
        connection_string=connection_string,
        db_name=db_name,
        collection_name=collection_name,
    ) as repository:
        paper = repository.find_paper(args.paper_id) if args.paper_id else None
        identity = _resolve_identity(args.paper_id, args.pdf, paper)
        pdf_path = _resolve_pdf_path(args.pdf, paper, identity, config)
        document = parse_pdf(pdf_path)
        title = args.title or (paper or {}).get("title") or identity.version_id

        model_name = resolve_ollama_model(config, explicit_model=args.model)
        schema_version = str(analysis_config.get("schema_version", "1.0"))
        prompt_version = analysis_config.get("prompt_version", "agent-paper-v5")
        if not args.force:
            existing = repository.find_matching_analysis(
                paper_id=identity.base_id,
                document_hash=document.document_hash,
                schema_version=schema_version,
                prompt_version=prompt_version,
                model=model_name,
            )
            if existing is not None:
                output = {
                    "status": "unchanged",
                    "reason": "matching analysis already exists",
                    "analysis": existing.model_dump(mode="json"),
                }
                if args.compact:
                    output = {
                        "status": "unchanged",
                        "reason": "matching analysis already exists",
                        "paper_id": existing.paper_id,
                        "paper_version_id": existing.paper_version_id,
                        "prompt_version": existing.prompt_version,
                        "model": existing.model,
                        "document_hash": existing.document_hash,
                    }
                print(
                    json.dumps(
                        output,
                        indent=2,
                    )
                )
                return 0

        ollama_url = resolve_ollama_url(
            config,
            explicit_url=args.ollama_url,
        )
        model = OllamaStructuredModel(
            model_name=model_name,
            host=ollama_url,
            context_length=int(analysis_config.get("context_length", 12288)),
            max_output_tokens=int(analysis_config.get("max_output_tokens", 4096)),
        )
        chunk_cache = None
        if not args.no_cache:
            chunk_cache = JsonChunkAnalysisCache(
                analysis_config.get("cache_directory", "data/analysis_cache")
            )
        summarizer = EvidenceAwareSummarizer(
            model,
            schema_version=schema_version,
            prompt_version=prompt_version,
            chunk_max_chars=int(analysis_config.get("chunk_max_chars", 12_000)),
            chunk_cache=chunk_cache,
        )
        analysis = summarizer.summarize(
            document=document,
            identity=identity,
            title=title,
        )
        analysis_id = repository.save_analysis(analysis)
        output = {
            "status": "created",
            "analysis_id": analysis_id,
            "analysis": analysis.model_dump(mode="json"),
        }
        if args.compact:
            output = {
                "status": "created",
                "analysis_id": analysis_id,
                "paper_id": analysis.paper_id,
                "paper_version_id": analysis.paper_version_id,
                "prompt_version": analysis.prompt_version,
                "model": analysis.model,
                "document_hash": analysis.document_hash,
                "evidence_count": len(analysis.evidence),
            }
        print(
            json.dumps(
                output,
                indent=2,
            )
        )
    return 0


def _resolve_identity(
    paper_id: str | None,
    pdf_path: str | None,
    paper: dict[str, Any] | None,
) -> PaperIdentity:
    candidates = [
        paper_id,
        (paper or {}).get("arxiv_id"),
        (paper or {}).get("pdf_url"),
        (paper or {}).get("id"),
        Path(pdf_path).stem if pdf_path else None,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return normalize_arxiv_id(str(candidate))
        except ValueError:
            continue
    raise ValueError(
        "Could not determine an arXiv ID; pass --paper-id with an arXiv ID or URL"
    )


def _resolve_pdf_path(
    explicit_path: str | None,
    paper: dict[str, Any] | None,
    identity: PaperIdentity,
    config: dict[str, Any],
) -> Path:
    if explicit_path:
        return Path(explicit_path)

    local_path = (paper or {}).get("local_pdf_path")
    if local_path and Path(local_path).is_file():
        return Path(local_path)

    base_directory = Path(config.get("pdf_storage", {}).get("directory", "data/pdfs"))
    categories = (paper or {}).get("categories") or ["uncategorized"]
    version_ids = [identity.version_id, identity.base_id]
    candidates: list[Path] = []
    for version_id in version_ids:
        candidates.append(base_directory / f"{version_id}.pdf")
        for category in categories:
            candidates.append(base_directory / category / f"{version_id}.pdf")
            candidates.append(Path("/app/data/pdfs") / category / f"{version_id}.pdf")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    rendered = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise FileNotFoundError(
        "Could not locate the paper PDF. Pass --pdf explicitly. Checked:\n"
        f"{rendered}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
