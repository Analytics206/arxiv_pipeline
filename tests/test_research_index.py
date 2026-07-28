from src.analysis.models import (
    EvidenceRef,
    ImplementationIdea,
    PaperAnalysis,
    SupportedClaim,
)
from src.retrieval.qdrant_index import build_analysis_points


def make_analysis() -> PaperAnalysis:
    evidence = EvidenceRef(
        evidence_id="ev_1",
        chunk_id="chunk_1",
        page=4,
        quote=(
            "The proxy records harness model calls and reconstructs standard "
            "reinforcement-learning samples."
        ),
        section="Method",
    )
    claim = SupportedClaim(
        statement=("A proxy converts harness interactions into standard RL samples."),
        evidence_ids=[evidence.evidence_id],
    )
    return PaperAnalysis(
        schema_version="1.0",
        prompt_version="agent-paper-v5",
        paper_id="2607.21557",
        paper_version_id="2607.21557v1",
        resource_uri="paper://arxiv/2607.21557",
        title="Harness-native RL",
        document_hash="a" * 64,
        page_count=8,
        model="qwen3.5:4b",
        tldr=claim,
        methods=[claim],
        implementation_ideas=[
            ImplementationIdea(
                title="Inference proxy",
                description="Record harness inference at the model boundary.",
                agent_use="Turn existing agent executions into training samples.",
                expected_benefit="Avoid rewriting the agent harness.",
                risks=["Not stated"],
                evidence_ids=[evidence.evidence_id],
            )
        ],
        evidence=[evidence],
    )


def test_analysis_points_are_stable_and_preserve_provenance():
    analysis = make_analysis()

    first = build_analysis_points(
        analysis,
        embedding_model="mxbai-embed-large:latest",
    )
    second = build_analysis_points(
        analysis,
        embedding_model="mxbai-embed-large:latest",
    )

    assert [point.point_id for point in first] == [point.point_id for point in second]
    assert {point.kind for point in first} == {
        "evidence",
        "claim",
        "implementation_idea",
    }
    assert all(point.paper_id == analysis.paper_id for point in first)
    assert all(point.evidence[0].page == 4 for point in first)
    assert all(point.evidence_ids == ["ev_1"] for point in first)
    assert "embedding_text" not in first[0].payload()
    idea_point = next(point for point in first if point.kind == "implementation_idea")
    assert idea_point.text == "Record harness inference at the model boundary."
    assert idea_point.text.count("Record harness inference") == 1
    assert idea_point.implementation_idea is not None
    assert idea_point.implementation_idea.agent_use == (
        "Turn existing agent executions into training samples."
    )
    assert idea_point.implementation_idea.risks == []
    assert "Not stated" not in idea_point.embedding_text


def test_index_identity_changes_with_embedding_model():
    analysis = make_analysis()

    first = build_analysis_points(
        analysis,
        embedding_model="mxbai-embed-large:latest",
    )
    second = build_analysis_points(
        analysis,
        embedding_model="qwen3-embedding:0.6b",
    )

    assert first[0].analysis_key != second[0].analysis_key
    assert first[0].point_id != second[0].point_id
