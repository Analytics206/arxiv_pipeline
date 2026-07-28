"""Deterministic, evidence-closed context packages for external agents."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from typing import Literal

from src.analysis.models import (
    AgentContextPackage,
    AgentPaperContext,
    BudgetedPaperAnalysis,
    ContextContentCounts,
    ContextPackageBudget,
    ContextPackagePaper,
    ContextPackageProvenance,
    EvidenceRef,
    ImplementationIdea,
    SupportedClaim,
)

ContextProfile = Literal["brief", "standard", "deep"]

CONTEXT_PROFILE_BUDGETS: dict[ContextProfile, int] = {
    "brief": 1500,
    "standard": 4000,
    "deep": 8000,
}
CONTEXT_ESTIMATOR = "utf8-bytes-div-4-v1"
CONTEXT_SELECTION_POLICY = "coding-agent-v1"

_CLAIM_FIELDS = (
    "methods",
    "results",
    "limitations",
    "contributions",
    "problem",
)
_ALL_CONTENT_FIELDS = (
    "tldr",
    "problem",
    "contributions",
    "methods",
    "results",
    "limitations",
    "implementation_ideas",
    "concepts",
    "tags",
    "evidence",
)


class ContextBudgetTooSmallError(ValueError):
    """Raised when the required TLDR and its evidence exceed the budget."""

    def __init__(self, requested_tokens: int, minimum_required_tokens: int):
        self.requested_tokens = requested_tokens
        self.minimum_required_tokens = minimum_required_tokens
        super().__init__(
            "The token budget cannot hold the required TLDR, its verified "
            f"evidence, and provenance; requested {requested_tokens}, "
            f"minimum {minimum_required_tokens} estimated tokens."
        )


def build_agent_context_package(
    context: AgentPaperContext,
    *,
    profile: ContextProfile = "standard",
    token_budget: int | None = None,
) -> AgentContextPackage:
    """Build an implementation-first package without dangling evidence IDs.

    Profile names are reproducible budget aliases. An explicit budget uses the
    same coding-agent selection policy and reports the response profile as
    ``custom``.
    """

    context = _trusted_context(context)
    if profile not in CONTEXT_PROFILE_BUDGETS:
        raise ValueError(f"Unknown context profile: {profile}")
    if token_budget is not None and token_budget < 1:
        raise ValueError("token_budget must be greater than zero")

    requested_tokens = (
        token_budget if token_budget is not None else CONTEXT_PROFILE_BUDGETS[profile]
    )
    response_profile = "custom" if token_budget is not None else profile
    budget_source = "explicit" if token_budget is not None else "profile"
    analysis = context.analysis
    evidence_by_id = {item.evidence_id: item for item in analysis.evidence}

    selected: dict[str, list] = {
        "implementation_ideas": [],
        **{field_name: [] for field_name in _CLAIM_FIELDS},
        "concepts": [],
        "tags": [],
    }
    selected_evidence_ids = set(analysis.tldr.evidence_ids)
    all_referenced_evidence_ids = selected_evidence_ids | {
        evidence_id
        for _, item in _selection_candidates(context)
        for evidence_id in _item_evidence_ids(item)
    }
    _require_evidence(all_referenced_evidence_ids, evidence_by_id)

    available = _content_counts(
        context,
        evidence_count=len(all_referenced_evidence_ids),
    )
    package = _make_package(
        context=context,
        selected=selected,
        evidence_ids=selected_evidence_ids,
        available=available,
        requested_tokens=requested_tokens,
        profile=response_profile,
        budget_source=budget_source,
    )
    if package.budget.estimated_tokens > requested_tokens:
        minimum_required_tokens = package.budget.estimated_tokens
        for _ in range(4):
            minimum_package = _make_package(
                context=context,
                selected=selected,
                evidence_ids=selected_evidence_ids,
                available=available,
                requested_tokens=minimum_required_tokens,
                profile=response_profile,
                budget_source=budget_source,
            )
            if minimum_package.budget.estimated_tokens == minimum_required_tokens:
                break
            minimum_required_tokens = minimum_package.budget.estimated_tokens
        raise ContextBudgetTooSmallError(
            requested_tokens=requested_tokens,
            minimum_required_tokens=minimum_required_tokens,
        )

    for field_name, item in _selection_candidates(context):
        candidate_evidence_ids = selected_evidence_ids | set(_item_evidence_ids(item))
        _require_evidence(candidate_evidence_ids, evidence_by_id)
        selected[field_name].append(item)
        candidate = _make_package(
            context=context,
            selected=selected,
            evidence_ids=candidate_evidence_ids,
            available=available,
            requested_tokens=requested_tokens,
            profile=response_profile,
            budget_source=budget_source,
        )
        if candidate.budget.estimated_tokens > requested_tokens:
            selected[field_name].pop()
            break
        package = candidate
        selected_evidence_ids = candidate_evidence_ids

    return package


def _trusted_context(context: AgentPaperContext) -> AgentPaperContext:
    """Exclude incomplete evidence and any derived item left unsupported."""

    source = context.analysis
    evidence_by_id = {item.evidence_id: item for item in source.evidence}
    referenced_ids = set(source.tldr.evidence_ids)
    for field_name in (*_CLAIM_FIELDS, "implementation_ideas"):
        referenced_ids.update(
            evidence_id
            for item in getattr(source, field_name)
            for evidence_id in item.evidence_ids
        )
    _require_evidence(referenced_ids, evidence_by_id)
    trusted_ids = {item.evidence_id for item in source.evidence if not item.truncated}

    def clean_item(item: SupportedClaim | ImplementationIdea):
        evidence_ids = [
            evidence_id
            for evidence_id in item.evidence_ids
            if evidence_id in trusted_ids
        ]
        if not evidence_ids:
            return None
        return item.model_copy(update={"evidence_ids": evidence_ids})

    tldr = clean_item(source.tldr)
    if tldr is None:
        raise ValueError("Paper TLDR has no complete verification span")
    updates: dict[str, object] = {
        "tldr": tldr,
        "evidence": [
            item for item in source.evidence if item.evidence_id in trusted_ids
        ],
        "implementation_ideas": [
            cleaned
            for item in source.implementation_ideas
            if (cleaned := clean_item(item)) is not None
        ],
    }
    for field_name in _CLAIM_FIELDS:
        updates[field_name] = [
            cleaned
            for item in getattr(source, field_name)
            if (cleaned := clean_item(item)) is not None
        ]
    return context.model_copy(update={"analysis": source.model_copy(update=updates)})


def estimate_context_tokens(value: AgentContextPackage | dict) -> int:
    """Estimate JSON tokens without binding the service to one model tokenizer."""

    document = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    serialized = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return max(1, math.ceil(len(serialized.encode("utf-8")) / 4))


def package_item_keys(package: AgentContextPackage) -> set[str]:
    """Return stable selected-item keys for monotonicity evaluation."""

    keys: set[str] = {"tldr:" + package.analysis.tldr.statement}
    for field_name in _CLAIM_FIELDS:
        keys.update(
            f"{field_name}:{item.statement}"
            for item in getattr(package.analysis, field_name)
        )
    keys.update(
        f"implementation_ideas:{item.title}:{item.description}"
        for item in package.analysis.implementation_ideas
    )
    keys.update(f"concepts:{item}" for item in package.analysis.concepts)
    keys.update(f"tags:{item}" for item in package.analysis.tags)
    return keys


def _selection_candidates(
    context: AgentPaperContext,
) -> Iterable[tuple[str, SupportedClaim | ImplementationIdea | str]]:
    analysis = context.analysis
    for item in analysis.implementation_ideas:
        yield "implementation_ideas", item
    for field_name in _CLAIM_FIELDS:
        for item in getattr(analysis, field_name):
            yield field_name, item
    for item in analysis.concepts:
        yield "concepts", item
    for item in analysis.tags:
        yield "tags", item


def _item_evidence_ids(
    item: SupportedClaim | ImplementationIdea | str,
) -> list[str]:
    return item.evidence_ids if not isinstance(item, str) else []


def _require_evidence(
    evidence_ids: set[str],
    evidence_by_id: dict[str, EvidenceRef],
) -> None:
    missing = sorted(evidence_ids - evidence_by_id.keys())
    if missing:
        raise ValueError(
            "Analysis references evidence IDs that are not present: "
            + ", ".join(missing)
        )


def _make_package(
    *,
    context: AgentPaperContext,
    selected: dict[str, list],
    evidence_ids: set[str],
    available: ContextContentCounts,
    requested_tokens: int,
    profile: Literal["brief", "standard", "deep", "custom"],
    budget_source: Literal["profile", "explicit"],
) -> AgentContextPackage:
    source = context.analysis
    evidence = [item for item in source.evidence if item.evidence_id in evidence_ids]
    included = ContextContentCounts(
        tldr=1,
        evidence=len(evidence),
        **{field_name: len(selected[field_name]) for field_name in selected},
    )
    omitted = ContextContentCounts(
        **{
            field_name: getattr(available, field_name) - getattr(included, field_name)
            for field_name in _ALL_CONTENT_FIELDS
        }
    )
    package = AgentContextPackage(
        paper=_paper_identity(context),
        provenance=ContextPackageProvenance(
            document_hash=source.document_hash,
            page_count=source.page_count,
            analysis_schema_version=source.schema_version,
            prompt_version=source.prompt_version,
            analysis_model=source.model,
            generated_at=source.generated_at,
        ),
        budget=ContextPackageBudget(
            requested_tokens=requested_tokens,
            estimated_tokens=1,
            profile=profile,
            budget_source=budget_source,
            truncated=any(
                getattr(omitted, field_name) > 0 for field_name in _ALL_CONTENT_FIELDS
            ),
            available=available,
            included=included,
            omitted=omitted,
        ),
        analysis=BudgetedPaperAnalysis(
            tldr=source.tldr,
            evidence=evidence,
            **selected,
        ),
    )
    return _finalize_estimate(package)


def _paper_identity(context: AgentPaperContext) -> ContextPackagePaper:
    source = context.analysis
    raw_paper = context.paper
    return ContextPackagePaper(
        paper_id=source.paper_id,
        paper_version_id=source.paper_version_id,
        resource_uri=source.resource_uri,
        title=source.title,
        arxiv_url=str(
            raw_paper.get("arxiv_url")
            or f"https://arxiv.org/abs/{source.paper_version_id}"
        ),
        pdf_url=str(
            raw_paper.get("pdf_url")
            or f"https://arxiv.org/pdf/{source.paper_version_id}"
        ),
    )


def _content_counts(
    context: AgentPaperContext,
    *,
    evidence_count: int,
) -> ContextContentCounts:
    analysis = context.analysis
    return ContextContentCounts(
        tldr=1,
        problem=len(analysis.problem),
        contributions=len(analysis.contributions),
        methods=len(analysis.methods),
        results=len(analysis.results),
        limitations=len(analysis.limitations),
        implementation_ideas=len(analysis.implementation_ideas),
        concepts=len(analysis.concepts),
        tags=len(analysis.tags),
        evidence=evidence_count,
    )


def _finalize_estimate(package: AgentContextPackage) -> AgentContextPackage:
    for _ in range(4):
        estimated_tokens = estimate_context_tokens(package)
        if estimated_tokens == package.budget.estimated_tokens:
            break
        package.budget.estimated_tokens = estimated_tokens
    return package
