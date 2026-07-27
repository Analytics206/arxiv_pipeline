"""Import a configured, bounded arXiv metadata window into MongoDB."""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.ingestion.fetch import ArxivClient, ArxivFetchError
from src.storage.mongo import MongoStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load configuration from YAML."""

    with Path(config_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def filter_papers_by_date(
    papers: list[dict[str, Any]],
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Filter papers by their ISO published date."""

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    return [
        paper
        for paper in papers
        if "published" in paper
        and start <= datetime.fromisoformat(str(paper["published"])[:10]) <= end
    ]


def _fetch_with_retries(
    client: ArxivClient,
    *,
    category: str,
    search_query: str | None,
    start: int,
    attempts: int = 3,
) -> list[dict[str, Any]]:
    for attempt in range(1, attempts + 1):
        try:
            return client.fetch_papers(
                category=category,
                search_query=search_query,
                start=start,
            )
        except ArxivFetchError:
            if attempt >= attempts:
                raise
            delay = 10 * attempt
            logger.warning(
                "arXiv request failed (%d/%d); retrying in %d seconds",
                attempt,
                attempts,
                delay,
            )
            time.sleep(delay)
    return []


def run_ingestion_pipeline(config: dict[str, Any]) -> dict[str, Any]:
    """Run the arXiv metadata ingestion pipeline."""

    arxiv_config = config["arxiv"]
    arxiv_client = ArxivClient(
        max_results=arxiv_config["max_results"],
        sort_by=arxiv_config["sort_by"],
        sort_order=arxiv_config["sort_order"],
    )
    mongo_uri = (
        os.environ.get("MONGO_CONNECTION_STRING")
        or os.environ.get("MONGO_URI")
        or config["mongo"]["connection_string"]
    )
    mongo_storage = MongoStorage(
        connection_string=mongo_uri,
        db_name=config["mongo"]["db_name"],
    )
    logger.info("Using MongoDB connection: %s", mongo_uri)

    grand_total = 0
    category_totals: dict[str, int] = {}
    try:
        for category in arxiv_config["categories"]:
            logger.info("Processing category: %s", category)
            start = 0
            max_iterations = int(arxiv_config.get("max_iterations", 2))
            max_results = int(arxiv_config["max_results"])
            total_papers = 0
            empty_batches = 0

            for iteration in range(max_iterations):
                logger.info(
                    "Fetching batch %d/%d, start=%d",
                    iteration + 1,
                    max_iterations,
                    start,
                )
                papers = _fetch_with_retries(
                    arxiv_client,
                    category=category,
                    search_query=arxiv_config.get("search_query"),
                    start=start,
                )
                logger.info(
                    "Fetched %d papers from arXiv before filtering",
                    len(papers),
                )

                start_date = arxiv_config.get("start_date")
                end_date = arxiv_config.get("end_date")
                if start_date and end_date:
                    before_filter = len(papers)
                    papers = filter_papers_by_date(
                        papers,
                        start_date,
                        end_date,
                    )
                    logger.info(
                        "%d papers remain after date filtering "
                        "(%d filtered out); range %s to %s",
                        len(papers),
                        before_filter - len(papers),
                        start_date,
                        end_date,
                    )

                if papers:
                    empty_batches = 0
                    mongo_storage.store_papers_bulk(papers)
                    total_papers += len(papers)
                    grand_total += len(papers)
                else:
                    empty_batches += 1
                    logger.info("Empty batch %d", empty_batches)

                start += max_results
                if empty_batches >= int(arxiv_config["max_no_papers"]):
                    logger.info(
                        "No more papers after %d empty batches",
                        empty_batches,
                    )
                    break
                logger.info(
                    "%s progress: %d papers processed",
                    category,
                    total_papers,
                )

                rate_limit = float(arxiv_config.get("rate_limit_seconds", 0))
                if rate_limit > 0 and iteration + 1 < max_iterations:
                    time.sleep(rate_limit)
            category_totals[category] = total_papers
    finally:
        mongo_storage.close()

    result = {
        "total_processed": grand_total,
        "category_totals": category_totals,
    }
    logger.info("Ingestion pipeline completed: %s", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the arXiv metadata ingestion pipeline"
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of idempotent passes",
    )
    args = parser.parse_args(argv)
    config = load_config(args.config)

    for run in range(args.runs):
        logger.info(
            "Starting arXiv ingestion pipeline (run %d/%d)",
            run + 1,
            args.runs,
        )
        started = datetime.now()
        run_ingestion_pipeline(config)
        logger.info(
            "Pipeline run completed in %s",
            datetime.now() - started,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
