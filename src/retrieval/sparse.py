"""Dependency-free sparse lexical features for Qdrant hybrid retrieval."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass

SPARSE_ENCODER_VERSION = "hashed-tfidf-v1"
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[._+-][a-z0-9]+)*")
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "both",
        "by",
        "can",
        "does",
        "for",
        "from",
        "how",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "used",
        "using",
        "what",
        "when",
        "where",
        "which",
        "with",
    }
)


@dataclass(frozen=True)
class SparseTextVector:
    indices: list[int]
    values: list[float]


def encode_sparse_text(text: str) -> SparseTextVector:
    """Create stable hashed term-frequency features.

    Qdrant applies collection-level inverse document frequency at query time.
    Hashing keeps token identities stable for incremental indexing without a
    separately persisted vocabulary.
    """

    counts = Counter(_tokens(text))
    by_index: dict[int, float] = {}
    for token, count in counts.items():
        index = _token_index(token)
        by_index[index] = by_index.get(index, 0.0) + 1.0 + math.log(count)
    ordered = sorted(by_index.items())
    return SparseTextVector(
        indices=[index for index, _ in ordered],
        values=[round(value, 6) for _, value in ordered],
    )


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_PATTERN.findall(text.lower())
        if token not in _STOPWORDS and len(token) > 1
    ]


def _token_index(token: str) -> int:
    digest = hashlib.blake2s(
        token.encode("utf-8"),
        digest_size=4,
        person=b"arxivlex",
    ).digest()
    return int.from_bytes(digest, "big", signed=False)
