"""Stable identity helpers for arXiv papers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

_MODERN_ID = re.compile(r"^(?P<base>\d{4}\.\d{4,5})(?:v(?P<version>\d+))?$")
_LEGACY_ID = re.compile(r"^(?P<base>[A-Za-z0-9.-]+/\d{7})(?:v(?P<version>\d+))?$")


@dataclass(frozen=True, slots=True)
class PaperIdentity:
    """Canonical representation of an arXiv paper and optional version."""

    base_id: str
    version_id: str
    version: int | None

    @property
    def resource_uri(self) -> str:
        return f"paper://arxiv/{self.base_id}"


def normalize_arxiv_id(value: str) -> PaperIdentity:
    """Normalize a raw arXiv ID or arXiv abs/pdf URL.

    Raises:
        ValueError: if ``value`` is not a recognized arXiv identity.
    """

    candidate = _extract_candidate(value)
    match = _MODERN_ID.fullmatch(candidate) or _LEGACY_ID.fullmatch(candidate)
    if not match:
        raise ValueError(f"Unrecognized arXiv identifier: {value!r}")

    base_id = match.group("base")
    version_text = match.group("version")
    version = int(version_text) if version_text else None
    version_id = f"{base_id}v{version}" if version is not None else base_id
    return PaperIdentity(base_id=base_id, version_id=version_id, version=version)


def paper_lookup_aliases(value: str) -> list[str]:
    """Return common MongoDB identity variants in deterministic order."""

    identity = normalize_arxiv_id(value)
    ids = [identity.version_id]
    if identity.base_id != identity.version_id:
        ids.append(identity.base_id)

    aliases: list[str] = []
    for arxiv_id in ids:
        aliases.extend(
            [
                arxiv_id,
                f"https://arxiv.org/abs/{arxiv_id}",
                f"http://arxiv.org/abs/{arxiv_id}",
                f"https://arxiv.org/pdf/{arxiv_id}",
                f"http://arxiv.org/pdf/{arxiv_id}",
                f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                f"http://arxiv.org/pdf/{arxiv_id}.pdf",
            ]
        )
    return list(dict.fromkeys(aliases))


def _extract_candidate(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("An arXiv identifier is required")

    raw = unquote(value.strip())
    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        if parsed.netloc.lower() not in {
            "arxiv.org",
            "www.arxiv.org",
            "export.arxiv.org",
        }:
            raise ValueError(f"Not an arXiv URL: {value!r}")
        path = parsed.path.strip("/")
        for prefix in ("abs/", "pdf/"):
            if path.startswith(prefix):
                path = path[len(prefix) :]
                break
        raw = path

    raw = raw.split("?", 1)[0].split("#", 1)[0].strip("/")
    if raw.lower().endswith(".pdf"):
        raw = raw[:-4]
    return raw
