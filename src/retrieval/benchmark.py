"""Reproducible embedding-model benchmarks over canonical research analyses."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.analysis.models import PaperAnalysis
from src.analysis.identity import normalize_arxiv_id
from src.retrieval.evaluation import (
    RetrievalEvaluationReport,
    RetrievalEvaluationSuite,
    evaluate_retrieval,
)
from src.retrieval.factory import create_research_index


class BenchmarkModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmbeddingBenchmarkTarget(BenchmarkModel):
    embedding_model: str
    collection_name: str
    query_prefix: str = (
        "Represent this sentence for searching relevant passages: "
    )
    document_prefix: str = ""
    note: str | None = None


class EmbeddingBenchmarkMatrix(BenchmarkModel):
    benchmark_id: str
    description: str
    targets: list[EmbeddingBenchmarkTarget] = Field(min_length=1)


class EmbeddingBenchmarkResult(BenchmarkModel):
    embedding_model: str
    collection_name: str
    status: str
    model_size_bytes: int | None = None
    analysis_count: int = 0
    point_count: int = 0
    vector_size: int | None = None
    index_duration_ms: float | None = None
    index_statuses: dict[str, int] = Field(default_factory=dict)
    evaluation: RetrievalEvaluationReport | None = None
    error: str | None = None


class EmbeddingBenchmarkReport(BenchmarkModel):
    contract: str = "research-embedding-benchmark"
    benchmark_id: str
    suite_id: str
    available_models: list[str]
    analysis_count: int
    results: list[EmbeddingBenchmarkResult]


class EvaluationSuiteValidationError(ValueError):
    """Raised when reviewed judgments no longer match canonical analyses."""


def load_benchmark_matrix(path: str | Path) -> EmbeddingBenchmarkMatrix:
    return EmbeddingBenchmarkMatrix.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def save_benchmark_report(
    report: EmbeddingBenchmarkReport,
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def load_benchmark_report(path: str | Path) -> EmbeddingBenchmarkReport:
    return EmbeddingBenchmarkReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def merge_benchmark_reports(
    existing: EmbeddingBenchmarkReport,
    update: EmbeddingBenchmarkReport,
) -> EmbeddingBenchmarkReport:
    """Replace matching model results while retaining earlier matrix results."""

    if (
        existing.benchmark_id != update.benchmark_id
        or existing.suite_id != update.suite_id
    ):
        raise ValueError("Cannot merge reports from different benchmarks or suites")
    results = {
        result.embedding_model: result
        for result in existing.results
    }
    results.update(
        {
            result.embedding_model: result
            for result in update.results
        }
    )
    return EmbeddingBenchmarkReport(
        benchmark_id=update.benchmark_id,
        suite_id=update.suite_id,
        available_models=sorted(
            set(existing.available_models).union(update.available_models)
        ),
        analysis_count=update.analysis_count,
        results=list(results.values()),
    )


def ollama_model_inventory(ollama_url: str) -> dict[str, int]:
    """Return installed Ollama model names and their stored byte sizes."""

    from ollama import Client

    response = Client(host=ollama_url, timeout=60).list()
    models = response["models"] if isinstance(response, dict) else response.models
    inventory: dict[str, int] = {}
    for model in models:
        if isinstance(model, dict):
            name = model.get("model") or model.get("name")
            size = model.get("size")
        else:
            name = getattr(model, "model", None) or getattr(model, "name", None)
            size = getattr(model, "size", None)
        if name:
            inventory[str(name)] = int(size or 0)
    return inventory


def validate_suite_against_analyses(
    suite: RetrievalEvaluationSuite,
    analyses: list[PaperAnalysis],
) -> None:
    """Reject stale document hashes, unknown evidence, and wrong paper filters."""

    by_paper = {analysis.paper_id: analysis for analysis in analyses}
    evidence_owner = {
        evidence.evidence_id: analysis.paper_id
        for analysis in analyses
        for evidence in analysis.evidence
    }
    errors: list[str] = []
    for paper_id, expected_hash in suite.document_hashes.items():
        base_id = normalize_arxiv_id(paper_id).base_id
        analysis = by_paper.get(base_id)
        if analysis is None:
            errors.append(f"{base_id}: canonical analysis is missing")
        elif analysis.document_hash != expected_hash:
            errors.append(
                f"{base_id}: expected document {expected_hash}, "
                f"found {analysis.document_hash}"
            )

    for case in suite.cases:
        for group in case.relevance_groups:
            for evidence_id in group:
                owner = evidence_owner.get(evidence_id)
                if owner is None:
                    errors.append(f"{case.case_id}: unknown evidence {evidence_id}")
                elif case.paper_id:
                    expected_owner = normalize_arxiv_id(case.paper_id).base_id
                    if owner != expected_owner:
                        errors.append(
                            f"{case.case_id}: evidence {evidence_id} belongs "
                            f"to {owner}, not filter {expected_owner}"
                        )
    if errors:
        raise EvaluationSuiteValidationError(
            "Evaluation suite does not match canonical analyses:\n- "
            + "\n- ".join(errors)
        )


def run_embedding_benchmark(
    *,
    config: dict[str, Any],
    suite: RetrievalEvaluationSuite,
    matrix: EmbeddingBenchmarkMatrix,
    analyses: list[PaperAnalysis],
    ollama_url: str,
    qdrant_url: str,
    selected_models: set[str] | None = None,
    skip_index: bool = False,
) -> EmbeddingBenchmarkReport:
    """Index/evaluate each candidate while preserving per-model isolation."""

    validate_suite_against_analyses(suite, analyses)
    inventory = ollama_model_inventory(ollama_url)
    results: list[EmbeddingBenchmarkResult] = []
    for target in matrix.targets:
        if selected_models and target.embedding_model not in selected_models:
            continue
        if target.embedding_model not in inventory:
            results.append(
                EmbeddingBenchmarkResult(
                    embedding_model=target.embedding_model,
                    collection_name=target.collection_name,
                    status="unavailable",
                    error="Model is not installed in the shared Ollama service",
                )
            )
            continue

        try:
            index = create_research_index(
                config,
                qdrant_url=qdrant_url,
                ollama_url=ollama_url,
                embedding_model=target.embedding_model,
                collection_name=target.collection_name,
                query_prefix=target.query_prefix,
                document_prefix=target.document_prefix,
            )
            index_results: list[dict[str, Any]] = []
            index_duration_ms: float | None = None
            if not skip_index:
                started = perf_counter()
                index_results = [
                    index.index_analysis(analysis) for analysis in analyses
                ]
                index_duration_ms = (perf_counter() - started) * 1000

            evaluation = evaluate_retrieval(index, suite)
            vector_sizes = {
                int(result["vector_size"])
                for result in index_results
                if result.get("vector_size") is not None
            }
            results.append(
                EmbeddingBenchmarkResult(
                    embedding_model=target.embedding_model,
                    collection_name=target.collection_name,
                    status="complete",
                    model_size_bytes=inventory[target.embedding_model],
                    analysis_count=len(analyses),
                    point_count=sum(
                        int(result.get("points", 0)) for result in index_results
                    ),
                    vector_size=(
                        next(iter(vector_sizes)) if len(vector_sizes) == 1 else None
                    ),
                    index_duration_ms=(
                        round(index_duration_ms, 3)
                        if index_duration_ms is not None
                        else None
                    ),
                    index_statuses=dict(
                        Counter(
                            str(result.get("status", "unknown"))
                            for result in index_results
                        )
                    ),
                    evaluation=evaluation,
                )
            )
        except Exception as exc:
            results.append(
                EmbeddingBenchmarkResult(
                    embedding_model=target.embedding_model,
                    collection_name=target.collection_name,
                    status="failed",
                    model_size_bytes=inventory.get(target.embedding_model),
                    analysis_count=len(analyses),
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    return EmbeddingBenchmarkReport(
        benchmark_id=matrix.benchmark_id,
        suite_id=suite.suite_id,
        available_models=sorted(inventory),
        analysis_count=len(analyses),
        results=results,
    )
