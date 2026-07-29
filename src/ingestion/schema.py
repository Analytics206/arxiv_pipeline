"""Canonical MongoDB metadata schema for versioned arXiv papers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.analysis.identity import PaperIdentity, normalize_arxiv_id

PAPER_METADATA_SCHEMA_VERSION = "2.0"


def paper_identity_from_metadata(paper: Mapping[str, Any]) -> PaperIdentity:
    """Resolve an arXiv identity from a paper metadata document."""

    for field in ("arxiv_id", "id", "arxiv_url", "pdf_url"):
        value = paper.get(field)
        if value:
            return normalize_arxiv_id(str(value))
    raise ValueError("Paper metadata contains no arXiv identifier")


def canonicalize_paper_metadata(paper: Mapping[str, Any]) -> dict[str, Any]:
    """Return one version-aware paper document using stable identity fields."""

    identity = paper_identity_from_metadata(paper)
    canonical = dict(paper)
    canonical.update(
        {
            "paper_schema_version": PAPER_METADATA_SCHEMA_VERSION,
            "base_arxiv_id": identity.base_id,
            "arxiv_id": identity.version_id,
            "arxiv_version": identity.version,
            "id": f"https://arxiv.org/abs/{identity.version_id}",
            "arxiv_url": f"https://arxiv.org/abs/{identity.version_id}",
            "pdf_url": f"https://arxiv.org/pdf/{identity.version_id}",
        }
    )
    return canonical


def paper_version_sort_key(paper: Mapping[str, Any]) -> tuple[int, str, str]:
    """Order versions deterministically, preferring the newest arXiv version."""

    identity = paper_identity_from_metadata(paper)
    version = identity.version if identity.version is not None else -1
    return (
        version,
        str(paper.get("updated") or ""),
        str(paper.get("ingestion_timestamp") or ""),
    )
