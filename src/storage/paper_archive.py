"""Planning helpers for retaining only the latest paper version in MongoDB."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from src.ingestion.schema import (
    canonicalize_paper_metadata,
    paper_identity_from_metadata,
    paper_version_sort_key,
)

PAPERS_ARCHIVE_COLLECTION = "papers_archive"


@dataclass(slots=True)
class PaperCleanupPlan:
    """A deterministic latest-version selection over paper documents."""

    current: list[dict[str, Any]]
    archive: list[dict[str, Any]]
    invalid: list[dict[str, Any]]
    base_papers: int

    @property
    def archive_count(self) -> int:
        return len(self.archive)


def build_paper_cleanup_plan(
    documents: Iterable[Mapping[str, Any]],
) -> PaperCleanupPlan:
    """Group documents by base arXiv ID and select the latest version."""

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invalid: list[dict[str, Any]] = []

    for source in documents:
        document = dict(source)
        try:
            identity = paper_identity_from_metadata(document)
        except ValueError:
            invalid.append(document)
            continue
        groups[identity.base_id].append(document)

    current: list[dict[str, Any]] = []
    archive: list[dict[str, Any]] = []
    for base_id in sorted(groups):
        versions = sorted(groups[base_id], key=paper_version_sort_key)
        winner = versions[-1]
        current.append(canonicalize_paper_metadata(winner))
        archive.extend(canonicalize_paper_metadata(item) for item in versions[:-1])

    return PaperCleanupPlan(
        current=current,
        archive=archive,
        invalid=invalid,
        base_papers=len(groups),
    )
