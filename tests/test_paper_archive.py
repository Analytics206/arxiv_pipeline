from src.ingestion.schema import canonicalize_paper_metadata
from src.storage.mongo import MongoStorage
from src.storage.paper_archive import build_paper_cleanup_plan


def paper(version: int, *, object_id: str | None = None) -> dict:
    document = {
        "id": f"http://arxiv.org/abs/2607.21557v{version}",
        "title": "OpenForgeRL",
        "updated": f"2026-07-{20 + version:02d}T00:00:00Z",
    }
    if object_id is not None:
        document["_id"] = object_id
    return document


def test_canonical_schema_records_base_and_version():
    canonical = canonicalize_paper_metadata(paper(2))

    assert canonical["paper_schema_version"] == "2.0"
    assert canonical["base_arxiv_id"] == "2607.21557"
    assert canonical["arxiv_id"] == "2607.21557v2"
    assert canonical["arxiv_version"] == 2
    assert canonical["id"] == "https://arxiv.org/abs/2607.21557v2"
    assert canonical["pdf_url"] == "https://arxiv.org/pdf/2607.21557v2"


def test_cleanup_plan_keeps_latest_and_archives_older_versions():
    plan = build_paper_cleanup_plan(
        [paper(1, object_id="old"), paper(2, object_id="new")]
    )

    assert plan.base_papers == 1
    assert plan.current[0]["_id"] == "new"
    assert plan.current[0]["arxiv_version"] == 2
    assert plan.archive[0]["_id"] == "old"
    assert plan.archive[0]["arxiv_version"] == 1


def test_cleanup_plan_consolidates_same_version_url_variants():
    first = paper(2, object_id="http")
    second = {
        **paper(2, object_id="https"),
        "id": "https://arxiv.org/abs/2607.21557v2",
        "ingestion_timestamp": "2026-07-28T02:00:00Z",
    }

    plan = build_paper_cleanup_plan([first, second])

    assert len(plan.current) == 1
    assert plan.current[0]["_id"] == "https"
    assert len(plan.archive) == 1


class FakePaperCollection:
    def __init__(self, documents):
        self.documents = documents

    def count_documents(self, query):
        assert query == {}
        return len(self.documents)

    def find(self, query):
        assert query == {}
        return iter(self.documents)


def test_cleanup_dry_run_does_not_require_write_collections():
    storage = MongoStorage.__new__(MongoStorage)
    storage.papers = FakePaperCollection(
        [paper(1, object_id="old"), paper(2, object_id="new")]
    )

    report = storage.cleanup_paper_versions(dry_run=True)

    assert report["documents_before"] == 2
    assert report["base_papers"] == 1
    assert report["archived_documents"] == 1
    assert report["documents_after"] == 2
