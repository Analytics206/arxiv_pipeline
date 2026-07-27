import pytest

from src.analysis.identity import normalize_arxiv_id, paper_lookup_aliases


@pytest.mark.parametrize(
    ("raw", "base_id", "version_id", "version"),
    [
        ("2504.18538", "2504.18538", "2504.18538", None),
        ("2504.18538v2", "2504.18538", "2504.18538v2", 2),
        (
            "https://arxiv.org/abs/2504.18538v2",
            "2504.18538",
            "2504.18538v2",
            2,
        ),
        (
            "http://arxiv.org/pdf/2504.18538v2.pdf?download=1",
            "2504.18538",
            "2504.18538v2",
            2,
        ),
        ("hep-th/9901001v3", "hep-th/9901001", "hep-th/9901001v3", 3),
    ],
)
def test_normalize_arxiv_id(raw, base_id, version_id, version):
    identity = normalize_arxiv_id(raw)

    assert identity.base_id == base_id
    assert identity.version_id == version_id
    assert identity.version == version
    assert identity.resource_uri == f"paper://arxiv/{base_id}"


def test_rejects_non_arxiv_urls():
    with pytest.raises(ValueError, match="Not an arXiv URL"):
        normalize_arxiv_id("https://example.com/abs/2504.18538")


def test_lookup_aliases_include_version_and_base_urls():
    aliases = paper_lookup_aliases("2504.18538v2")

    assert "2504.18538v2" in aliases
    assert "2504.18538" in aliases
    assert "https://arxiv.org/abs/2504.18538v2" in aliases
    assert "https://arxiv.org/pdf/2504.18538.pdf" in aliases
