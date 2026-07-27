from datetime import datetime, timezone

import pytest

from src.analysis.context_packages import (
    ContextBudgetTooSmallError,
    build_agent_context_package,
    estimate_context_tokens,
    package_item_keys,
)
from src.analysis.context_evaluation import evaluate_context_packages
from src.analysis.models import (
    AgentPaperContext,
    EvidenceRef,
    ImplementationIdea,
    PaperAnalysis,
    SupportedClaim,
)


def make_context() -> AgentPaperContext:
    evidence = [
        EvidenceRef(
            evidence_id=f"ev-{index}",
            chunk_id=f"chunk-{index}",
            page=index,
            quote=(
                f"Verified source passage {index} explains the evaluated "
                "agent workflow and its measured behavior."
            ),
            section="Evaluation",
        )
        for index in range(1, 13)
    ]

    def claim(index: int, kind: str) -> SupportedClaim:
        return SupportedClaim(
            statement=(
                f"{kind.title()} claim {index} describes a concrete mechanism "
                "and the conditions under which the reported result applies."
            ),
            evidence_ids=[f"ev-{index}"],
        )

    analysis = PaperAnalysis(
        schema_version="1.0",
        prompt_version="agent-paper-v5",
        paper_id="2607.00001",
        paper_version_id="2607.00001v1",
        resource_uri="paper://arxiv/2607.00001",
        title="Evaluated Agent Workflows",
        document_hash="a" * 64,
        page_count=12,
        model="qwen3.5:4b",
        generated_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        tldr=claim(1, "summary"),
        problem=[claim(10, "problem")],
        contributions=[claim(9, "contribution")],
        methods=[claim(5, "method"), claim(6, "method")],
        results=[claim(7, "result")],
        limitations=[claim(8, "limitation")],
        implementation_ideas=[
            ImplementationIdea(
                title=f"Agent harness idea {index}",
                description=(
                    "Add the paper's mechanism behind a configurable harness "
                    "boundary and capture comparable evaluation telemetry."
                ),
                agent_use=(
                    "A coding agent can inspect failures, select the mechanism, "
                    "and retain the evidence URI with its implementation plan."
                ),
                expected_benefit="More reproducible and evidence-aware changes.",
                risks=["The paper's assumptions may not match the target project."],
                evidence_ids=[f"ev-{index}"],
            )
            for index in range(2, 5)
        ],
        concepts=["agent harness", "workflow evaluation", "tool feedback"],
        tags=["coding-agents", "evaluation"],
        evidence=evidence,
    )
    return AgentPaperContext(
        resource_uri=analysis.resource_uri,
        paper={
            "arxiv_url": "https://arxiv.org/abs/2607.00001v1",
            "pdf_url": "https://arxiv.org/pdf/2607.00001v1",
            "summary": "This long abstract must not enter compact packages.",
            "local_pdf_path": "data/pdfs/cs.AI/2607.00001v1.pdf",
        },
        analysis=analysis,
    )


def referenced_evidence_ids(package) -> set[str]:
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


def test_package_respects_budget_and_closes_evidence_references():
    package = build_agent_context_package(make_context(), profile="standard")
    included_evidence = {item.evidence_id for item in package.analysis.evidence}

    assert package.contract == "agent-context-package"
    assert package.budget.requested_tokens == 4000
    assert package.budget.estimated_tokens <= package.budget.requested_tokens
    assert package.budget.estimated_tokens == estimate_context_tokens(package)
    assert referenced_evidence_ids(package) == included_evidence
    assert package.paper.model_dump().keys() == {
        "paper_id",
        "paper_version_id",
        "resource_uri",
        "title",
        "arxiv_url",
        "pdf_url",
    }


def test_package_selection_is_deterministic_and_monotonic_across_budgets():
    context = make_context()
    with pytest.raises(ContextBudgetTooSmallError) as caught:
        build_agent_context_package(context, token_budget=1)

    minimum = caught.value.minimum_required_tokens
    small = build_agent_context_package(context, token_budget=minimum)
    medium = build_agent_context_package(context, token_budget=minimum + 1000)
    large = build_agent_context_package(context, token_budget=32000)
    repeated = build_agent_context_package(context, token_budget=minimum + 1000)

    assert package_item_keys(small) <= package_item_keys(medium)
    assert package_item_keys(medium) <= package_item_keys(large)
    assert medium == repeated
    assert small.budget.included.implementation_ideas == 0
    assert large.budget.truncated is False


def test_package_counts_disclose_every_omission():
    package = build_agent_context_package(make_context(), profile="brief")

    for field_name in type(package.budget.available).model_fields:
        assert getattr(package.budget.available, field_name) == (
            getattr(package.budget.included, field_name)
            + getattr(package.budget.omitted, field_name)
        )
    assert package.budget.truncated == any(
        value > 0 for value in package.budget.omitted.model_dump().values()
    )


def test_package_rejects_dangling_evidence_in_canonical_analysis():
    context = make_context()
    context.analysis.tldr.evidence_ids = ["missing-evidence"]

    with pytest.raises(ValueError, match="missing-evidence"):
        build_agent_context_package(context)


def test_context_package_evaluation_covers_all_profiles():
    report = evaluate_context_packages([make_context()])

    assert report["paper_count"] == 1
    assert report["package_count"] == 3
    assert report["all_passed"] is True
    assert report["rates"] == {
        "budget_compliance_rate": 1.0,
        "evidence_closure_rate": 1.0,
        "determinism_rate": 1.0,
        "provenance_rate": 1.0,
        "tldr_retention_rate": 1.0,
        "paper_monotonicity_rate": 1.0,
    }
