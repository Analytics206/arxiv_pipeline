"""Regression tests for the intentionally narrow legacy dependency boundary."""

from pathlib import Path
import re
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RETIRED_EMBEDDING_DEPENDENCIES = {
    "bertopic",
    "gensim",
    "hdbscan",
    "langchain-huggingface",
    "langchain-text-splitters",
    "numba",
    "scikit-learn",
    "scipy",
    "seaborn",
    "sentence-transformers",
    "top2vec",
    "umap-learn",
}

SUPPORTED_PROJECT_DEPENDENCIES = {
    "biopython",
    "confluent-kafka",
    "evaluate",
    "jupyter",
    "jupyterlab",
    "kaggle",
    "kagglehub",
    "nltk",
    "numpy",
    "pandas",
    "prometheus-client",
    "pycocoevalcap",
    "pycocotools",
    "torch",
    "transformers",
}


def requirement_names(requirements: list[str]) -> set[str]:
    """Extract normalized distribution names without importing packaging tools."""
    names = set()
    for requirement in requirements:
        match = re.match(r"[A-Za-z0-9_.-]+", requirement)
        assert match, f"Invalid requirement: {requirement}"
        names.add(match.group(0).lower().replace("_", "-"))
    return names


def project_metadata() -> dict:
    return tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())


def test_legacy_extra_contains_only_retired_embedding_dependencies():
    metadata = project_metadata()
    legacy = requirement_names(
        metadata["project"]["optional-dependencies"]["legacy"]
    )

    assert legacy == RETIRED_EMBEDDING_DEPENDENCIES


def test_supported_project_tools_are_normal_dependencies():
    metadata = project_metadata()
    normal = requirement_names(metadata["project"]["dependencies"])

    assert SUPPORTED_PROJECT_DEPENDENCIES <= normal


def test_normal_setup_does_not_enable_retired_embedding_extra():
    normal_setup_files = [
        PROJECT_ROOT / "scripts" / "setup_uv.ps1",
        PROJECT_ROOT / "scripts" / "setup_uv.sh",
        PROJECT_ROOT / "Dockerfile.jupyter",
    ]

    for setup_file in normal_setup_files:
        assert "--extra legacy" not in setup_file.read_text()
