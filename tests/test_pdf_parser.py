from src.analysis.pdf_parser import PageText, _strip_reference_sections


def test_reference_text_is_removed_and_appendix_is_preserved():
    pages = [
        PageText(number=1, text="Conclusion text\nREFERENCES\nFirst citation"),
        PageText(number=2, text="More citations"),
        PageText(number=3, text="Paper header\nA\nTRAINING DETAILS\nAppendix body"),
    ]

    cleaned = _strip_reference_sections(pages)

    assert cleaned[0].text == "Conclusion text"
    assert cleaned[1].text == ""
    assert "Appendix body" in cleaned[2].text
