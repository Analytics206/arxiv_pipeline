"""Normalization rules for structured implementation ideas."""

from __future__ import annotations

from src.analysis.models import ImplementationIdea

_NULL_MARKERS = {
    "",
    "n/a",
    "none",
    "not applicable",
    "not provided",
    "not specified",
    "not stated",
    "unknown",
}


def normalize_implementation_idea(idea: ImplementationIdea) -> ImplementationIdea:
    """Keep absence out of persisted and embedded idea content."""

    return idea.model_copy(
        update={
            "title": idea.title.strip(),
            "description": idea.description.strip(),
            "agent_use": idea.agent_use.strip(),
            "expected_benefit": idea.expected_benefit.strip(),
            "risks": clean_optional_strings(idea.risks)[:10],
            "evidence_ids": list(dict.fromkeys(idea.evidence_ids))[:12],
        }
    )


def canonical_idea_text(idea: ImplementationIdea) -> str:
    """Return one non-repeating text representation for retrieval."""

    normalized = normalize_implementation_idea(idea)
    for candidate in (
        normalized.description,
        normalized.agent_use,
        normalized.title,
    ):
        if candidate:
            return candidate
    return normalized.title


def clean_optional_strings(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw_item in items:
        item = raw_item.strip()
        normalized = item.casefold().rstrip(".")
        if normalized in _NULL_MARKERS:
            continue
        cleaned.append(item)
    return list(dict.fromkeys(cleaned))
