from src.api.routes.research import federate_search_results
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


def evidence_response():
    return ResearchSearchResponse(
        query="agent retrieval",
        limit=5,
        embedding_model="model",
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
            returned_hits=1,
        ),
        hits=[
            ResearchSearchHit(
                point_id="ev-point",
                score=0.9,
                relevance=1.0,
                paper_id="2607.00001",
                paper_version_id="2607.00001v1",
                resource_uri="paper://arxiv/2607.00001",
                title="Evidence paper",
                kind="claim",
                category="methods",
                text="Evidence-backed retrieval method.",
                pages=[1],
                evidence_ids=["ev-1"],
                evidence=[
                    {
                        "evidence_id": "ev-1",
                        "page": 1,
                        "quote": "Evidence-backed retrieval method.",
                    }
                ],
                document_hash="a" * 64,
                prompt_version="v1",
                analysis_model="model",
                embedding_model="model",
            )
        ],
    )


def discovery_response():
    def hit(paper_id, title):
        return DiscoverySearchHit(
            point_id=f"point-{paper_id}",
            score=0.9,
            relevance=1.0,
            paper_id=paper_id,
            title=title,
            metadata_hash="b" * 64,
        )

    return DiscoverySearchResponse(
        query="agent retrieval",
        limit=5,
        embedding_model="model",
        result_status="matches",
        coverage=DiscoveryCorpusCoverage(
            collection="discovery",
            eligible_points=2,
            returned_hits=2,
        ),
        hits=[
            hit("2607.00001", "Duplicate metadata paper"),
            hit("2607.00002", "Metadata-only paper"),
        ],
    )


def test_federation_keeps_tiers_and_deduplicates_in_favor_of_evidence():
    response = federate_search_results(
        query="agent retrieval",
        evidence=evidence_response(),
        discovery=discovery_response(),
    )

    assert response.evidence_backed.hits[0].paper_id == "2607.00001"
    assert [hit.paper_id for hit in response.metadata_only.hits] == ["2607.00002"]
    assert response.metadata_only.coverage.returned_hits == 1
    assert response.metadata_only.score_semantics == "rrf"
