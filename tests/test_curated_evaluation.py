from src.retrieval.curated_evaluation import (
    CuratedSearchCase,
    CuratedSearchSuite,
    evaluate_curated_search,
)
from src.retrieval.curated_models import (
    CuratedPaperResult,
    CuratedResearchSearchResponse,
    CuratedSearchBudget,
    CuratedSearchCoverage,
    CuratedSourceCoverage,
    PaperSearchMetadata,
    PaperSourceScore,
)


class FakeService:
    def search(self, query, **kwargs):
        papers = []
        if query != "negative":
            paper_id = "2607.00001"
            papers = [
                CuratedPaperResult(
                    rank=1,
                    paper_id=paper_id,
                    resource_uri=f"paper://arxiv/{paper_id}",
                    tier="metadata_only",
                    relevance=0.8,
                    source_scores=[
                        PaperSourceScore(
                            source="discovery",
                            rank=1,
                            relevance=0.8,
                            raw_score=0.03,
                        )
                    ],
                    metadata=PaperSearchMetadata(
                        paper_id=paper_id,
                        title="Paper",
                        arxiv_url=f"https://arxiv.org/abs/{paper_id}",
                        pdf_url=f"https://arxiv.org/pdf/{paper_id}",
                    ),
                )
            ]
        return CuratedResearchSearchResponse(
            request_id="rs_test",
            generated_at=datetime.now(timezone.utc),
            query=query,
            result_status="matches" if papers else "no_match",
            no_match_reason=None if papers else "No match",
            coverage=CuratedSearchCoverage(
                sources=[
                    CuratedSourceCoverage(
                        source="evidence",
                        collection="evidence",
                        status="no_match",
                        returned_candidates=0,
                    ),
                    CuratedSourceCoverage(
                        source="discovery",
                        collection="discovery",
                        status="matches" if papers else "no_match",
                        returned_candidates=len(papers),
                    ),
                ],
                source_candidates=len(papers),
                unique_candidate_papers=len(papers),
                returned_papers=len(papers),
                evidence_backed_papers=0,
                metadata_only_papers=len(papers),
            ),
            budget=CuratedSearchBudget(
                requested_tokens=12000,
                estimated_tokens=500,
                requested_papers=kwargs["limit"],
                returned_papers=len(papers),
                evidence_items_per_paper=3,
                omitted_papers=0,
            ),
            papers=papers,
        )


def test_curated_evaluation_checks_positive_negative_and_contract_invariants():
    suite = CuratedSearchSuite(
        suite_id="test",
        description="test",
        cases=[
            CuratedSearchCase(
                case_id="positive",
                query="positive",
                expected_paper_ids=["2607.00001"],
            ),
            CuratedSearchCase(
                case_id="negative",
                query="negative",
                case_type="negative",
            ),
        ],
    )

    report = evaluate_curated_search(FakeService(), suite)

    assert report.pass_rate == 1.0
    assert report.mean_recall_at_limit == 1.0
    assert report.mean_reciprocal_rank == 1.0


from datetime import datetime, timezone
