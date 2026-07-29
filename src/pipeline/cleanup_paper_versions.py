"""Archive superseded arXiv versions and retain one latest paper document."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import yaml

from src.storage.mongo import MongoStorage


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move superseded arXiv versions from papers to papers_archive "
            "and normalize the retained latest documents"
        )
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the cleanup; without this flag the command is a dry run",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    mongo_uri = (
        os.environ.get("MONGO_CONNECTION_STRING")
        or os.environ.get("MONGO_URI")
        or config["mongo"].get("connection_string_local")
        or config["mongo"]["connection_string"]
    )
    with MongoStorage(
        connection_string=mongo_uri,
        db_name=config["mongo"]["db_name"],
    ) as storage:
        report = storage.cleanup_paper_versions(dry_run=not args.apply)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
