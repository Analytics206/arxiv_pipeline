"""Safe, portable PDF storage for exact paper processing."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from src.analysis.identity import PaperIdentity


class PdfDownloadError(RuntimeError):
    """Raised when a PDF cannot be downloaded or validated."""


@dataclass(frozen=True, slots=True)
class PdfDownloadResult:
    status: str
    path: Path
    storage_path: str
    sha256: str
    size_bytes: int


def resolve_pdf_directory(
    config: dict[str, Any],
    *,
    explicit_directory: str | None = None,
) -> tuple[Path, str]:
    """Return an absolute write path and its portable configured form."""

    configured = (
        explicit_directory
        or os.getenv("PDF_STORAGE_DIR")
        or config.get("pdf_storage", {}).get("directory")
        or "data/pdfs"
    )
    portable = str(Path(configured))
    return Path(configured).expanduser().resolve(), portable


def download_paper_pdf(
    paper: dict[str, Any],
    identity: PaperIdentity,
    *,
    directory: Path,
    portable_directory: str,
    force: bool = False,
    session=None,
    timeout: int = 120,
) -> PdfDownloadResult:
    pdf_url = str(paper.get("pdf_url") or "").strip()
    if not pdf_url:
        raise PdfDownloadError(f"No PDF URL is available for {identity.version_id}")

    categories = paper.get("categories") or ["uncategorized"]
    category = _safe_category(str(categories[0]))
    filename = f"{identity.version_id}.pdf"
    destination = directory / category / filename
    storage_path = str(Path(portable_directory) / category / filename)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.is_file() and not force:
        return _existing_result(destination, storage_path)
    if not force:
        existing_locations = [
            candidate
            for candidate in directory.glob(f"*/{filename}")
            if candidate.is_file() and candidate != destination
        ]
        if len(existing_locations) == 1:
            existing_locations[0].replace(destination)
            existing = _existing_result(destination, storage_path)
            return PdfDownloadResult(
                status="moved",
                path=existing.path,
                storage_path=existing.storage_path,
                sha256=existing.sha256,
                size_bytes=existing.size_bytes,
            )

    partial = destination.with_suffix(".pdf.part")
    client = session or requests.Session()
    try:
        response = client.get(
            pdf_url,
            stream=True,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "arxiv-pipeline/0.7 "
                    "(local research indexing; contact: local-user)"
                )
            },
        )
        response.raise_for_status()
        sha256 = hashlib.sha256()
        size_bytes = 0
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                sha256.update(chunk)
                size_bytes += len(chunk)
        with partial.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise PdfDownloadError(
                    f"Downloaded content for {identity.version_id} is not a PDF"
                )
        partial.replace(destination)
        return PdfDownloadResult(
            status="downloaded",
            path=destination,
            storage_path=storage_path,
            sha256=sha256.hexdigest(),
            size_bytes=size_bytes,
        )
    except (requests.RequestException, OSError) as error:
        raise PdfDownloadError(
            f"Could not download {identity.version_id} from {pdf_url}: {error}"
        ) from error
    finally:
        if partial.exists():
            partial.unlink()


def _existing_result(destination: Path, storage_path: str) -> PdfDownloadResult:
    sha256 = hashlib.sha256()
    with destination.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise PdfDownloadError(f"Existing file is not a PDF: {destination}")
        handle.seek(0)
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha256.update(block)
    return PdfDownloadResult(
        status="unchanged",
        path=destination,
        storage_path=storage_path,
        sha256=sha256.hexdigest(),
        size_bytes=destination.stat().st_size,
    )


def _safe_category(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return cleaned or "uncategorized"
