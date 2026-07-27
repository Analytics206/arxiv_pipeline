from src.storage.mongo import MongoStorage


class FakeCursor:
    def __init__(self, documents):
        self.documents = documents
        self.operations = []

    def sort(self, field, order):
        self.operations.append(("sort", field, order))
        return self

    def skip(self, count):
        self.operations.append(("skip", count))
        return self

    def limit(self, count):
        self.operations.append(("limit", count))
        return self

    def __iter__(self):
        return iter(self.documents)


class FakePapers:
    def __init__(self):
        self.cursor = FakeCursor([{"id": "paper-1"}])
        self.last_query = None

    def find_one(self, query):
        self.last_query = query
        return {"id": query["id"]}

    def find(self, query):
        self.last_query = query
        return self.cursor


def make_storage():
    storage = MongoStorage.__new__(MongoStorage)
    storage.papers = FakePapers()
    return storage


def test_get_paper_uses_pymongo_collection_directly():
    storage = make_storage()

    paper = storage.get_paper("paper-1")

    assert paper == {"id": "paper-1"}
    assert storage.papers.last_query == {"id": "paper-1"}


def test_get_papers_applies_sort_and_pagination():
    storage = make_storage()

    papers = storage.get_papers(
        {"categories": "cs.AI"},
        limit=10,
        skip=5,
        sort_by="published",
        sort_order=-1,
    )

    assert papers == [{"id": "paper-1"}]
    assert storage.papers.last_query == {"categories": "cs.AI"}
    assert storage.papers.cursor.operations == [
        ("sort", "published", -1),
        ("skip", 5),
        ("limit", 10),
    ]
