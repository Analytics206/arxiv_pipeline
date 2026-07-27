from src.retrieval.evaluation import (
    RetrievalEvaluationCase,
    RetrievalEvaluationSuite,
    evaluate_retrieval,
)
from src.retrieval.models import (
    EvidenceSnippet,
    ResearchSearchHit,
    ResearchSearchResponse,
)


def make_hit(evidence_id: str, point_id: str) -> ResearchSearchHit:
    evidence = EvidenceSnippet(
        evidence_id=evidence_id,
        page=4,
        quote="The proxy records harness calls as RL samples.",
    )
    return ResearchSearchHit(
        point_id=point_id,
        score=0.9,
        paper_id="2607.21557",
        paper_version_id="2607.21557v1",
        resource_uri="paper://arxiv/2607.21557",
        title="Harness RL",
        kind="claim",
        category="methods",
        text="The proxy records harness calls as RL samples.",
        pages=[4],
        evidence_ids=[evidence_id],
        evidence=[evidence],
        document_hash="a" * 64,
        prompt_version="v5",
        analysis_model="qwen3.5:4b",
        embedding_model="fake-embedder",
    )


class FakeIndex:
    def search(self, query, *, limit=8, paper_id=None, kinds=None):
        return ResearchSearchResponse(
            query=query,
            limit=limit,
            embedding_model="fake-embedder",
            hits=[
                make_hit("ev_wrong", "point-1"),
                make_hit("ev_expected", "point-2"),
            ],
        )


def test_retrieval_evaluation_computes_rank_and_provenance():
    suite = RetrievalEvaluationSuite(
        suite_id="test-suite",
        description="Test suite",
        cases=[
            RetrievalEvaluationCase(
                case_id="proxy",
                query="How does the proxy work?",
                expected_evidence_ids=["ev_expected"],
            )
        ],
    )

    report = evaluate_retrieval(FakeIndex(), suite)

    assert report.recall_at_limit == 1
    assert report.mean_reciprocal_rank == 0.5
    assert report.provenance_completeness == 1
    assert report.group_recall_at_limit == 1
    assert report.full_group_recall_at_limit == 1
    assert report.group_recall_at_5 == 1
    assert report.group_recall_at_8 == 1
    assert report.positive_case_count == 1
    assert report.negative_case_count == 0
    assert report.cases[0].first_relevant_rank == 2


class GroupedIndex:
    def search(self, query, *, limit=8, paper_id=None, kinds=None):
        if query == "negative":
            hits = [make_hit("ev_unrelated", "point-negative")]
        else:
            hits = [
                make_hit("ev_group_a", "point-a"),
                make_hit("ev_group_b", "point-b"),
            ]
        return ResearchSearchResponse(
            query=query,
            limit=limit,
            embedding_model="fake-embedder",
            hits=hits,
        )


def test_retrieval_evaluation_scores_groups_and_negative_controls():
    suite = RetrievalEvaluationSuite(
        suite_id="grouped-suite",
        description="Grouped and negative judgments",
        cases=[
            RetrievalEvaluationCase(
                case_id="cross-paper",
                query="positive",
                scope="cross-paper",
                expected_evidence_groups=[
                    ["ev_group_a", "ev_alternative_a"],
                    ["ev_group_b"],
                ],
            ),
            RetrievalEvaluationCase(
                case_id="unanswerable",
                query="negative",
                case_type="negative",
                scope="negative",
            ),
        ],
    )

    report = evaluate_retrieval(GroupedIndex(), suite)

    assert report.positive_case_count == 1
    assert report.negative_case_count == 1
    assert report.group_recall_at_limit == 1
    assert report.cases[0].retrieved_group_count == 2
    assert report.cases[0].relevant_group_ranks == [1, 2]
    assert report.cases[0].all_groups_retrieved is True
    assert report.full_group_recall_at_5 == 1
    assert report.full_group_recall_at_8 == 1
    assert report.cases[1].group_recall_at_limit is None
    assert report.mean_negative_top_score == 0.9
