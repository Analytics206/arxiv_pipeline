"""Evaluate dense, hybrid, and diversity-reranked retrieval strategies."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.analysis.models import PaperAnalysis
from src.retrieval.benchmark import validate_suite_against_analyses
from src.retrieval.evaluation import (
    RetrievalEvaluationReport,
    RetrievalEvaluationSuite,
    evaluate_retrieval,
)
from src.retrieval.factory import create_research_index
from src.retrieval.models import RetrievalMode
from src.retrieval.qdrant_index import DENSE_VECTOR_NAME


class StrategyBenchmarkModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetrievalStrategy(StrategyBenchmarkModel):
    strategy_id: str
    retrieval_mode: RetrievalMode
    candidate_multiplier: int = Field(default=4, ge=1, le=25)
    candidate_minimum: int = Field(default=50, ge=1, le=200)
    dense_weight: float = Field(default=1.0, gt=0)
    sparse_weight: float = Field(default=1.0, gt=0)
    rrf_k: int = Field(default=60, ge=1)
    paper_diversity_penalty: float = Field(default=0.0, ge=0, le=1)
    note: str | None = None


class RetrievalStrategyMatrix(StrategyBenchmarkModel):
    benchmark_id: str
    description: str
    embedding_model: str
    baseline_collection: str
    hybrid_collection: str
    hybrid_index_schema_version: str = "2.0"
    selected_strategy_id: str
    strategies: list[RetrievalStrategy] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_selected_strategy(self) -> "RetrievalStrategyMatrix":
        selected = [
            strategy
            for strategy in self.strategies
            if strategy.strategy_id == self.selected_strategy_id
        ]
        if len(selected) != 1:
            raise ValueError("selected_strategy_id must match exactly one strategy")
        if selected[0].retrieval_mode != "hybrid":
            raise ValueError("selected strategy must use hybrid retrieval")
        return self


class RetrievalStrategyResult(StrategyBenchmarkModel):
    strategy_id: str
    retrieval_mode: RetrievalMode
    candidate_multiplier: int
    candidate_minimum: int
    dense_weight: float
    sparse_weight: float
    rrf_k: int
    paper_diversity_penalty: float
    evaluation: RetrievalEvaluationReport


class RetrievalStrategyBenchmarkReport(StrategyBenchmarkModel):
    contract: str = "research-retrieval-strategy-benchmark"
    benchmark_id: str
    suite_id: str
    embedding_model: str
    baseline_collection: str
    hybrid_collection: str
    selected_strategy_id: str
    analysis_count: int
    point_count: int
    vector_size: int | None
    index_duration_ms: float
    index_statuses: dict[str, int]
    results: list[RetrievalStrategyResult]


def load_strategy_matrix(path: str | Path) -> RetrievalStrategyMatrix:
    return RetrievalStrategyMatrix.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def save_strategy_report(
    report: RetrievalStrategyBenchmarkReport,
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def run_strategy_benchmark(
    *,
    config: dict[str, Any],
    suite: RetrievalEvaluationSuite,
    matrix: RetrievalStrategyMatrix,
    analyses: list[PaperAnalysis],
    ollama_url: str,
    qdrant_url: str,
    skip_index: bool = False,
) -> RetrievalStrategyBenchmarkReport:
    validate_suite_against_analyses(suite, analyses)
    hybrid_strategies = [
        strategy
        for strategy in matrix.strategies
        if strategy.retrieval_mode == "hybrid"
    ]
    if not hybrid_strategies:
        raise ValueError("Strategy matrix requires at least one hybrid strategy")

    index_results: list[dict[str, Any]] = []
    index_duration_ms = 0.0
    builder = _create_strategy_index(
        config=config,
        matrix=matrix,
        strategy=hybrid_strategies[0],
        ollama_url=ollama_url,
        qdrant_url=qdrant_url,
    )
    point_count = 0
    vector_size: int | None = None
    if not skip_index:
        started = perf_counter()
        index_results = [builder.index_analysis(analysis) for analysis in analyses]
        index_duration_ms = (perf_counter() - started) * 1000
        point_count = sum(int(result.get("points", 0)) for result in index_results)
        vector_sizes = {
            int(result["vector_size"])
            for result in index_results
            if result.get("vector_size") is not None
        }
        vector_size = next(iter(vector_sizes)) if len(vector_sizes) == 1 else None
    else:
        point_count = int(
            builder.client.count(
                collection_name=matrix.hybrid_collection,
                exact=True,
            ).count
        )
        collection = builder.client.get_collection(matrix.hybrid_collection)
        vector_size = int(collection.config.params.vectors[DENSE_VECTOR_NAME].size)

    results: list[RetrievalStrategyResult] = []
    for strategy in matrix.strategies:
        index = _create_strategy_index(
            config=config,
            matrix=matrix,
            strategy=strategy,
            ollama_url=ollama_url,
            qdrant_url=qdrant_url,
        )
        results.append(
            RetrievalStrategyResult(
                strategy_id=strategy.strategy_id,
                retrieval_mode=strategy.retrieval_mode,
                candidate_multiplier=strategy.candidate_multiplier,
                candidate_minimum=strategy.candidate_minimum,
                dense_weight=strategy.dense_weight,
                sparse_weight=strategy.sparse_weight,
                rrf_k=strategy.rrf_k,
                paper_diversity_penalty=strategy.paper_diversity_penalty,
                evaluation=evaluate_retrieval(index, suite),
            )
        )

    return RetrievalStrategyBenchmarkReport(
        benchmark_id=matrix.benchmark_id,
        suite_id=suite.suite_id,
        embedding_model=matrix.embedding_model,
        baseline_collection=matrix.baseline_collection,
        hybrid_collection=matrix.hybrid_collection,
        selected_strategy_id=matrix.selected_strategy_id,
        analysis_count=len(analyses),
        point_count=point_count,
        vector_size=vector_size,
        index_duration_ms=round(index_duration_ms, 3),
        index_statuses=(
            dict(
                Counter(
                    str(result.get("status", "unknown")) for result in index_results
                )
            )
            if index_results
            else {"reused": len(analyses)}
        ),
        results=results,
    )


def _create_strategy_index(
    *,
    config: dict[str, Any],
    matrix: RetrievalStrategyMatrix,
    strategy: RetrievalStrategy,
    ollama_url: str,
    qdrant_url: str,
):
    is_hybrid = strategy.retrieval_mode == "hybrid"
    return create_research_index(
        config,
        qdrant_url=qdrant_url,
        ollama_url=ollama_url,
        embedding_model=matrix.embedding_model,
        collection_name=(
            matrix.hybrid_collection if is_hybrid else matrix.baseline_collection
        ),
        retrieval_mode=strategy.retrieval_mode,
        hybrid_candidate_multiplier=strategy.candidate_multiplier,
        hybrid_candidate_minimum=strategy.candidate_minimum,
        rrf_dense_weight=strategy.dense_weight,
        rrf_sparse_weight=strategy.sparse_weight,
        rrf_k=strategy.rrf_k,
        paper_diversity_penalty=strategy.paper_diversity_penalty,
        index_schema_version=(
            matrix.hybrid_index_schema_version if is_hybrid else None
        ),
    )
