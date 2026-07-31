from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.retrieval.curated_models import PaperSearchMetadata
from src.retrieval.curated_service import CuratedResearchService
from src.retrieval.discovery_models import (
    DiscoveryCorpusCoverage,
    DiscoverySearchHit,
    DiscoverySearchResponse,
)
from src.retrieval.models import (
    ResearchSearchHit,
    ResearchSearchResponse,
    SearchCorpusCoverage,
    SearchScoreCalibration,
)


def research_hit(
    paper_id: str,
    *,
    point_id: str,
    kind: str = "claim",
    relevance: float = 0.9,
) -> ResearchSearchHit:
    evidence_id = f"ev-{point_id}"
    return ResearchSearchHit(
        point_id=point_id,
        score=0.03,
        relevance=relevance,
        paper_id=paper_id,
        paper_version_id=f"{paper_id}v1",
        resource_uri=f"paper://arxiv/{paper_id}",
        title=f"Evidence {paper_id}",
        kind=kind,
        category="methods",
        text=f"Evidence-backed method {point_id}.",
        pages=[1],
        evidence_ids=[evidence_id],
        evidence=[
            {
                "evidence_id": evidence_id,
                "page": 1,
                "quote": f"Verified source {point_id}.",
            }
        ],
        document_hash="a" * 64,
        prompt_version="prompt",
        analysis_model="analysis-model",
        embedding_model="embedding-model",
    )


def evidence_response() -> ResearchSearchResponse:
    return ResearchSearchResponse(
        query="agent retrieval",
        limit=50,
        embedding_model="embedding-model",
        retrieval_mode="hybrid",
        score_semantics="rrf",
        score_calibration=SearchScoreCalibration(
            raw_score="rrf",
            relevance="rrf_retriever_agreement_v1",
            floor=0.01,
            ceiling=0.03,
            minimum_relevance=0.05,
            description="test",
        ),
        result_status="matches",
        coverage=SearchCorpusCoverage(
            collection="evidence",
            papers=2,
            points=3,
            eligible_papers=2,
            eligible_points=3,
            returned_hits=3,
        ),
        hits=[
            research_hit("2607.00001", point_id="one", kind="evidence"),
            research_hit("2607.00001", point_id="two", kind="claim"),
            research_hit("2607.00002", point_id="three"),
        ],
    )


def discovery_hit(paper_id: str, relevance: float = 0.9) -> DiscoverySearchHit:
    return DiscoverySearchHit(
        point_id=f"point-{paper_id}",
        score=0.03,
        relevance=relevance,
        paper_id=paper_id,
        title=f"Metadata {paper_id}",
        metadata_hash="b" * 64,
    )


def discovery_response() -> DiscoverySearchResponse:
    return DiscoverySearchResponse(
        query="agent retrieval",
        limit=50,
        embedding_model="embedding-model",
        result_status="matches",
        coverage=DiscoveryCorpusCoverage(
            collection="discovery",
            eligible_points=3,
            returned_hits=2,
        ),
        hits=[
            discovery_hit("2607.00001"),
            discovery_hit("2607.00003", relevance=0.8),
        ],
    )


class FakeEmbedder:
    model_name = "embedding-model"

    def __init__(self):
        self.queries = []

    def embed_query(self, query):
        self.queries.append(query)
        return [0.1, 0.2]


class FakeIndex:
    def __init__(self, collection_name, response=None, error=None):
        self.collection_name = collection_name
        self.response = response
        self.error = error
        self.embedder = FakeEmbedder()
        self.calls = []

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if self.error:
            raise self.error
        return self.response


class FakeMetadataRepository:
    def hydrate_paper_metadata(self, paper_ids):
        return {
            paper_id: PaperSearchMetadata(
                paper_id=paper_id,
                title=f"Merged {paper_id}",
                abstract=f"Abstract for {paper_id}",
                authors=["Researcher"],
                categories=["cs.AI"],
                primary_category="cs.AI",
                update_year=2026,
                arxiv_url=f"https://arxiv.org/abs/{paper_id}",
                pdf_url=f"https://arxiv.org/pdf/{paper_id}",
                metadata_sources=["papers", "arxiv_kaggle"],
            )
            for paper_id in paper_ids
        }


class FakeHistoryRecorder:
    def __init__(self):
        self.calls = []

    def start_search(self, **kwargs):
        self.calls.append(("start_search", kwargs))

    def save_source_pulls(self, **kwargs):
        self.calls.append(("save_source_pulls", kwargs))

    def complete_search(self, **kwargs):
        self.calls.append(("complete_search", kwargs))

    def fail_search(self, **kwargs):
        self.calls.append(("fail_search", kwargs))


def make_service(research=None, discovery=None, history=None, **service_kwargs):
    research_index = FakeIndex(
        "evidence",
        response=research if research is not None else evidence_response(),
    )
    discovery_index = FakeIndex(
        "discovery",
        response=discovery if discovery is not None else discovery_response(),
    )
    service = CuratedResearchService(
        research_index=research_index,
        discovery_index=discovery_index,
        metadata_repository=FakeMetadataRepository(),
        history_recorder=history,
        **service_kwargs,
    )
    return service, research_index, discovery_index


def test_search_merges_duplicate_sources_into_unique_papers():
    history = FakeHistoryRecorder()
    service, research_index, discovery_index = make_service(history=history)

    response = service.search(
        "agent retrieval",
        limit=3,
        token_budget=12000,
        client={"channel": "test-agent"},
    )

    assert [paper.paper_id for paper in response.papers] == [
        "2607.00001",
        "2607.00002",
        "2607.00003",
    ]
    merged = response.papers[0]
    assert merged.tier == "evidence_backed"
    assert {score.source for score in merged.source_scores} == {
        "evidence",
        "discovery",
    }
    assert len(merged.research_items) == 2
    assert merged.metadata.metadata_sources == ["papers", "arxiv_kaggle"]
    assert response.coverage.unique_candidate_papers == 3
    assert response.coverage.returned_papers == 3
    assert research_index.embedder.queries == ["agent retrieval"]
    assert discovery_index.embedder.queries == []
    assert research_index.calls[0][1]["query_vector"] == [0.1, 0.2]
    assert discovery_index.calls[0][1]["query_vector"] == [0.1, 0.2]
    assert response.request_id.startswith("rs_")
    assert [name for name, _ in history.calls] == [
        "start_search",
        "save_source_pulls",
        "complete_search",
    ]
    started = history.calls[0][1]
    assert started["request_id"] == response.request_id
    assert started["request"]["query"] == "agent retrieval"
    assert started["request"]["execution"]["recency_weight"] == 0.0
    assert started["request"]["execution"]["recency_half_life_days"] == 365.0
    assert started["client"]["channel"] == "test-agent"
    source_pulls = history.calls[1][1]["pulls"]
    assert [pull["source"] for pull in source_pulls] == [
        "evidence",
        "discovery",
    ]
    assert source_pulls[0]["candidate_count"] == 3
    assert source_pulls[0]["response"]["contract"] == "research-search-results"
    completed = history.calls[2][1]
    assert completed["response"] is response


def test_search_returns_partial_results_when_one_index_is_unavailable():
    service, _, discovery_index = make_service()
    service.research_index = FakeIndex(
        "evidence",
        error=RuntimeError("evidence unavailable"),
    )
    service.research_index.embedder = discovery_index.embedder

    response = service.search("agent retrieval", limit=2)

    assert response.coverage.partial is True
    assert all(paper.tier == "metadata_only" for paper in response.papers)
    evidence_status = next(
        source for source in response.coverage.sources if source.source == "evidence"
    )
    assert evidence_status.status == "unavailable"
    assert "evidence unavailable" in evidence_status.error


def test_search_records_both_source_failures():
    history = FakeHistoryRecorder()
    service, _, _ = make_service(history=history)
    service.research_index = FakeIndex(
        "evidence",
        error=RuntimeError("evidence unavailable"),
    )
    service.discovery_index = FakeIndex(
        "discovery",
        error=RuntimeError("discovery unavailable"),
    )
    service.discovery_index.embedder = service.research_index.embedder

    try:
        service.search("agent retrieval")
    except RuntimeError as error:
        assert "both unavailable" in str(error)
    else:
        raise AssertionError("Expected unavailable search to fail")

    assert [name for name, _ in history.calls] == [
        "start_search",
        "save_source_pulls",
        "fail_search",
    ]
    assert history.calls[-1][1]["stage"] == "source_retrieval"


def test_search_honors_filters_and_output_budget():
    response = discovery_response().model_copy(
        update={
            "hits": [
                discovery_hit("2607.00003"),
                discovery_hit("2607.00004"),
            ]
        }
    )
    service, _, _ = make_service(discovery=response)
    service.metadata_repository = SimpleNamespace(
        hydrate_paper_metadata=lambda paper_ids: {
            paper_id: PaperSearchMetadata(
                paper_id=paper_id,
                title=paper_id,
                abstract="long abstract " * 1000,
                categories=["cs.AI"],
                update_year=2026,
                arxiv_url=f"https://arxiv.org/abs/{paper_id}",
                pdf_url=f"https://arxiv.org/pdf/{paper_id}",
                metadata_sources=["arxiv_kaggle"],
            )
            for paper_id in paper_ids
        }
    )

    result = service.search(
        "agent retrieval",
        limit=4,
        categories=["cs.AI"],
        start_year=2026,
        token_budget=2000,
    )

    assert result.papers
    assert result.budget.estimated_tokens <= result.budget.requested_tokens
    assert result.budget.truncated is True


def test_recency_weight_is_neutral_by_default_and_can_favor_a_newer_paper():
    older_id = "2401.00001"
    newer_id = "2607.00001"
    discovery = discovery_response().model_copy(
        update={
            "hits": [
                discovery_hit(older_id),
                discovery_hit(newer_id),
            ]
        }
    )
    now = datetime.now(timezone.utc)

    def metadata_for(paper_ids):
        published = {
            older_id: now - timedelta(days=3 * 365),
            newer_id: now - timedelta(days=1),
        }
        return {
            paper_id: PaperSearchMetadata(
                paper_id=paper_id,
                title=paper_id,
                published=published[paper_id].isoformat(),
                update_year=published[paper_id].year,
                arxiv_url=f"https://arxiv.org/abs/{paper_id}",
                pdf_url=f"https://arxiv.org/pdf/{paper_id}",
                metadata_sources=["arxiv_kaggle"],
            )
            for paper_id in paper_ids
        }

    neutral, _, neutral_discovery = make_service(discovery=discovery)
    neutral.research_index = FakeIndex(
        "evidence",
        error=RuntimeError("evidence unavailable"),
    )
    neutral.research_index.embedder = neutral_discovery.embedder
    neutral.metadata_repository = SimpleNamespace(hydrate_paper_metadata=metadata_for)

    neutral_result = neutral.search("agent retrieval", limit=2)

    assert neutral_result.ranking == "weighted-paper-rrf"
    assert [paper.paper_id for paper in neutral_result.papers] == [
        older_id,
        newer_id,
    ]

    freshness, _, freshness_discovery = make_service(
        discovery=discovery,
        recency_weight=0.2,
        recency_half_life_days=365,
    )
    freshness.research_index = FakeIndex(
        "evidence",
        error=RuntimeError("evidence unavailable"),
    )
    freshness.research_index.embedder = freshness_discovery.embedder
    freshness.metadata_repository = SimpleNamespace(hydrate_paper_metadata=metadata_for)

    freshness_result = freshness.search("agent retrieval", limit=2)

    assert freshness_result.ranking == "weighted-paper-rrf-recency"
    assert [paper.paper_id for paper in freshness_result.papers] == [
        newer_id,
        older_id,
    ]
