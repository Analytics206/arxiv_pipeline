from src.retrieval.discovery_evaluation import (
    DiscoveryEvaluationCase,
    DiscoveryEvaluationSuite,
    evaluate_discovery,
)
from src.retrieval.discovery_models import (
    DiscoveryCorpusCoverage,
    DiscoverySearchHit,
    DiscoverySearchResponse,
)


class FakeDiscoveryIndex:
    def search(self, query, **kwargs):
        hits = []
        if query == "relevant":
            hits = [
                DiscoverySearchHit(
                    point_id="point-a",
                    score=0.9,
                    relevance=1.0,
                    paper_id="paper-a",
                    title="Paper A",
                    metadata_hash="a" * 64,
                )
            ]
        return DiscoverySearchResponse(
            query=query,
            limit=kwargs["limit"],
            embedding_model="model",
            result_status="matches" if hits else "no_match",
            coverage=DiscoveryCorpusCoverage(
                collection="discovery",
                returned_hits=len(hits),
            ),
            hits=hits,
        )


def test_discovery_evaluation_measures_positive_and_negative_cases():
    suite = DiscoveryEvaluationSuite(
        suite_id="test",
        description="test suite",
        cases=[
            DiscoveryEvaluationCase(
                case_id="positive",
                query="relevant",
                expected_paper_ids=["paper-a"],
            ),
            DiscoveryEvaluationCase(
                case_id="negative",
                query="unrelated",
                case_type="negative",
            ),
        ],
    )

    report = evaluate_discovery(FakeDiscoveryIndex(), suite)

    assert report.recall_at_limit == 1.0
    assert report.mean_reciprocal_rank == 1.0
    assert report.negative_no_match_rate == 1.0
    assert report.positive_case_count == 1
    assert report.negative_case_count == 1
