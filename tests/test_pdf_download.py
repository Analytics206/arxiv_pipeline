from pathlib import Path

from src.analysis.identity import normalize_arxiv_id
from src.ingestion.pdf_download import (
    download_paper_pdf,
    resolve_pdf_directory,
)


class FakePdfResponse:
    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield b"%PDF-1.7\n"
        yield b"test paper bytes"


class FakePdfSession:
    def get(self, url, **kwargs):
        assert url == "https://arxiv.org/pdf/2607.02134v1"
        assert kwargs["stream"] is True
        return FakePdfResponse()


def test_pdf_download_uses_category_and_portable_path(tmp_path):
    identity = normalize_arxiv_id("2607.02134v1")

    result = download_paper_pdf(
        {
            "pdf_url": "https://arxiv.org/pdf/2607.02134v1",
            "categories": ["cs.SE"],
        },
        identity,
        directory=tmp_path,
        portable_directory="data/pdfs",
        session=FakePdfSession(),
    )

    assert result.status == "downloaded"
    assert result.path == tmp_path / "cs.SE" / "2607.02134v1.pdf"
    assert result.storage_path == str(Path("data/pdfs/cs.SE/2607.02134v1.pdf"))
    assert result.path.read_bytes().startswith(b"%PDF-")

    unchanged = download_paper_pdf(
        {
            "pdf_url": "https://arxiv.org/pdf/2607.02134v1",
            "categories": ["cs.SE"],
        },
        identity,
        directory=tmp_path,
        portable_directory="data/pdfs",
        session=FakePdfSession(),
    )
    assert unchanged.status == "unchanged"
    assert unchanged.sha256 == result.sha256


def test_pdf_directory_defaults_to_project_data(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PDF_STORAGE_DIR", raising=False)

    absolute, portable = resolve_pdf_directory(
        {"pdf_storage": {"directory": "data/pdfs"}}
    )

    assert absolute == tmp_path / "data" / "pdfs"
    assert portable == str(Path("data/pdfs"))


def test_existing_pdf_is_moved_from_old_category(tmp_path):
    identity = normalize_arxiv_id("2607.02134v1")
    old_path = tmp_path / "uncategorized" / "2607.02134v1.pdf"
    old_path.parent.mkdir()
    old_path.write_bytes(b"%PDF-1.7\nexisting")

    result = download_paper_pdf(
        {
            "pdf_url": "https://arxiv.org/pdf/2607.02134v1",
            "categories": ["cs.AI"],
        },
        identity,
        directory=tmp_path,
        portable_directory="data/pdfs",
        session=FakePdfSession(),
    )

    assert result.status == "moved"
    assert result.path == tmp_path / "cs.AI" / "2607.02134v1.pdf"
    assert result.path.is_file()
    assert not old_path.exists()
