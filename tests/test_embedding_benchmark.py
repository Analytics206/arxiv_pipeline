import pytest

from src.analysis.models import EvidenceRef, PaperAnalysis, SupportedClaim
from src.retrieval.benchmark import (
    EmbeddingBenchmarkReport,
    EmbeddingBenchmarkResult,
    EvaluationSuiteValidationError,
    merge_benchmark_reports,
    validate_suite_against_analyses,
)
from src.retrieval.evaluation import (
    RetrievalEvaluationCase,
    RetrievalEvaluationSuite,
)


def make_analysis() -> PaperAnalysis:
    evidence = EvidenceRef(
        evidence_id="ev_valid",
        chunk_id="chunk-1",
        page=1,
        quote="The workflow validates every generated target.",
    )
    claim = SupportedClaim(
        statement="The workflow validates every generated target.",
        evidence_ids=[evidence.evidence_id],
    )
    return PaperAnalysis(
        schema_version="1.0",
        prompt_version="v1",
        paper_id="2504.18538",
        paper_version_id="2504.18538v1",
        resource_uri="paper://arxiv/2504.18538",
        title="Validated agents",
        document_hash="a" * 64,
        page_count=1,
        model="fake-model",
        tldr=claim,
        evidence=[evidence],
    )


def test_suite_validation_accepts_matching_hash_and_evidence():
    analysis = make_analysis()
    suite = RetrievalEvaluationSuite(
        suite_id="valid",
        description="Valid suite",
        document_hashes={analysis.paper_id: analysis.document_hash},
        cases=[
            RetrievalEvaluationCase(
                case_id="valid-case",
                query="How is work checked?",
                paper_id=analysis.paper_id,
                expected_evidence_ids=["ev_valid"],
            )
        ],
    )

    validate_suite_against_analyses(suite, [analysis])


def test_suite_validation_rejects_stale_ground_truth():
    analysis = make_analysis()
    suite = RetrievalEvaluationSuite(
        suite_id="stale",
        description="Stale suite",
        document_hashes={analysis.paper_id: "b" * 64},
        cases=[
            RetrievalEvaluationCase(
                case_id="stale-case",
                query="How is work checked?",
                paper_id=analysis.paper_id,
                expected_evidence_ids=["ev_missing"],
            )
        ],
    )

    with pytest.raises(EvaluationSuiteValidationError) as exc:
        validate_suite_against_analyses(suite, [analysis])

    assert "expected document" in str(exc.value)
    assert "unknown evidence ev_missing" in str(exc.value)


def test_benchmark_report_merge_replaces_only_selected_model():
    first = EmbeddingBenchmarkReport(
        benchmark_id="benchmark",
        suite_id="suite",
        available_models=["model-a", "model-b"],
        analysis_count=1,
        results=[
            EmbeddingBenchmarkResult(
                embedding_model="model-a",
                collection_name="a",
                status="complete",
            )
        ],
    )
    update = EmbeddingBenchmarkReport(
        benchmark_id="benchmark",
        suite_id="suite",
        available_models=["model-a", "model-b"],
        analysis_count=1,
        results=[
            EmbeddingBenchmarkResult(
                embedding_model="model-b",
                collection_name="b",
                status="complete",
            )
        ],
    )

    merged = merge_benchmark_reports(first, update)

    assert [result.embedding_model for result in merged.results] == [
        "model-a",
        "model-b",
    ]
