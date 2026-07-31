from src.retrieval.discovery_repository import KaggleDiscoveryRepository


class FakeCursor:
    def __init__(self, documents):
        self.documents = list(documents)

    def __iter__(self):
        return iter(self.documents)

    def sort(self, field, direction):
        self.documents.sort(key=lambda document: document.get(field, ""))
        return self


class FakeCollection:
    def __init__(self, documents):
        self.documents = list(documents)

    def count_documents(self, query):
        return len(self._matching(query))

    def find_one(self, query, projection):
        documents = self._matching(query)
        return self._project(documents[0], projection) if documents else None

    def find(self, query, projection):
        return FakeCursor(
            self._project(document, projection) for document in self._matching(query)
        )

    def _matching(self, query):
        if not query:
            return self.documents
        field, condition = next(iter(query.items()))
        if "$type" in condition:
            return [
                document
                for document in self.documents
                if isinstance(document.get(field), str)
            ]
        selected = set(condition["$in"])
        return [
            document for document in self.documents if document.get(field) in selected
        ]

    @staticmethod
    def _project(document, projection):
        return {
            field: value for field, value in document.items() if projection.get(field)
        }


class FakeDatabase:
    def __init__(self, *, kaggle, papers):
        self.collections = {
            "arxiv_kaggle": FakeCollection(kaggle),
            "papers": FakeCollection(papers),
        }

    def __getitem__(self, name):
        return self.collections[name]


def kaggle_document(paper_id):
    return {
        "id": paper_id,
        "title": f"Paper {paper_id}",
        "abstract": "Abstract",
        "category_codes": ["cs.AI"],
        "corpus_run_id": "run-1",
        "retention_policy_hash": "policy-1",
        "update_date": "2026-07-30",
    }


def make_repository(paper_ids):
    database = FakeDatabase(
        kaggle=[
            kaggle_document("2607.00001"),
            kaggle_document("2607.00002"),
            kaggle_document("2607.00003"),
        ],
        papers=[{"base_arxiv_id": paper_id} for paper_id in paper_ids],
    )
    return KaggleDiscoveryRepository(database=database)


def test_repository_streams_only_kaggle_papers_present_in_papers_collection():
    repository = make_repository(
        [
            "2607.00001",
            "2607.00003v2",
            "2607.99999",
        ]
    )

    snapshot = repository.snapshot_identity()
    batches = list(repository.iter_batches(batch_size=1))

    assert snapshot["candidate_documents"] == 3
    assert snapshot["eligibility_documents"] == 3
    assert snapshot["documents"] == 2
    assert [batch[0]["id"] for batch in batches] == [
        "2607.00001",
        "2607.00003",
    ]


def test_intersection_changes_discovery_snapshot_identity():
    first = make_repository(["2607.00001"]).snapshot_identity()
    second = make_repository(["2607.00001", "2607.00002"]).snapshot_identity()

    assert first["snapshot_token"] != second["snapshot_token"]
    assert first["matched_ids_hash"] != second["matched_ids_hash"]


def test_resume_cursor_applies_to_the_intersection_not_all_kaggle_documents():
    repository = make_repository(["2607.00001", "2607.00003"])

    batches = list(
        repository.iter_batches(
            batch_size=10,
            after_id="2607.00001",
        )
    )

    assert [[document["id"] for document in batch] for batch in batches] == [
        ["2607.00003"]
    ]


def test_metadata_hydration_merges_both_mongodb_collections():
    database = FakeDatabase(
        kaggle=[
            {
                **kaggle_document("2607.00001"),
                "authors": "Ada Lovelace and Grace Hopper",
                "doi": "10.1234/example",
                "license": "https://example.test/license",
                "latest_version": "v2",
                "primary_category": "cs.AI",
            }
        ],
        papers=[
            {
                "base_arxiv_id": "2607.00001",
                "title": "Canonical title",
                "summary": "Canonical abstract",
                "authors": ["Ada Lovelace", "Grace Hopper"],
                "categories": ["cs.AI"],
                "published": "2026-07-01T00:00:00Z",
                "updated": "2026-07-30T00:00:00Z",
                "arxiv_url": "https://arxiv.org/abs/2607.00001v2",
                "pdf_url": "https://arxiv.org/pdf/2607.00001v2",
            }
        ],
    )
    repository = KaggleDiscoveryRepository(database=database)

    metadata = repository.hydrate_paper_metadata(["2607.00001"])["2607.00001"]

    assert metadata.metadata_sources == ["papers", "arxiv_kaggle"]
    assert metadata.authors == ["Ada Lovelace", "Grace Hopper"]
    assert metadata.doi == "10.1234/example"
    assert metadata.latest_version == "v2"
    assert metadata.abstract == "Abstract"
    assert metadata.arxiv_url.endswith("2607.00001v2")
