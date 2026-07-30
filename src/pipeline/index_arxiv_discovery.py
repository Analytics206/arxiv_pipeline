"""Resumably build a physical Qdrant paper-discovery collection."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml
from pymongo import MongoClient

from src.retrieval.discovery_repository import KaggleDiscoveryRepository
from src.retrieval.factory import create_discovery_index


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build or resume the metadata-only hybrid discovery index from "
            "a validated arxiv_kaggle collection"
        )
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument("--collection", help="Physical Qdrant collection override")
    parser.add_argument("--qdrant-url")
    parser.add_argument("--ollama-url")
    parser.add_argument("--embedding-model")
    parser.add_argument("--batch-size", type=int)
    run_limit = parser.add_mutually_exclusive_group()
    run_limit.add_argument(
        "--max-papers",
        type=int,
        help=(
            "Legacy cumulative target count for a smoke/resume pass; "
            "prefer --run-papers for a per-invocation limit"
        ),
    )
    run_limit.add_argument(
        "--run-papers",
        type=int,
        help="Process at most this many additional papers in this invocation",
    )
    run_limit.add_argument(
        "--run-minutes",
        type=float,
        help=(
            "Stop after approximately this many embedding minutes at a batch "
            "boundary; rerunning resumes from the checkpoint"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the source snapshot and target name without indexing",
    )
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Complete the physical collection without updating the current alias",
    )
    return parser


def physical_collection_name(
    *,
    prefix: str,
    snapshot_token: str,
    embedding_model: str,
    schema_version: str,
) -> str:
    identity = hashlib.sha256(
        f"{snapshot_token}:{embedding_model}:{schema_version}".encode("utf-8")
    ).hexdigest()[:12]
    return f"{prefix}_{identity}"


def run_discovery_index(
    config: dict[str, Any],
    *,
    repository: KaggleDiscoveryRepository,
    database: Any,
    collection_name: str | None = None,
    qdrant_url: str | None = None,
    ollama_url: str | None = None,
    embedding_model: str | None = None,
    batch_size: int | None = None,
    max_papers: int | None = None,
    run_papers: int | None = None,
    run_minutes: float | None = None,
    dry_run: bool = False,
    activate: bool = True,
) -> dict[str, Any]:
    settings = config.get("discovery_index", {})
    snapshot = repository.snapshot_identity()
    selected_model = str(
        embedding_model
        or settings.get("embedding_model")
        or config.get("research_index", {}).get("embedding_model")
        or "mxbai-embed-large:latest"
    )
    schema_version = str(settings.get("schema_version", "1.0"))
    physical_collection = collection_name or physical_collection_name(
        prefix=str(settings.get("collection_prefix") or "arxiv_discovery_hybrid_v1"),
        snapshot_token=str(snapshot["snapshot_token"]),
        embedding_model=selected_model,
        schema_version=schema_version,
    )
    source_count = int(snapshot["documents"])
    if sum(
        option is not None
        for option in (max_papers, run_papers, run_minutes)
    ) > 1:
        raise ValueError(
            "max_papers, run_papers, and run_minutes are mutually exclusive"
        )
    if max_papers is not None and max_papers < 1:
        raise ValueError("max_papers must be positive")
    if run_papers is not None and run_papers < 1:
        raise ValueError("run_papers must be positive")
    if run_minutes is not None and run_minutes <= 0:
        raise ValueError("run_minutes must be positive")

    checkpoint_name = str(
        settings.get("checkpoint_collection") or "discovery_index_runs"
    )
    checkpoints = database[checkpoint_name]
    checkpoint = checkpoints.find_one({"_id": physical_collection}) or {}
    checkpoint_processed = int(checkpoint.get("processed", 0))
    remaining_at_plan = max(0, source_count - checkpoint_processed)
    if max_papers is not None:
        target_at_plan: int | None = min(source_count, max_papers)
        planned_run_documents: int | None = max(
            0,
            target_at_plan - checkpoint_processed,
        )
    elif run_papers is not None:
        target_at_plan = min(
            source_count,
            checkpoint_processed + run_papers,
        )
        planned_run_documents = min(run_papers, remaining_at_plan)
    elif run_minutes is not None:
        target_at_plan = None
        planned_run_documents = None
    else:
        target_at_plan = source_count
        planned_run_documents = remaining_at_plan
    plan = {
        "event": "arxiv_discovery_index",
        "status": "dry-run" if dry_run else "ready",
        "timestamp": datetime.now(timezone.utc),
        "dry_run": dry_run,
        "source_collection": settings.get(
            "source_collection",
            "arxiv_kaggle",
        ),
        "eligibility_collection": snapshot.get("eligibility_collection", "papers"),
        "eligibility_id_field": snapshot.get(
            "eligibility_id_field",
            "base_arxiv_id",
        ),
        "candidate_documents": snapshot.get("candidate_documents", source_count),
        "source_documents": source_count,
        "already_processed": checkpoint_processed,
        "remaining_documents": remaining_at_plan,
        "selected_documents": planned_run_documents,
        "target_documents": target_at_plan,
        "run_papers": run_papers,
        "run_minutes": run_minutes,
        "source_snapshot": snapshot,
        "physical_collection": physical_collection,
        "alias_name": settings.get(
            "alias_name",
            "arxiv_discovery_current",
        ),
        "embedding_model": selected_model,
        "schema_version": schema_version,
        "will_activate_alias": bool(
            activate
            and run_minutes is None
            and target_at_plan == source_count
        ),
    }
    if dry_run:
        return plan
    if not snapshot["prepared"]:
        raise RuntimeError(
            "The discovery source is not a validated Kaggle cleanup output; "
            "run clean_kaggle_collection --apply first"
        )
    if source_count < 1:
        raise RuntimeError(
            "No arxiv_kaggle papers match the configured papers collection; "
            "nothing is eligible for discovery indexing"
        )
    processed = checkpoint_processed
    last_id = checkpoint.get("last_id")
    index = create_discovery_index(
        config,
        qdrant_url=qdrant_url,
        ollama_url=ollama_url,
        embedding_model=selected_model,
        collection_name=physical_collection,
        use_alias=False,
    )
    if processed and not index.exists():
        processed = 0
        last_id = None
    elif index.exists():
        existing_points = index.count()
        if existing_points != processed:
            raise RuntimeError(
                "Discovery checkpoint/Qdrant mismatch before resume: "
                f"checkpoint has {processed}, collection has {existing_points}"
            )
    if max_papers is not None and processed > min(source_count, max_papers):
        raise RuntimeError(
            f"Checkpoint has already processed {processed} papers, which "
            f"exceeds this run's --max-papers limit of "
            f"{min(source_count, max_papers)}"
        )
    if batch_size is not None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        index.batch_size = batch_size
    selected_batch_size = int(batch_size or settings.get("embedding_batch_size", 32))
    run_started_processed = processed
    if max_papers is not None:
        run_target = min(source_count, max_papers)
        remaining_limit = max(0, run_target - processed)
    elif run_papers is not None:
        run_target = min(source_count, processed + run_papers)
        remaining_limit = max(0, run_target - processed)
    else:
        run_target = source_count
        remaining_limit = None
    vector_started = perf_counter()
    runtime_seconds = run_minutes * 60 if run_minutes is not None else None
    checkpoints.update_one(
        {"_id": physical_collection},
        {
            "$set": {
                "status": "running",
                "source_snapshot": snapshot,
                "embedding_model": selected_model,
                "schema_version": schema_version,
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {
                "created_at": datetime.now(timezone.utc),
                "processed": processed,
            },
            "$unset": {
                "error": "",
            },
        },
        upsert=True,
    )
    try:
        for documents in repository.iter_batches(
            batch_size=selected_batch_size,
            after_id=str(last_id) if last_id else None,
            limit=remaining_limit,
        ):
            if (
                runtime_seconds is not None
                and processed > run_started_processed
                and perf_counter() - vector_started >= runtime_seconds
            ):
                break
            result = index.index_documents(documents)
            processed += int(result["points"])
            last_id = str(documents[-1]["id"])
            checkpoints.update_one(
                {"_id": physical_collection},
                {
                    "$set": {
                        "status": "running",
                        "processed": processed,
                        "points": processed,
                        "last_id": last_id,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

        point_count = index.count()
        if point_count != processed:
            raise RuntimeError(
                f"Discovery index count mismatch: expected {processed}, "
                f"found {point_count}"
            )
        vector_elapsed = perf_counter() - vector_started
        run_processed = processed - run_started_processed
        complete = point_count == source_count
        alias_activated = False
        if complete and activate:
            index.activate_alias()
            alias_activated = True
        status = "complete" if complete else "partial"
        completed = {
            **plan,
            "status": status,
            "dry_run": False,
            "already_processed": run_started_processed,
            "selected_documents": run_processed,
            "processed": processed,
            "points": point_count,
            "last_id": last_id,
            "run_target_documents": run_target,
            "run_started_processed": run_started_processed,
            "run_processed": run_processed,
            "run_elapsed_seconds": vector_elapsed,
            "throughput_papers_per_second": (
                run_processed / vector_elapsed if vector_elapsed > 0 else None
            ),
            "remaining_documents": max(0, source_count - point_count),
            "alias_activated": alias_activated,
        }
        checkpoints.update_one(
            {"_id": physical_collection},
            {
                "$set": {
                    **completed,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return completed
    except Exception as error:
        checkpoints.update_one(
            {"_id": physical_collection},
            {
                "$set": {
                    "status": "failed",
                    "processed": processed,
                    "last_id": last_id,
                    "error": str(error),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        raise


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    mongo = config.get("mongo", {})
    settings = config.get("discovery_index", {})
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
        repository = KaggleDiscoveryRepository(
            database=database,
            collection_name=str(settings.get("source_collection") or "arxiv_kaggle"),
            eligibility_collection_name=str(
                settings.get("eligibility_collection") or "papers"
            ),
            eligibility_id_field=str(
                settings.get("eligibility_id_field") or "base_arxiv_id"
            ),
        )
        report = run_discovery_index(
            config,
            repository=repository,
            database=database,
            collection_name=args.collection,
            qdrant_url=args.qdrant_url,
            ollama_url=args.ollama_url,
            embedding_model=args.embedding_model,
            batch_size=args.batch_size,
            max_papers=args.max_papers,
            run_papers=args.run_papers,
            run_minutes=args.run_minutes,
            dry_run=args.dry_run,
            activate=not args.no_activate,
        )
        print(json.dumps(report, indent=2, default=str))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
