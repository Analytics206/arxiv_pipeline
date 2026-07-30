from src.pipeline.process_downloaded_papers import select_downloaded_papers
from src.utils.download_pdfs import build_paper_query, select_papers


class FakeCursor:
    def __init__(self, papers):
        self.papers = list(papers)
        self.limited_to = None

    def sort(self, field, direction):
        assert field == "published"
        self.papers.sort(
            key=lambda paper: paper["published"],
            reverse=direction == -1,
        )
        return self

    def limit(self, count):
        self.limited_to = count
        self.papers = self.papers[:count]
        return self

    def __iter__(self):
        return iter(self.papers)


class FakeCollection:
    def __init__(self, papers):
        self.papers = papers
        self.queries = []

    def find(self, query):
        self.queries.append(query)
        category = query["categories"]
        papers = [
            dict(paper)
            for paper in self.papers
            if category in paper["categories"]
            and ("local_pdf_path" not in query or paper.get("local_pdf_path"))
        ]
        return FakeCursor(papers)


class FakeAnalysisCollection:
    def __init__(self, analyses):
        self.analyses = analyses
        self.queries = []

    def find(self, query, projection):
        self.queries.append((query, projection))
        return [
            dict(analysis)
            for analysis in self.analyses
            if all(analysis.get(key) == value for key, value in query.items())
        ]


CONFIG = {
    "arxiv": {
        "categories": ["cs.AI", "cs.LG"],
    },
    "pdf_storage": {
        "papers_per_category": 2,
        "process_categories": ["cs.AI", "cs.LG"],
        "download_date_filter": {
            "enabled": True,
            "start_date": "2026-01-01",
            "end_date": "2026-07-31",
            "sort_by_date": True,
        },
    },
    "research_processing": {
        "papers_per_category": 1,
    },
    "analysis": {
        "schema_version": "1.0",
        "prompt_version": "agent-paper-v5",
        "model": "qwen3.5:4b",
    },
}

PAPERS = [
    {
        "id": "https://arxiv.org/abs/2607.00001v1",
        "published": "2026-07-20T00:00:00Z",
        "categories": ["cs.AI", "cs.LG"],
        "pdf_url": "https://arxiv.org/pdf/2607.00001v1",
        "local_pdf_path": "data/pdfs/cs.AI/2607.00001v1.pdf",
        "pdf_document_hash": "a" * 64,
    },
    {
        "id": "https://arxiv.org/abs/2607.00002v1",
        "published": "2026-07-19T00:00:00Z",
        "categories": ["cs.AI"],
        "pdf_url": "https://arxiv.org/pdf/2607.00002v1",
        "local_pdf_path": "data/pdfs/cs.AI/2607.00002v1.pdf",
        "pdf_document_hash": "b" * 64,
    },
    {
        "id": "https://arxiv.org/abs/2607.00003v1",
        "published": "2026-07-18T00:00:00Z",
        "categories": ["cs.LG"],
        "pdf_url": "https://arxiv.org/pdf/2607.00003v1",
        "local_pdf_path": "data/pdfs/cs.LG/2607.00003v1.pdf",
        "pdf_document_hash": "c" * 64,
    },
]


def test_pdf_query_uses_configured_date_window():
    query = build_paper_query(CONFIG, "cs.AI")

    assert query["categories"] == "cs.AI"
    assert query["published"] == {
        "$gte": "2026-01-01T00:00:00",
        "$lte": "2026-07-31T23:59:59Z",
    }


def test_pdf_selection_is_bounded_and_deduplicated():
    papers = select_papers(FakeCollection(PAPERS), CONFIG)

    assert [paper["id"] for paper in papers] == [
        "https://arxiv.org/abs/2607.00001v1",
        "https://arxiv.org/abs/2607.00002v1",
        "https://arxiv.org/abs/2607.00003v1",
    ]


def test_analysis_selection_requires_download_and_spans_categories():
    papers = select_downloaded_papers(
        FakeCollection(PAPERS),
        CONFIG,
        categories=["cs.AI", "cs.LG"],
    )

    assert [paper["_selected_category"] for paper in papers] == [
        "cs.AI",
        "cs.LG",
    ]
    assert papers[0]["id"] == "https://arxiv.org/abs/2607.00001v1"
    assert papers[1]["id"] == "https://arxiv.org/abs/2607.00003v1"


def test_analysis_selection_advances_past_matching_current_work():
    analyses = FakeAnalysisCollection(
        [
            {
                "paper_id": "2607.00001",
                "document_hash": "a" * 64,
                "schema_version": "1.0",
                "prompt_version": "agent-paper-v5",
                "model": "qwen3.5:4b",
            }
        ]
    )

    papers = select_downloaded_papers(
        FakeCollection(PAPERS),
        CONFIG,
        analyses_collection=analyses,
        categories=["cs.AI", "cs.LG"],
    )

    assert [paper["id"] for paper in papers] == [
        "https://arxiv.org/abs/2607.00002v1",
        "https://arxiv.org/abs/2607.00003v1",
    ]


def test_forced_analysis_can_reselect_matching_work():
    analyses = FakeAnalysisCollection(
        [
            {
                "paper_id": "2607.00001",
                "document_hash": "a" * 64,
                "schema_version": "1.0",
                "prompt_version": "agent-paper-v5",
                "model": "qwen3.5:4b",
            }
        ]
    )

    papers = select_downloaded_papers(
        FakeCollection(PAPERS),
        CONFIG,
        analyses_collection=analyses,
        skip_matching_analyses=False,
        categories=["cs.AI", "cs.LG"],
    )

    assert papers[0]["id"] == "https://arxiv.org/abs/2607.00001v1"
