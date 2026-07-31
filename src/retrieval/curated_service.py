"""Paper-centric fusion and deterministic curation across both Qdrant indexes."""

from __future__ import annotations

import json
import logging
import math
import time
import uuid
from collections import defaultdict
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, Literal, Protocol, TypeVar

from src.analysis.identity import normalize_arxiv_id
from src.retrieval.curated_models import (
    CuratedPaperResult,
    CuratedResearchSearchResponse,
    CuratedSearchBudget,
    CuratedSearchCoverage,
    CuratedSourceCoverage,
    PaperSearchMetadata,
    PaperSourceScore,
)
from src.retrieval.discovery_models import DiscoverySearchHit, DiscoverySearchResponse
from src.retrieval.models import (
    ResearchPointKind,
    ResearchSearchHit,
    ResearchSearchResponse,
)
from src.retrieval.search_history import SearchHistoryRecorder

logger = logging.getLogger(__name__)
SourceResponse = TypeVar(
    "SourceResponse",
    ResearchSearchResponse,
    DiscoverySearchResponse,
)


class ResearchIndex(Protocol):
    collection_name: str
    embedder: Any

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        paper_id: str | None = None,
        kinds: Sequence[ResearchPointKind] | None = None,
        min_relevance: float | None = None,
        query_vector: Sequence[float] | None = None,
    ) -> ResearchSearchResponse: ...


class DiscoveryIndex(Protocol):
    collection_name: str
    embedder: Any

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        paper_id: str | None = None,
        categories: Sequence[str] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        min_relevance: float | None = None,
        query_vector: Sequence[float] | None = None,
    ) -> DiscoverySearchResponse: ...


class MetadataRepository(Protocol):
    def hydrate_paper_metadata(
        self,
        paper_ids: list[str],
    ) -> dict[str, PaperSearchMetadata]: ...


class CuratedSearchUnavailableError(RuntimeError):
    """Raised only when neither complementary retrieval source is available."""


@dataclass(frozen=True)
class _SourcePull(Generic[SourceResponse]):
    source: Literal["evidence", "discovery"]
    collection: str
    elapsed_ms: int
    response: SourceResponse | None = None
    error: str | None = None


class CuratedResearchService:
    def __init__(
        self,
        *,
        research_index: ResearchIndex,
        discovery_index: DiscoveryIndex,
        metadata_repository: MetadataRepository,
        candidate_multiplier: int = 6,
        candidate_minimum: int = 50,
        evidence_weight: float = 1.0,
        discovery_weight: float = 1.0,
        rrf_k: int = 60,
        default_evidence_items_per_paper: int = 3,
        default_token_budget: int = 12_000,
        maximum_abstract_chars: int = 2_400,
        history_recorder: SearchHistoryRecorder | None = None,
    ):
        if candidate_multiplier < 1 or candidate_minimum < 1:
            raise ValueError("candidate sizing must be positive")
        if evidence_weight <= 0 or discovery_weight <= 0:
            raise ValueError("source weights must be positive")
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        self.research_index = research_index
        self.discovery_index = discovery_index
        self.metadata_repository = metadata_repository
        self.candidate_multiplier = candidate_multiplier
        self.candidate_minimum = candidate_minimum
        self.evidence_weight = evidence_weight
        self.discovery_weight = discovery_weight
        self.rrf_k = rrf_k
        self.default_evidence_items_per_paper = default_evidence_items_per_paper
        self.default_token_budget = default_token_budget
        self.maximum_abstract_chars = maximum_abstract_chars
        self.history_recorder = history_recorder

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        paper_id: str | None = None,
        kinds: Sequence[ResearchPointKind] | None = None,
        categories: Sequence[str] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        min_relevance: float | None = None,
        evidence_items_per_paper: int | None = None,
        token_budget: int | None = None,
        client: dict[str, Any] | None = None,
    ) -> CuratedResearchSearchResponse:
        if limit < 1:
            raise ValueError("limit must be positive")
        if start_year is not None and end_year is not None and start_year > end_year:
            raise ValueError("start_year cannot be later than end_year")
        selected_evidence_limit = (
            evidence_items_per_paper
            if evidence_items_per_paper is not None
            else self.default_evidence_items_per_paper
        )
        if selected_evidence_limit < 1:
            raise ValueError("evidence_items_per_paper must be positive")
        selected_token_budget = (
            token_budget if token_budget is not None else self.default_token_budget
        )
        if selected_token_budget < 1:
            raise ValueError("token_budget must be positive")

        request_id = f"rs_{uuid.uuid4().hex}"
        generated_at = datetime.now(timezone.utc)
        search_started = time.perf_counter()
        normalized_paper_id = normalize_arxiv_id(paper_id).base_id if paper_id else None
        source_limit = min(
            200,
            max(
                self.candidate_minimum,
                limit * self.candidate_multiplier,
            ),
        )
        request_document = {
            "contract": "curated-research-request",
            "query": query,
            "parameters": {
                "limit": limit,
                "paper_id": paper_id,
                "normalized_paper_id": normalized_paper_id,
                "kinds": list(kinds or []),
                "categories": list(categories or []),
                "start_year": start_year,
                "end_year": end_year,
                "min_relevance": min_relevance,
                "evidence_items_per_paper": selected_evidence_limit,
                "token_budget": selected_token_budget,
            },
            "execution": {
                "source_candidate_limit": source_limit,
                "candidate_multiplier": self.candidate_multiplier,
                "candidate_minimum": self.candidate_minimum,
                "evidence_weight": self.evidence_weight,
                "discovery_weight": self.discovery_weight,
                "rrf_k": self.rrf_k,
            },
        }
        self._history(
            "start_search",
            request_id=request_id,
            created_at=generated_at,
            request=request_document,
            client=client or {"channel": "unknown"},
        )
        try:
            shared_query_vector = self._shared_query_vector(query)
        except Exception as error:
            self._history(
                "fail_search",
                request_id=request_id,
                stage="query_embedding",
                error=str(error),
                duration_ms=_elapsed_ms(search_started),
            )
            raise

        research_pull, discovery_pull = self._retrieve_sources(
            query=query,
            limit=source_limit,
            paper_id=normalized_paper_id,
            kinds=kinds,
            categories=categories,
            start_year=start_year,
            end_year=end_year,
            min_relevance=min_relevance,
            shared_query_vector=shared_query_vector,
        )
        self._history(
            "save_source_pulls",
            request_id=request_id,
            created_at=generated_at,
            pulls=[
                _source_pull_document(research_pull),
                _source_pull_document(discovery_pull),
            ],
        )
        research_response = research_pull.response
        research_error = research_pull.error
        discovery_response = discovery_pull.response
        discovery_error = discovery_pull.error
        if research_response is None and discovery_response is None:
            source_failure = (
                "Evidence and discovery indexes are both unavailable: "
                f"evidence={research_error}; discovery={discovery_error}"
            )
            self._history(
                "fail_search",
                request_id=request_id,
                stage="source_retrieval",
                error=source_failure,
                duration_ms=_elapsed_ms(search_started),
            )
            raise CuratedSearchUnavailableError(source_failure)

        research_hits = research_response.hits if research_response else []
        discovery_hits = discovery_response.hits if discovery_response else []
        research_by_paper = _group_research_hits(research_hits)
        discovery_by_paper = {hit.paper_id: hit for hit in discovery_hits}
        research_ranks = _unique_paper_ranks(research_hits)
        discovery_ranks = _unique_paper_ranks(discovery_hits)
        candidate_ids = list(
            dict.fromkeys([*research_by_paper.keys(), *discovery_by_paper.keys()])
        )
        warnings: list[str] = []
        try:
            metadata = self.metadata_repository.hydrate_paper_metadata(candidate_ids)
        except Exception as error:
            metadata = {}
            warnings.append(f"metadata_hydration: {error}")

        selected_categories = {
            value.strip() for value in categories or [] if value and value.strip()
        }
        candidates: list[CuratedPaperResult] = []
        for candidate_id in candidate_ids:
            paper_research_hits = research_by_paper.get(candidate_id, [])
            discovery_hit = discovery_by_paper.get(candidate_id)
            if kinds and not paper_research_hits:
                continue
            paper_metadata = metadata.get(candidate_id) or _fallback_metadata(
                candidate_id,
                paper_research_hits,
                discovery_hit,
            )
            paper_metadata = _bounded_abstract(
                paper_metadata,
                maximum_chars=self.maximum_abstract_chars,
            )
            if not _metadata_matches_filters(
                paper_metadata,
                categories=selected_categories,
                start_year=start_year,
                end_year=end_year,
            ):
                continue
            source_scores = _source_scores(
                candidate_id,
                research_by_paper=research_by_paper,
                discovery_by_paper=discovery_by_paper,
                research_ranks=research_ranks,
                discovery_ranks=discovery_ranks,
            )
            fused_relevance = self._paper_relevance(source_scores)
            selected_research = _curate_research_items(
                paper_research_hits,
                limit=selected_evidence_limit,
            )
            candidates.append(
                CuratedPaperResult(
                    rank=1,
                    paper_id=candidate_id,
                    resource_uri=(
                        selected_research[0].resource_uri
                        if selected_research
                        else f"paper://arxiv/{candidate_id}"
                    ),
                    tier=("evidence_backed" if selected_research else "metadata_only"),
                    relevance=fused_relevance,
                    source_scores=source_scores,
                    metadata=paper_metadata,
                    research_items=selected_research,
                )
            )

        candidates.sort(
            key=lambda item: (
                item.relevance,
                item.tier == "evidence_backed",
                max(score.relevance for score in item.source_scores),
                item.metadata.update_year or 0,
                item.paper_id,
            ),
            reverse=True,
        )
        for rank, paper in enumerate(candidates, start=1):
            paper.rank = rank

        source_coverage = [
            _research_coverage(
                self.research_index.collection_name,
                research_response,
                research_error,
            ),
            _discovery_coverage(
                self.discovery_index.collection_name,
                discovery_response,
                discovery_error,
            ),
        ]
        response = _build_response(
            request_id=request_id,
            generated_at=generated_at,
            query=query,
            candidates=candidates,
            selected=list(candidates[:limit]),
            source_coverage=source_coverage,
            requested_papers=limit,
            evidence_items_per_paper=selected_evidence_limit,
            token_budget=selected_token_budget,
        )
        response = _fit_response_to_budget(response, candidates=candidates)
        self._history(
            "complete_search",
            request_id=request_id,
            response=response,
            duration_ms=_elapsed_ms(search_started),
            warnings=warnings,
        )
        return response

    def _shared_query_vector(self, query: str) -> list[float] | None:
        research_model = getattr(self.research_index.embedder, "model_name", None)
        discovery_model = getattr(self.discovery_index.embedder, "model_name", None)
        if not research_model or research_model != discovery_model:
            return None
        return list(self.research_index.embedder.embed_query(query))

    def _retrieve_sources(
        self,
        *,
        query: str,
        limit: int,
        paper_id: str | None,
        kinds: Sequence[ResearchPointKind] | None,
        categories: Sequence[str] | None,
        start_year: int | None,
        end_year: int | None,
        min_relevance: float | None,
        shared_query_vector: Sequence[float] | None,
    ) -> tuple[
        _SourcePull[ResearchSearchResponse],
        _SourcePull[DiscoverySearchResponse],
    ]:
        research_kwargs = {
            "limit": limit,
            "paper_id": paper_id,
            "kinds": kinds,
            "min_relevance": min_relevance,
            "query_vector": shared_query_vector,
        }
        discovery_kwargs = {
            "limit": limit,
            "paper_id": paper_id,
            "categories": categories,
            "start_year": start_year,
            "end_year": end_year,
            "min_relevance": min_relevance,
            "query_vector": shared_query_vector,
        }
        with ThreadPoolExecutor(max_workers=2) as executor:
            research_future = executor.submit(
                _retrieve_source,
                source="evidence",
                collection=self.research_index.collection_name,
                search=self.research_index.search,
                query=query,
                kwargs=research_kwargs,
            )
            discovery_future = executor.submit(
                _retrieve_source,
                source="discovery",
                collection=self.discovery_index.collection_name,
                search=self.discovery_index.search,
                query=query,
                kwargs=discovery_kwargs,
            )
            research_pull = research_future.result()
            discovery_pull = discovery_future.result()
        return research_pull, discovery_pull

    def _paper_relevance(self, scores: list[PaperSourceScore]) -> float:
        fused = 0.0
        for score in scores:
            weight = (
                self.evidence_weight
                if score.source == "evidence"
                else self.discovery_weight
            )
            quality = 0.25 + 0.75 * score.relevance
            fused += weight * quality / (self.rrf_k + score.rank)
        ideal = (self.evidence_weight + self.discovery_weight) / (self.rrf_k + 1)
        return min(1.0, max(0.0, fused / ideal))

    def _history(self, method: str, **kwargs: Any) -> None:
        if self.history_recorder is None:
            return
        try:
            getattr(self.history_recorder, method)(**kwargs)
        except Exception:
            logger.exception(
                "Research search history write failed",
                extra={
                    "history_method": method,
                    "request_id": kwargs.get("request_id"),
                },
            )


def _retrieve_source(
    *,
    source: Literal["evidence", "discovery"],
    collection: str,
    search: Any,
    query: str,
    kwargs: dict[str, Any],
) -> _SourcePull[Any]:
    started = time.perf_counter()
    try:
        response = search(query, **kwargs)
        return _SourcePull(
            source=source,
            collection=collection,
            elapsed_ms=_elapsed_ms(started),
            response=response,
        )
    except Exception as error:
        return _SourcePull(
            source=source,
            collection=collection,
            elapsed_ms=_elapsed_ms(started),
            error=str(error),
        )


def _source_pull_document(pull: _SourcePull[Any]) -> dict[str, Any]:
    response = pull.response
    return {
        "source": pull.source,
        "collection": (
            response.coverage.collection if response is not None else pull.collection
        ),
        "status": response.result_status if response is not None else "unavailable",
        "elapsed_ms": pull.elapsed_ms,
        "candidate_count": len(response.hits) if response is not None else 0,
        "error": pull.error,
        "response": (
            response.model_dump(mode="json") if response is not None else None
        ),
    }


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _group_research_hits(
    hits: Sequence[ResearchSearchHit],
) -> dict[str, list[ResearchSearchHit]]:
    grouped: defaultdict[str, list[ResearchSearchHit]] = defaultdict(list)
    for hit in hits:
        grouped[hit.paper_id].append(hit)
    return dict(grouped)


def _unique_paper_ranks(
    hits: Sequence[ResearchSearchHit] | Sequence[DiscoverySearchHit],
) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for hit in hits:
        ranks.setdefault(hit.paper_id, len(ranks) + 1)
    return ranks


def _source_scores(
    paper_id: str,
    *,
    research_by_paper: dict[str, list[ResearchSearchHit]],
    discovery_by_paper: dict[str, DiscoverySearchHit],
    research_ranks: dict[str, int],
    discovery_ranks: dict[str, int],
) -> list[PaperSourceScore]:
    scores: list[PaperSourceScore] = []
    if paper_id in research_by_paper:
        top = max(research_by_paper[paper_id], key=lambda item: item.relevance)
        scores.append(
            PaperSourceScore(
                source="evidence",
                rank=research_ranks[paper_id],
                relevance=top.relevance,
                raw_score=top.score,
            )
        )
    if paper_id in discovery_by_paper:
        hit = discovery_by_paper[paper_id]
        scores.append(
            PaperSourceScore(
                source="discovery",
                rank=discovery_ranks[paper_id],
                relevance=hit.relevance,
                raw_score=hit.score,
            )
        )
    return scores


def _curate_research_items(
    hits: Sequence[ResearchSearchHit],
    *,
    limit: int,
) -> list[ResearchSearchHit]:
    ordered = sorted(hits, key=lambda item: item.relevance, reverse=True)
    deduplicated: list[ResearchSearchHit] = []
    seen_points: set[str] = set()
    seen_evidence: set[tuple[str, ...]] = set()
    for hit in ordered:
        evidence_key = tuple(sorted(hit.evidence_ids))
        if hit.point_id in seen_points or (
            evidence_key and evidence_key in seen_evidence
        ):
            continue
        seen_points.add(hit.point_id)
        if evidence_key:
            seen_evidence.add(evidence_key)
        deduplicated.append(hit)

    selected: list[ResearchSearchHit] = []
    selected_kinds: set[str] = set()
    for hit in deduplicated:
        if hit.kind not in selected_kinds:
            selected.append(hit)
            selected_kinds.add(hit.kind)
        if len(selected) == limit:
            return selected
    for hit in deduplicated:
        if hit not in selected:
            selected.append(hit)
        if len(selected) == limit:
            break
    return selected


def _fallback_metadata(
    paper_id: str,
    research_hits: Sequence[ResearchSearchHit],
    discovery_hit: DiscoverySearchHit | None,
) -> PaperSearchMetadata:
    title = (
        research_hits[0].title
        if research_hits
        else discovery_hit.title if discovery_hit else paper_id
    )
    latest_version = discovery_hit.latest_version if discovery_hit else None
    return PaperSearchMetadata(
        paper_id=paper_id,
        title=title,
        abstract=discovery_hit.abstract if discovery_hit else None,
        authors=_authors_from_discovery(discovery_hit),
        categories=discovery_hit.categories if discovery_hit else [],
        primary_category=discovery_hit.primary_category if discovery_hit else None,
        update_date=discovery_hit.update_date if discovery_hit else None,
        update_year=discovery_hit.update_year if discovery_hit else None,
        latest_version=latest_version,
        doi=discovery_hit.doi if discovery_hit else None,
        journal_ref=discovery_hit.journal_ref if discovery_hit else None,
        license=discovery_hit.license if discovery_hit else None,
        comments=discovery_hit.comments if discovery_hit else None,
        arxiv_url=f"https://arxiv.org/abs/{paper_id}",
        pdf_url=f"https://arxiv.org/pdf/{paper_id}",
        corpus_run_id=discovery_hit.corpus_run_id if discovery_hit else None,
    )


def _authors_from_discovery(hit: DiscoverySearchHit | None) -> list[str]:
    if not hit or not hit.authors:
        return []
    return [value.strip() for value in hit.authors.split(" and ") if value.strip()]


def _bounded_abstract(
    metadata: PaperSearchMetadata,
    *,
    maximum_chars: int,
) -> PaperSearchMetadata:
    abstract = metadata.abstract
    if not abstract or len(abstract) <= maximum_chars:
        return metadata
    clipped = abstract[:maximum_chars].rsplit(" ", 1)[0].rstrip(" ,;:")
    return metadata.model_copy(
        update={
            "abstract": clipped + "…",
            "abstract_truncated": True,
        }
    )


def _metadata_matches_filters(
    metadata: PaperSearchMetadata,
    *,
    categories: set[str],
    start_year: int | None,
    end_year: int | None,
) -> bool:
    if categories and not categories.intersection(metadata.categories):
        return False
    if start_year is not None or end_year is not None:
        if metadata.update_year is None:
            return False
        if start_year is not None and metadata.update_year < start_year:
            return False
        if end_year is not None and metadata.update_year > end_year:
            return False
    return True


def _research_coverage(
    collection: str,
    response: ResearchSearchResponse | None,
    error: str | None,
) -> CuratedSourceCoverage:
    if response is None:
        return CuratedSourceCoverage(
            source="evidence",
            collection=collection,
            status="unavailable",
            returned_candidates=0,
            error=error,
        )
    return CuratedSourceCoverage(
        source="evidence",
        collection=response.coverage.collection,
        status=response.result_status,
        returned_candidates=len(response.hits),
        eligible_papers=response.coverage.eligible_papers,
        eligible_points=response.coverage.eligible_points,
    )


def _discovery_coverage(
    collection: str,
    response: DiscoverySearchResponse | None,
    error: str | None,
) -> CuratedSourceCoverage:
    if response is None:
        return CuratedSourceCoverage(
            source="discovery",
            collection=collection,
            status="unavailable",
            returned_candidates=0,
            error=error,
        )
    return CuratedSourceCoverage(
        source="discovery",
        collection=response.coverage.collection,
        status=response.result_status,
        returned_candidates=len(response.hits),
        eligible_papers=response.coverage.eligible_points,
        eligible_points=response.coverage.eligible_points,
    )


def _build_response(
    *,
    request_id: str,
    generated_at: datetime,
    query: str,
    candidates: list[CuratedPaperResult],
    selected: list[CuratedPaperResult],
    source_coverage: list[CuratedSourceCoverage],
    requested_papers: int,
    evidence_items_per_paper: int,
    token_budget: int,
) -> CuratedResearchSearchResponse:
    evidence_count = sum(item.tier == "evidence_backed" for item in selected)
    metadata_count = len(selected) - evidence_count
    partial = any(item.status == "unavailable" for item in source_coverage)
    response = CuratedResearchSearchResponse(
        request_id=request_id,
        generated_at=generated_at,
        query=query,
        result_status="matches" if selected else "no_match",
        no_match_reason=(
            None
            if selected
            else "No paper from an available source met the requested filters."
        ),
        coverage=CuratedSearchCoverage(
            sources=source_coverage,
            source_candidates=sum(item.returned_candidates for item in source_coverage),
            unique_candidate_papers=len(candidates),
            returned_papers=len(selected),
            evidence_backed_papers=evidence_count,
            metadata_only_papers=metadata_count,
            partial=partial,
        ),
        budget=CuratedSearchBudget(
            requested_tokens=token_budget,
            estimated_tokens=1,
            requested_papers=requested_papers,
            returned_papers=len(selected),
            evidence_items_per_paper=evidence_items_per_paper,
            omitted_papers=max(0, len(candidates) - len(selected)),
            truncated=len(selected) < len(candidates),
        ),
        papers=selected,
    )
    return _with_estimated_tokens(response)


def _fit_response_to_budget(
    response: CuratedResearchSearchResponse,
    *,
    candidates: list[CuratedPaperResult],
) -> CuratedResearchSearchResponse:
    while response.budget.estimated_tokens > response.budget.requested_tokens:
        changed = False
        for paper in reversed(response.papers):
            if paper.tier == "evidence_backed" and paper.metadata.abstract:
                paper.metadata.abstract = None
                paper.metadata.abstract_truncated = True
                changed = True
                break
        if not changed:
            for paper in reversed(response.papers):
                if len(paper.research_items) > 1:
                    paper.research_items.pop()
                    changed = True
                    break
        if not changed:
            for paper in reversed(response.papers):
                abstract = paper.metadata.abstract
                if abstract and len(abstract) > 800:
                    paper.metadata.abstract = abstract[:800].rsplit(" ", 1)[0] + "…"
                    paper.metadata.abstract_truncated = True
                    changed = True
                    break
        if not changed and len(response.papers) > 1:
            response.papers.pop()
            changed = True
        if not changed:
            for paper in response.papers:
                if paper.metadata.abstract:
                    paper.metadata.abstract = None
                    paper.metadata.abstract_truncated = True
                    changed = True
                    break
        if not changed:
            break
        _refresh_response_counts(response, candidate_count=len(candidates))
        response = _with_estimated_tokens(response)
    response.budget.truncated = (
        response.budget.truncated
        or response.budget.estimated_tokens > response.budget.requested_tokens
    )
    return response


def _refresh_response_counts(
    response: CuratedResearchSearchResponse,
    *,
    candidate_count: int,
) -> None:
    evidence_count = sum(item.tier == "evidence_backed" for item in response.papers)
    response.coverage.returned_papers = len(response.papers)
    response.coverage.evidence_backed_papers = evidence_count
    response.coverage.metadata_only_papers = len(response.papers) - evidence_count
    response.budget.returned_papers = len(response.papers)
    response.budget.omitted_papers = max(0, candidate_count - len(response.papers))
    response.budget.truncated = response.budget.omitted_papers > 0 or any(
        paper.metadata.abstract_truncated for paper in response.papers
    )
    response.result_status = "matches" if response.papers else "no_match"


def _with_estimated_tokens(
    response: CuratedResearchSearchResponse,
) -> CuratedResearchSearchResponse:
    for _ in range(4):
        document = response.model_dump(mode="json")
        serialized = json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        estimate = max(1, math.ceil(len(serialized.encode("utf-8")) / 4))
        if estimate == response.budget.estimated_tokens:
            break
        response.budget.estimated_tokens = estimate
    return response
