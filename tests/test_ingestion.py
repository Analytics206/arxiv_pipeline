import pytest

from src.ingestion.fetch import ArxivClient, ArxivFetchError, ArxivPage
from src.pipeline import run_pipeline, sync_mongodb

ARXIV_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/2607.02134v1</id>
    <updated>2026-07-02T13:11:30Z</updated>
    <published>2026-07-02T13:11:30Z</published>
    <title>Coding-agents can
      replicate scientific machine learning papers</title>
    <summary>A workflow with recorded evidence.</summary>
    <author><name>Ada Researcher</name></author>
    <arxiv:primary_category term="cs.SE"/>
    <category term="cs.SE"/>
    <category term="cs.AI"/>
  </entry>
</feed>
"""


class FakeResponse:
    status_code = 200
    text = ARXIV_RESPONSE

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, response=None):
        self.request = None
        self.response = response or FakeResponse()

    def get(self, url, **kwargs):
        self.request = (url, kwargs)
        return self.response


class ResponseWithText:
    status_code = 200

    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class SequenceSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return next(self.responses)


class FailedApiResponse:
    text = ""

    def raise_for_status(self):
        import requests

        raise requests.HTTPError("API unavailable")


class PaperPageResponse:
    text = """<html><head>
      <meta name="citation_title" content="Fallback agent paper">
      <meta name="citation_author" content="Ada Researcher">
      <meta name="citation_arxiv_id" content="2607.02134">
      <meta name="citation_date" content="2026/07/02">
      <meta name="description" content="Evidence-gated coding agents.">
    </head><body>
      <span class="primary-subject">Artificial Intelligence (cs.AI)</span>
    </body></html>"""

    def raise_for_status(self):
        return None


class FallbackSession:
    def get(self, url, **kwargs):
        if "api/query" in url:
            return FailedApiResponse()
        assert url == "https://arxiv.org/abs/2607.02134v1"
        return PaperPageResponse()


def test_legacy_pipeline_entrypoint_uses_the_hardened_pipeline():
    assert run_pipeline.load_config is sync_mongodb.load_config
    assert run_pipeline.run_ingestion_pipeline is sync_mongodb.run_ingestion_pipeline
    assert run_pipeline.main is sync_mongodb.main


def test_fetch_exact_paper_normalizes_metadata_and_identity():
    session = FakeSession()
    client = ArxivClient(session=session)

    paper = client.fetch_paper_by_id("https://arxiv.org/abs/2607.02134v1")

    assert session.request[1]["params"]["id_list"] == "2607.02134v1"
    assert paper["arxiv_id"] == "2607.02134v1"
    assert paper["base_arxiv_id"] == "2607.02134"
    assert paper["title"] == (
        "Coding-agents can replicate scientific machine learning papers"
    )
    assert paper["categories"] == ["cs.SE", "cs.AI"]
    assert paper["paper_schema_version"] == "2.0"
    assert paper["arxiv_version"] == 1
    assert paper["id"] == "https://arxiv.org/abs/2607.02134v1"
    assert paper["pdf_url"] == "https://arxiv.org/pdf/2607.02134v1"


def test_exact_fetch_falls_back_to_official_paper_page():
    client = ArxivClient(session=FallbackSession())

    paper = client.fetch_paper_by_id("2607.02134v1")

    assert paper["title"] == "Fallback agent paper"
    assert paper["id"] == "https://arxiv.org/abs/2607.02134v1"
    assert paper["pdf_url"] == "https://arxiv.org/pdf/2607.02134v1"
    assert paper["categories"] == ["cs.AI"]
    assert paper["arxiv_id"] == "2607.02134v1"
    assert paper["base_arxiv_id"] == "2607.02134"
    assert paper["arxiv_version"] == 1


def test_category_fetch_uses_canonical_versioned_schema():
    client = ArxivClient(session=FakeSession())

    papers = client.fetch_papers(category="cs.AI")

    assert papers[0]["id"] == "https://arxiv.org/abs/2607.02134v1"
    assert papers[0]["arxiv_id"] == "2607.02134v1"
    assert papers[0]["base_arxiv_id"] == "2607.02134"
    assert papers[0]["arxiv_version"] == 1
    assert papers[0]["paper_schema_version"] == "2.0"


def test_category_fetch_sends_date_bounds_and_parses_pagination():
    session = FakeSession()
    client = ArxivClient(session=session)

    page = client.fetch_papers_page(
        category="cs.AI",
        search_query="ti:agents",
        start_date="2026-01-01",
        end_date="2026-01-31",
    )

    assert session.request[1]["params"]["search_query"] == (
        "cat:cs.AI AND ti:agents AND " "submittedDate:[202601010000 TO 202601312359]"
    )
    assert page.total_results == 1
    assert page.start_index == 0
    assert page.items_per_page == 1
    assert page.papers[0]["arxiv_id"] == "2607.02134v1"


def test_bulk_fetch_rejects_invalid_date_range():
    client = ArxivClient(session=FakeSession())

    with pytest.raises(ValueError, match="must not be after"):
        client.fetch_papers(
            category="cs.AI",
            start_date="2026-02-01",
            end_date="2026-01-01",
        )


def test_bulk_fetch_retries_malformed_atom_xml(monkeypatch):
    session = SequenceSession(
        [
            ResponseWithText("<feed"),
            ResponseWithText(ARXIV_RESPONSE),
        ]
    )
    client = ArxivClient(session=session)
    sleeps = []
    monkeypatch.setattr(sync_mongodb.time, "sleep", sleeps.append)

    page = sync_mongodb._fetch_with_retries(
        client,
        category="cs.AI",
        search_query=None,
        start=0,
        start_date="2026-01-01",
        end_date="2026-01-31",
        attempts=2,
    )

    assert len(session.requests) == 2
    assert sleeps == [10]
    assert page.papers[0]["arxiv_id"] == "2607.02134v1"


def test_exact_fetch_rejects_a_different_returned_version():
    wrong_version = ARXIV_RESPONSE.replace("2607.02134v1", "2607.02134v2")
    client = ArxivClient(session=FakeSession(ResponseWithText(wrong_version)))

    with pytest.raises(ArxivFetchError, match="exact version request"):
        client.fetch_paper_by_id("2607.02134v1")


def test_metadata_import_advances_by_returned_records_and_stops_at_total(
    monkeypatch,
):
    starts = []
    stored_batches = []

    class FakeArxivClient:
        def __init__(self, **kwargs):
            pass

        def fetch_papers_page(self, **kwargs):
            start = kwargs["start"]
            starts.append(start)
            if start == 0:
                papers = [
                    {"id": "https://arxiv.org/abs/2607.00001v1"},
                    {"id": "https://arxiv.org/abs/2607.00002v1"},
                ]
            elif start == 2:
                papers = [{"id": "https://arxiv.org/abs/2607.00003v1"}]
            else:
                raise AssertionError(f"Unexpected offset: {start}")
            return ArxivPage(
                papers=papers,
                total_results=3,
                start_index=start,
                items_per_page=100,
            )

    class FakeMongoStorage:
        def __init__(self, **kwargs):
            pass

        def store_papers_bulk(self, papers):
            stored_batches.append([paper["id"] for paper in papers])

        def cleanup_paper_versions(self):
            return {"archived_documents": 0}

        def close(self):
            pass

    monkeypatch.setattr(sync_mongodb, "ArxivClient", FakeArxivClient)
    monkeypatch.setattr(sync_mongodb, "MongoStorage", FakeMongoStorage)

    result = sync_mongodb.run_ingestion_pipeline(
        {
            "mongo": {
                "connection_string": "mongodb://unused/",
                "db_name": "arxiv_papers",
            },
            "arxiv": {
                "categories": ["cs.AI"],
                "max_results": 100,
                "max_iterations": 10,
                "max_no_papers": 1,
                "sort_by": "submittedDate",
                "sort_order": "descending",
                "rate_limit_seconds": 0,
            },
        }
    )

    assert starts == [0, 2]
    assert stored_batches == [
        [
            "https://arxiv.org/abs/2607.00001v1",
            "https://arxiv.org/abs/2607.00002v1",
        ],
        ["https://arxiv.org/abs/2607.00003v1"],
    ]
    assert result["total_processed"] == 3


def test_metadata_import_runs_version_cleanup_at_the_end(monkeypatch):
    events = []
    fetches = []

    class FakeArxivClient:
        def __init__(self, **kwargs):
            pass

        def fetch_papers_page(self, **kwargs):
            fetches.append(kwargs)
            return ArxivPage(
                papers=[
                    {
                        "id": "https://arxiv.org/abs/2607.02134v2",
                        "published": "2026-07-02T13:11:30Z",
                    }
                ],
                total_results=1,
                start_index=0,
                items_per_page=1,
            )

    class FakeMongoStorage:
        def __init__(self, **kwargs):
            pass

        def store_papers_bulk(self, papers):
            events.append(("store", papers[0]["id"]))

        def cleanup_paper_versions(self):
            events.append(("cleanup", None))
            return {"archived_documents": 1}

        def close(self):
            events.append(("close", None))

    monkeypatch.setattr(sync_mongodb, "ArxivClient", FakeArxivClient)
    monkeypatch.setattr(sync_mongodb, "MongoStorage", FakeMongoStorage)

    result = sync_mongodb.run_ingestion_pipeline(
        {
            "mongo": {
                "connection_string": "mongodb://unused/",
                "db_name": "arxiv_papers",
            },
            "arxiv": {
                "categories": ["cs.AI"],
                "max_results": 100,
                "max_iterations": 5,
                "max_no_papers": 1,
                "sort_by": "submittedDate",
                "sort_order": "descending",
                "rate_limit_seconds": 0,
                "start_date": "2026-07-01",
                "end_date": "2026-07-31",
            },
        }
    )

    assert fetches == [
        {
            "category": "cs.AI",
            "search_query": None,
            "start": 0,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        }
    ]
    assert events == [
        ("store", "https://arxiv.org/abs/2607.02134v2"),
        ("cleanup", None),
        ("close", None),
    ]
    assert result["version_cleanup"] == {"archived_documents": 1}
