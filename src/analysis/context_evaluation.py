"""Corpus-level quality checks for token-budgeted agent context packages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.analysis.context_packages import (
    CONTEXT_PROFILE_BUDGETS,
    build_agent_context_package,
    package_item_keys,
)
from src.analysis.models import AgentContextPackage, AgentPaperContext

EVALUATION_PROFILES = ("brief", "standard", "deep")
_CONTENT_UNIT_FIELDS = (
    "tldr",
    "problem",
    "contributions",
    "methods",
    "results",
    "limitations",
    "implementation_ideas",
    "concepts",
    "tags",
)


def evaluate_context_packages(
    contexts: list[AgentPaperContext],
) -> dict[str, Any]:
    """Evaluate budget, evidence, determinism, and monotonicity invariants."""

    cases: list[dict[str, Any]] = []
    monotonic_papers = 0
    for context in contexts:
        previous_keys: set[str] = set()
        paper_is_monotonic = True
        for profile in EVALUATION_PROFILES:
            package = build_agent_context_package(context, profile=profile)
            repeated = build_agent_context_package(context, profile=profile)
            current_keys = package_item_keys(package)
            monotonic = previous_keys <= current_keys
            paper_is_monotonic = paper_is_monotonic and monotonic
            previous_keys = current_keys
            cases.append(
                _evaluate_case(
                    package,
                    deterministic=package == repeated,
                    monotonic_with_smaller_profile=monotonic,
                )
            )
        monotonic_papers += int(paper_is_monotonic)

    profile_summaries = {
        profile: _profile_summary(
            [case for case in cases if case["profile"] == profile]
        )
        for profile in EVALUATION_PROFILES
    }
    package_count = len(cases)
    rates = {
        "budget_compliance_rate": _rate(cases, "budget_compliant"),
        "evidence_closure_rate": _rate(cases, "evidence_closed"),
        "determinism_rate": _rate(cases, "deterministic"),
        "provenance_rate": _rate(cases, "provenance_complete"),
        "tldr_retention_rate": _rate(cases, "tldr_present"),
        "paper_monotonicity_rate": (
            monotonic_papers / len(contexts) if contexts else 0.0
        ),
    }
    all_passed = bool(contexts) and all(value == 1.0 for value in rates.values())
    return {
        "contract": "agent-context-package-evaluation",
        "schema_version": "1.0",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(contexts),
        "package_count": package_count,
        "profiles": dict(CONTEXT_PROFILE_BUDGETS),
        "rates": rates,
        "profile_summaries": profile_summaries,
        "all_passed": all_passed,
        "cases": cases,
    }


def _evaluate_case(
    package: AgentContextPackage,
    *,
    deterministic: bool,
    monotonic_with_smaller_profile: bool,
) -> dict[str, Any]:
    included_evidence = {item.evidence_id for item in package.analysis.evidence}
    referenced_evidence = _referenced_evidence(package)
    available_units = sum(
        getattr(package.budget.available, field_name)
        for field_name in _CONTENT_UNIT_FIELDS
    )
    included_units = sum(
        getattr(package.budget.included, field_name)
        for field_name in _CONTENT_UNIT_FIELDS
    )
    provenance = package.provenance
    return {
        "paper_id": package.paper.paper_id,
        "profile": package.budget.profile,
        "requested_tokens": package.budget.requested_tokens,
        "estimated_tokens": package.budget.estimated_tokens,
        "budget_utilization": (
            package.budget.estimated_tokens / package.budget.requested_tokens
        ),
        "content_retention": (
            included_units / available_units if available_units else 1.0
        ),
        "evidence_retention": (
            package.budget.included.evidence / package.budget.available.evidence
            if package.budget.available.evidence
            else 1.0
        ),
        "truncated": package.budget.truncated,
        "budget_compliant": (
            package.budget.estimated_tokens <= package.budget.requested_tokens
        ),
        "evidence_closed": referenced_evidence == included_evidence,
        "deterministic": deterministic,
        "monotonic_with_smaller_profile": monotonic_with_smaller_profile,
        "provenance_complete": all(
            (
                provenance.document_hash,
                provenance.analysis_schema_version,
                provenance.prompt_version,
                provenance.analysis_model,
                provenance.generated_at,
            )
        ),
        "tldr_present": bool(package.analysis.tldr.statement),
        "included": package.budget.included.model_dump(),
        "omitted": package.budget.omitted.model_dump(),
    }


def _referenced_evidence(package: AgentContextPackage) -> set[str]:
    items = [package.analysis.tldr]
    for field_name in (
        "implementation_ideas",
        "methods",
        "results",
        "limitations",
        "contributions",
        "problem",
    ):
        items.extend(getattr(package.analysis, field_name))
    return {evidence_id for item in items for evidence_id in item.evidence_ids}


def _profile_summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(cases)
    if not count:
        return {
            "package_count": 0,
            "mean_estimated_tokens": 0.0,
            "max_estimated_tokens": 0,
            "mean_content_retention": 0.0,
            "mean_evidence_retention": 0.0,
            "complete_package_rate": 0.0,
        }
    return {
        "package_count": count,
        "mean_estimated_tokens": sum(case["estimated_tokens"] for case in cases)
        / count,
        "max_estimated_tokens": max(case["estimated_tokens"] for case in cases),
        "mean_content_retention": sum(case["content_retention"] for case in cases)
        / count,
        "mean_evidence_retention": sum(case["evidence_retention"] for case in cases)
        / count,
        "complete_package_rate": sum(not case["truncated"] for case in cases) / count,
    }


def _rate(cases: list[dict[str, Any]], field_name: str) -> float:
    return sum(bool(case[field_name]) for case in cases) / len(cases) if cases else 0.0
