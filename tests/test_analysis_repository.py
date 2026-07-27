from copy import deepcopy

from src.analysis.models import (
    EvidenceRef,
    PaperAnalysis,
    SupportedClaim,
)
from src.analysis.repository import AnalysisRepository


class FakeCollection:
    def __init__(self):
        self.documents = {}

    def create_index(self, *args, **kwargs):
        return kwargs.get("name", "index")

    def count_documents(self, query):
        return sum(1 for document in self.documents.values() if _matches(document, query))

    def find(self, query):
        return FakeCursor(
            [
                deepcopy(document)
                for document in self.documents.values()
                if _matches(document, query)
            ]
        )

    def update_many(self, query, update):
        for document in self.documents.values():
            if document.get("paper_id") != query.get("paper_id"):
                continue
            excluded_id = query.get("_id", {}).get("$ne")
            if document.get("_id") != excluded_id:
                document.update(update["$set"])

    def replace_one(self, query, document, upsert=False):
        self.documents[query["_id"]] = deepcopy(document)

    def find_one(self, query, sort=None):
        matching = []
        for document in self.documents.values():
            if _matches(document, query):
                matching.append(deepcopy(document))
        if not matching:
            return None
        if sort:
            for key, direction in reversed(sort):
                matching.sort(
                    key=lambda item: item.get(key),
                    reverse=direction < 0,
                )
        return matching[0]


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, key, direction):
        self.documents.sort(
            key=lambda item: item.get(key),
            reverse=direction < 0,
        )
        return self

    def skip(self, count):
        self.documents = self.documents[count:]
        return self

    def limit(self, count):
        self.documents = self.documents[:count]
        return self

    def __iter__(self):
        return iter(self.documents)


def _matches(document, query):
    for key, expected in query.items():
        values = _nested_values(document, key.split("."))
        if isinstance(expected, dict) and "$ne" in expected:
            if any(value == expected["$ne"] for value in values):
                return False
        elif not any(value == expected for value in values):
            return False
    return True


def _nested_values(value, parts):
    if not parts:
        return [value]
    if isinstance(value, list):
        return [
            nested
            for item in value
            for nested in _nested_values(item, parts)
        ]
    if not isinstance(value, dict) or parts[0] not in value:
        return []
    return _nested_values(value[parts[0]], parts[1:])


class FakeDatabase:
    def __init__(self):
        self.collections = {
            "papers": FakeCollection(),
            "paper_analyses": FakeCollection(),
        }

    def __getitem__(self, name):
        return self.collections[name]


def make_analysis(document_hash: str, prompt_version: str) -> PaperAnalysis:
    evidence_id = f"ev_{document_hash[:8]}"
    claim = SupportedClaim(
        statement="The paper presents a tested agent memory method.",
        evidence_ids=[evidence_id],
    )
    return PaperAnalysis(
        schema_version="1.0",
        prompt_version=prompt_version,
        paper_id="2504.18538",
        paper_version_id="2504.18538v1",
        resource_uri="paper://arxiv/2504.18538",
        title="Agent Memory",
        document_hash=document_hash,
        page_count=1,
        model="fake-model",
        tldr=claim,
        evidence=[
            EvidenceRef(
                evidence_id=evidence_id,
                chunk_id="chunk-1",
                page=1,
                quote="The paper presents a tested agent memory method.",
            )
        ],
    )


def test_repository_versions_analyses_and_marks_latest_current():
    database = FakeDatabase()
    repository = AnalysisRepository(database=database)
    first = make_analysis("a" * 64, "v1")
    second = make_analysis("b" * 64, "v2")

    first_id = repository.save_analysis(first)
    second_id = repository.save_analysis(second)
    latest = repository.get_latest_analysis("2504.18538")

    documents = database["paper_analyses"].documents
    assert first_id != second_id
    assert documents[first_id]["is_current"] is False
    assert documents[second_id]["is_current"] is True
    assert latest.prompt_version == "v2"


def test_repository_exact_match_is_idempotent():
    database = FakeDatabase()
    repository = AnalysisRepository(database=database)
    analysis = make_analysis("a" * 64, "v1")
    repository.save_analysis(analysis)

    matching = repository.find_matching_analysis(
        paper_id="https://arxiv.org/abs/2504.18538v1",
        document_hash=analysis.document_hash,
        schema_version=analysis.schema_version,
        prompt_version=analysis.prompt_version,
        model=analysis.model,
    )

    assert matching == analysis


def test_repository_lists_current_analyses_for_discovery():
    database = FakeDatabase()
    repository = AnalysisRepository(database=database)
    first = make_analysis("a" * 64, "v1")
    second = make_analysis("b" * 64, "v2")
    repository.save_analysis(first)
    repository.save_analysis(second)

    catalog = repository.list_current_analyses(limit=20)

    assert catalog.contract == "research-paper-catalog"
    assert catalog.total == 1
    assert len(catalog.papers) == 1
    assert catalog.papers[0].paper_id == second.paper_id
    assert catalog.papers[0].evidence_count == 1
    assert catalog.papers[0].claim_count == 1


def test_repository_returns_current_analysis_documents_for_reindexing():
    database = FakeDatabase()
    repository = AnalysisRepository(database=database)
    first = make_analysis("a" * 64, "v1")
    second = make_analysis("b" * 64, "v2")
    repository.save_analysis(first)
    repository.save_analysis(second)

    analyses = repository.get_current_analyses(limit=20)

    assert analyses == [second]


def test_repository_resolves_evidence_with_analysis_provenance():
    database = FakeDatabase()
    repository = AnalysisRepository(database=database)
    analysis = make_analysis("a" * 64, "v1")
    repository.save_analysis(analysis)

    result = repository.get_evidence(analysis.evidence[0].evidence_id)

    assert result.contract == "research-evidence"
    assert result.paper_id == analysis.paper_id
    assert result.evidence.page == 1
    assert result.evidence.quote == analysis.evidence[0].quote
    assert result.evidence_uri.endswith(
        f"#evidence/{analysis.evidence[0].evidence_id}"
    )
