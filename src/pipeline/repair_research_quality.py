"""Repair current evidence spans and rebuild clean retrieval records."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from src.analysis.evidence_quality import expand_verification_span
from src.analysis.idea_quality import normalize_implementation_idea
from src.analysis.models import EvidenceRef, PaperAnalysis
from src.analysis.pdf_parser import ParsedPaperDocument, parse_pdf
from src.analysis.repository import AnalysisRepository
from src.retrieval.factory import create_research_index, load_project_config


@dataclass(slots=True)
class RepairStats:
    evidence_total: int = 0
    evidence_expanded: int = 0
    evidence_truncated: int = 0
    ideas_total: int = 0
    ideas_changed: int = 0

    def add(self, other: "RepairStats") -> None:
        for field_name in self.__dataclass_fields__:
            setattr(
                self,
                field_name,
                getattr(self, field_name) + getattr(other, field_name),
            )


def repair_analysis_quality(
    analysis: PaperAnalysis,
    document: ParsedPaperDocument,
) -> tuple[PaperAnalysis, RepairStats]:
    """Return a quality-repaired analysis without changing evidence IDs."""

    if document.document_hash != analysis.document_hash:
        raise ValueError(
            f"PDF hash mismatch for {analysis.paper_id}: "
            f"{document.document_hash} != {analysis.document_hash}"
        )
    stats = RepairStats()
    evidence: list[EvidenceRef] = []
    for item in analysis.evidence:
        stats.evidence_total += 1
        supporting_quote = item.supporting_quote or item.quote
        span = expand_verification_span(
            supporting_quote,
            document.page_text(item.page),
        )
        repaired = item.model_copy(
            update={
                "quote": span.quote,
                "supporting_quote": span.supporting_quote,
                "truncated": span.truncated,
            }
        )
        if repaired.quote != item.quote:
            stats.evidence_expanded += 1
        if repaired.truncated:
            stats.evidence_truncated += 1
        evidence.append(repaired)

    ideas = []
    for item in analysis.implementation_ideas:
        stats.ideas_total += 1
        normalized = normalize_implementation_idea(item)
        if normalized != item:
            stats.ideas_changed += 1
        ideas.append(normalized)

    return (
        analysis.model_copy(
            update={
                "evidence": evidence,
                "implementation_ideas": ideas,
            }
        ),
        stats,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Expand current evidence to sentence boundaries, normalize ideas, "
            "and rebuild the research index"
        )
    )
    parser.add_argument("--config", default="config/default.yaml")
    parser.add_argument(
        "--paper-id",
        action="append",
        dest="paper_ids",
        help="Optional paper ID; repeat to repair a subset",
    )
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Measure repairs without writing MongoDB or Qdrant",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Repair MongoDB without rebuilding Qdrant",
    )
    return parser


def resolve_pdf_path(
    analysis: PaperAnalysis,
    paper: dict | None,
    storage_root: Path,
    pdf_files: dict[str, list[Path]] | None = None,
) -> Path:
    """Resolve metadata paths first, then the deterministic corpus filename."""

    metadata_path = (paper or {}).get("local_pdf_path")
    if metadata_path:
        candidate = Path(metadata_path)
        if candidate.is_file():
            return candidate
    available = pdf_files if pdf_files is not None else _index_pdf_files(storage_root)
    matches = available.get(f"{analysis.paper_version_id}.pdf", [])
    if not matches:
        matches = [
            path
            for filename, paths in available.items()
            if filename.startswith(analysis.paper_id) and filename.endswith(".pdf")
            for path in paths
        ]
    if len(matches) != 1:
        raise FileNotFoundError(
            f"expected one PDF for {analysis.paper_version_id}, found {len(matches)}"
        )
    return matches[0]


def _index_pdf_files(storage_root: Path) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = {}
    for path in storage_root.rglob("*.pdf"):
        result.setdefault(path.name, []).append(path)
    return result


def main() -> None:
    args = build_parser().parse_args()
    config = load_project_config(Path(args.config))
    mongo = config.get("mongo", {})
    connection_string = os.getenv("MONGO_CONNECTION_STRING")
    if not connection_string:
        connection_string = (
            mongo.get("connection_string")
            if os.path.exists("/.dockerenv")
            else mongo.get("connection_string_local")
        )
    repository = AnalysisRepository(
        connection_string=connection_string or "mongodb://localhost:27017/",
        db_name=os.getenv("MONGO_DB", mongo.get("db_name", "arxiv_papers")),
        collection_name=os.getenv(
            "MONGO_ANALYSIS_COLLECTION",
            config.get("analysis", {}).get("collection_name", "paper_analyses"),
        ),
    )
    index = None
    if not args.dry_run and not args.no_index:
        index = create_research_index(config)
    storage_root = Path(
        os.getenv("PDF_STORAGE_DIR")
        or config.get("pdf_storage", {}).get("directory")
        or "data/pdfs"
    )
    pdf_files = _index_pdf_files(storage_root)

    report = {
        "contract": "research-quality-repair",
        "dry_run": args.dry_run,
        "papers": [],
        "failed": [],
    }
    totals = RepairStats()
    try:
        analyses = repository.get_current_analyses(
            paper_ids=args.paper_ids,
            limit=args.limit,
        )
        for position, analysis in enumerate(analyses, start=1):
            print(
                f"[{position}/{len(analyses)}] repairing {analysis.paper_version_id}",
                file=sys.stderr,
                flush=True,
            )
            try:
                paper = repository.find_paper(analysis.paper_id)
                pdf_path = resolve_pdf_path(
                    analysis,
                    paper,
                    storage_root,
                    pdf_files,
                )
                document = parse_pdf(pdf_path)
                repaired, stats = repair_analysis_quality(analysis, document)
                totals.add(stats)
                changed = repaired != analysis
                index_result = None
                if not args.dry_run:
                    if changed:
                        repository.save_analysis(repaired)
                    if index is not None:
                        index_result = index.index_analysis(repaired)
                report["papers"].append(
                    {
                        "paper_id": analysis.paper_id,
                        "changed": changed,
                        "stats": asdict(stats),
                        "index": index_result,
                    }
                )
            except Exception as error:
                report["failed"].append(
                    {
                        "paper_id": analysis.paper_id,
                        "error": str(error),
                    }
                )
    finally:
        repository.close()

    report["paper_count"] = len(report["papers"])
    report["totals"] = asdict(totals)
    report["all_passed"] = not report["failed"]
    print(json.dumps(report, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
