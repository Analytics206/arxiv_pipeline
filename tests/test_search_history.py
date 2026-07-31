from copy import deepcopy
from datetime import datetime, timezone

from src.retrieval.curated_models import (
    CuratedPaperResult,
    CuratedResearchSearchResponse,
    CuratedSearchBudget,
    CuratedSearchCoverage,
    CuratedSourceCoverage,
    PaperSearchMetadata,
    PaperSourceScore,
)
from src.retrieval.models import ResearchSearchHit
from src.retrieval.search_history import (
    SEARCH_HISTORY_SCHEMA_VERSION,
    MongoSearchHistoryRepository,
)


class FakeCollection:
    def __init__(self):
        self.documents = {}
        self.indexes = []

    def create_index(self, keys, **kwargs):
        self.indexes.append((keys, kwargs))
        return kwargs.get("name")

    def insert_one(self, document):
        self.documents[document["_id"]] = deepcopy(document)

    def replace_one(self, query, document, upsert=False):
        assert upsert is True
        self.documents[query["_id"]] = deepcopy(document)

    def update_one(self, query, update):
        document = self.documents[query["_id"]]
        document.update(deepcopy(update["$set"]))


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, FakeCollection())


def response() -> CuratedResearchSearchResponse:
    paper_id = "2607.00001"
    point = ResearchSearchHit(
        point_id="point-1",
        score=0.03,
        relevance=0.9,
        paper_id=paper_id,
        paper_version_id=f"{paper_id}v1",
        resource_uri=f"paper://arxiv/{paper_id}",
        title="Paper",
        kind="implementation_idea",
        category="methods",
        text="Use the method.",
        pages=[1],
        evidence_ids=["ev-1"],
        evidence=[
            {
                "evidence_id": "ev-1",
                "page": 1,
                "quote": "Verified source.",
            }
        ],
        document_hash="a" * 64,
        prompt_version="prompt",
        analysis_model="analysis-model",
        embedding_model="embedding-model",
    )
    return CuratedResearchSearchResponse(
        request_id="rs_test",
        generated_at=datetime.now(timezone.utc),
        query="agent research",
        result_status="matches",
        coverage=CuratedSearchCoverage(
            sources=[
                CuratedSourceCoverage(
                    source="evidence",
                    collection="research",
                    status="matches",
                    returned_candidates=1,
                ),
                CuratedSourceCoverage(
                    source="discovery",
                    collection="discovery",
                    status="matches",
                    returned_candidates=1,
                ),
            ],
            source_candidates=2,
            unique_candidate_papers=1,
            returned_papers=1,
            evidence_backed_papers=1,
            metadata_only_papers=0,
        ),
        budget=CuratedSearchBudget(
            requested_tokens=12000,
            estimated_tokens=500,
            requested_papers=1,
            returned_papers=1,
            evidence_items_per_paper=3,
            omitted_papers=0,
        ),
        papers=[
            CuratedPaperResult(
                rank=1,
                paper_id=paper_id,
                resource_uri=f"paper://arxiv/{paper_id}",
                tier="evidence_backed",
                relevance=0.9,
                source_scores=[
                    PaperSourceScore(
                        source="evidence",
                        rank=1,
                        relevance=0.9,
                        raw_score=0.03,
                    )
                ],
                metadata=PaperSearchMetadata(
                    paper_id=paper_id,
                    title="Paper",
                    arxiv_url=f"https://arxiv.org/abs/{paper_id}",
                    pdf_url=f"https://arxiv.org/pdf/{paper_id}",
                ),
                research_items=[point],
            )
        ],
    )


def test_history_persists_linked_request_pulls_output_and_targets():
    database = FakeDatabase()
    repository = MongoSearchHistoryRepository(database=database)
    result = response()

    repository.start_search(
        request_id=result.request_id,
        created_at=result.generated_at,
        request={"contract": "curated-research-request", "query": result.query},
        client={"channel": "mcp"},
    )
    repository.save_source_pulls(
        request_id=result.request_id,
        created_at=result.generated_at,
        pulls=[
            {
                "source": "evidence",
                "collection": "research",
                "status": "matches",
                "elapsed_ms": 10,
                "candidate_count": 1,
                "error": None,
                "response": {"hits": [{"point_id": "point-1"}]},
            },
            {
                "source": "discovery",
                "collection": "discovery",
                "status": "matches",
                "elapsed_ms": 12,
                "candidate_count": 1,
                "error": None,
                "response": {"hits": [{"paper_id": "2607.00001"}]},
            },
        ],
    )
    repository.complete_search(
        request_id=result.request_id,
        response=result,
        duration_ms=25,
        warnings=[],
    )

    run = repository.runs.documents[result.request_id]
    assert run["schema_version"] == SEARCH_HISTORY_SCHEMA_VERSION
    assert run["status"] == "completed"
    assert run["source_pull_count"] == 2
    assert run["feedback_targets"]["paper_ids"] == ["2607.00001"]
    assert run["feedback_targets"]["point_ids"] == ["point-1"]
    assert run["feedback_targets"]["papers"][0]["tier"] == "evidence_backed"

    assert set(repository.source_pulls.documents) == {
        "rs_test:evidence",
        "rs_test:discovery",
    }
    saved_output = repository.outputs.documents[result.request_id]
    assert saved_output["response"] == result.model_dump(mode="json")
    assert saved_output["response"]["request_id"] == run["request_id"]


def test_history_marks_failed_run_without_requiring_an_output():
    database = FakeDatabase()
    repository = MongoSearchHistoryRepository(database=database)
    created_at = datetime.now(timezone.utc)

    repository.start_search(
        request_id="rs_failed",
        created_at=created_at,
        request={"query": "failure"},
        client={"channel": "rest"},
    )
    repository.fail_search(
        request_id="rs_failed",
        stage="source_retrieval",
        error="both unavailable",
        duration_ms=50,
    )

    run = repository.runs.documents["rs_failed"]
    assert run["status"] == "failed"
    assert run["failure"] == {
        "stage": "source_retrieval",
        "error": "both unavailable",
    }
    assert repository.outputs.documents == {}
