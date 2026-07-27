"""Page-preserving PDF extraction used by the paper analyzer."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True, slots=True)
class PageText:
    number: int
    text: str


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    start_page: int
    end_page: int
    text: str


@dataclass(frozen=True, slots=True)
class ParsedPaperDocument:
    path: Path
    document_hash: str
    pages: tuple[PageText, ...]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def page_text(self, page: int) -> str:
        if page < 1 or page > len(self.pages):
            raise KeyError(f"Page {page} is outside this document")
        return self.pages[page - 1].text

    def chunks(self, max_chars: int = 12_000) -> list[DocumentChunk]:
        if max_chars < 1_000:
            raise ValueError("max_chars must be at least 1000")

        chunks: list[DocumentChunk] = []
        current_pages: list[PageText] = []
        current_size = 0

        for page in self.pages:
            rendered = _render_page(page)
            if current_pages and current_size + len(rendered) > max_chars:
                chunks.append(self._make_chunk(current_pages))
                current_pages = []
                current_size = 0
            current_pages.append(page)
            current_size += len(rendered)

        if current_pages:
            chunks.append(self._make_chunk(current_pages))
        return chunks

    def _make_chunk(self, pages: list[PageText]) -> DocumentChunk:
        start_page = pages[0].number
        end_page = pages[-1].number
        raw_id = f"{self.document_hash}:{start_page}:{end_page}".encode()
        chunk_id = hashlib.sha256(raw_id).hexdigest()[:24]
        return DocumentChunk(
            chunk_id=chunk_id,
            start_page=start_page,
            end_page=end_page,
            text="\n\n".join(_render_page(page) for page in pages),
        )


def parse_pdf(path: str | Path) -> ParsedPaperDocument:
    """Extract text from a PDF while retaining 1-based page boundaries."""

    pdf_path = Path(path).expanduser().resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file: {pdf_path}")

    document_hash = _sha256_file(pdf_path)
    pages: list[PageText] = []
    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            text = _clean_page_text(page.get_text("text"))
            pages.append(PageText(number=page_index + 1, text=text))
    pages = _strip_reference_sections(pages)

    if not pages:
        raise ValueError(f"PDF contains no pages: {pdf_path}")
    if not any(page.text for page in pages):
        raise ValueError(
            "PDF contains no extractable text; OCR support is not implemented yet"
        )
    return ParsedPaperDocument(
        path=pdf_path,
        document_hash=document_hash,
        pages=tuple(pages),
    )


def _render_page(page: PageText) -> str:
    return f"[PAGE {page.number}]\n{page.text}"


def _clean_page_text(text: str) -> str:
    without_nulls = text.replace("\x00", "")
    dehyphenated = re.sub(r"(?<=\w)-\s*\n(?=\w)", "", without_nulls)
    return dehyphenated.strip()


def _strip_reference_sections(pages: list[PageText]) -> list[PageText]:
    """Remove bibliography text while preserving content before/after it."""

    result: list[PageText] = []
    inside_references = False
    reference_heading = re.compile(r"(?im)^[ \t]*references[ \t]*$")

    for page in pages:
        text = page.text
        if inside_references:
            if _starts_appendix(text):
                inside_references = False
                result.append(page)
            else:
                result.append(PageText(number=page.number, text=""))
            continue

        heading = reference_heading.search(text)
        if heading is None:
            result.append(page)
            continue
        result.append(
            PageText(number=page.number, text=text[: heading.start()].strip())
        )
        inside_references = True
    return result


def _starts_appendix(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines()[:20] if line.strip()]
    if any(line.casefold().startswith("appendix") for line in lines):
        return True
    for index, line in enumerate(lines[:-1]):
        if re.fullmatch(r"[A-Z](?:\.\d+)?", line):
            heading = lines[index + 1]
            if heading == heading.upper() and 3 <= len(heading) <= 100:
                return True
    return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
