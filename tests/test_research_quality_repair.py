from src.analysis.models import EvidenceRef, PaperAnalysis
from src.analysis.pdf_parser import PageText, ParsedPaperDocument
from src.pipeline.repair_research_quality import (
    repair_analysis_quality,
    resolve_pdf_path,
)
from tests.test_research_index import make_analysis


def test_quality_repair_preserves_ids_and_expands_verification_context():
    analysis = make_analysis()
    source = analysis.evidence[0]
    analysis = analysis.model_copy(
        update={
            "evidence": [
                source.model_copy(
                    update={
                        "quote": (
                            "records harness model calls and reconstructs "
                            "standard reinforcement-learning samples"
                        )
                    }
                )
            ]
        }
    )
    pages = [
        PageText(number=index, text=f"Complete filler sentence {index}.")
        for index in range(1, 4)
    ]
    pages.append(
        PageText(
            number=4,
            text=(
                "The proxy sits at the model boundary. "
                "The proxy records harness model calls and reconstructs "
                "standard reinforcement-learning samples. "
                "External validators then inspect every generated sample."
            ),
        )
    )
    document = ParsedPaperDocument(
        path=None,
        document_hash=analysis.document_hash,
        pages=tuple(pages),
    )

    repaired, stats = repair_analysis_quality(analysis, document)
    evidence: EvidenceRef = repaired.evidence[0]

    assert evidence.evidence_id == source.evidence_id
    assert evidence.supporting_quote == analysis.evidence[0].quote
    assert evidence.quote.startswith("The proxy sits")
    assert evidence.quote.endswith("sample.")
    assert evidence.truncated is False
    assert repaired.implementation_ideas[0].risks == []
    assert stats.evidence_expanded == 1
    assert stats.evidence_truncated == 0


def test_quality_repair_rejects_wrong_pdf_hash():
    analysis: PaperAnalysis = make_analysis()
    document = ParsedPaperDocument(
        path=None,
        document_hash="b" * 64,
        pages=(PageText(number=1, text="A complete source sentence."),),
    )

    try:
        repair_analysis_quality(analysis, document)
    except ValueError as error:
        assert "PDF hash mismatch" in str(error)
    else:
        raise AssertionError("Expected the repair to reject a different PDF")


def test_pdf_resolution_prefers_analysis_version_over_latest_paper_metadata(tmp_path):
    analysis: PaperAnalysis = make_analysis()
    version_one = tmp_path / f"{analysis.paper_version_id}.pdf"
    version_two = tmp_path / f"{analysis.paper_id}v2.pdf"
    version_one.write_bytes(b"version one")
    version_two.write_bytes(b"version two")
    paper = {
        "local_pdf_path": str(version_two),
        "pdf_document_hash": "b" * 64,
    }
    pdf_files = {
        version_one.name: [version_one],
        version_two.name: [version_two],
    }

    resolved = resolve_pdf_path(analysis, paper, tmp_path, pdf_files)

    assert resolved == version_one
