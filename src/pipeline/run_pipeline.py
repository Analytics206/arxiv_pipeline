"""Backward-compatible entry point for the canonical metadata ingestion pipeline."""

from src.pipeline.sync_mongodb import load_config, main, run_ingestion_pipeline

__all__ = ["load_config", "main", "run_ingestion_pipeline"]


if __name__ == "__main__":
    raise SystemExit(main())
