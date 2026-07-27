from src.ingestion.fetch import ArxivClient

ARXIV_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
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
    def __init__(self):
        self.request = None

    def get(self, url, **kwargs):
        self.request = (url, kwargs)
        return FakeResponse()


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
    assert paper["pdf_url"] == "http://arxiv.org/pdf/2607.02134v1"


def test_exact_fetch_falls_back_to_official_paper_page():
    client = ArxivClient(session=FallbackSession())

    paper = client.fetch_paper_by_id("2607.02134v1")

    assert paper["title"] == "Fallback agent paper"
    assert paper["id"] == "https://arxiv.org/abs/2607.02134v1"
    assert paper["pdf_url"] == "https://arxiv.org/pdf/2607.02134v1"
    assert paper["categories"] == ["cs.AI"]
    assert paper["arxiv_id"] == "2607.02134v1"
