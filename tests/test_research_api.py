from src.api.main import app
from src.api.models import research_capabilities
from src.pipeline.index_research import build_parser as build_index_parser
from src.pipeline.process_downloaded_papers import build_parser as build_batch_parser
from src.pipeline.process_paper import build_parser as build_process_parser
from src.pipeline.summarize_paper import build_parser


def test_research_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/research/papers/resolve" in paths
    assert "/research/papers" in paths
    assert "/research/papers/analysis" in paths
    assert "/research/papers/agent-context" in paths
    assert "/research/papers/context-package" in paths
    assert "/research/capabilities" in paths
    assert "/research/evidence/{evidence_id}" in paths
    assert "/research/search" in paths
    assert "/research/discovery/search" in paths
    assert "/research/federated-search" in paths
    assert "/health" in paths


def test_capabilities_are_read_only_and_harness_discoverable():
    capabilities = research_capabilities("0.8.0")

    assert capabilities.read_only is True
    assert capabilities.openapi_path == "/openapi.json"
    assert {tool.name for tool in capabilities.tools} == {
        "search_research",
        "search_paper_discovery",
        "search_federated_research",
        "list_curated_papers",
        "get_paper_context",
        "get_paper_context_package",
        "get_evidence",
    }


def test_context_package_openapi_exposes_budget_controls():
    operation = app.openapi()["paths"]["/research/papers/context-package"]["get"]
    parameters = {item["name"]: item for item in operation["parameters"]}

    assert operation["operationId"] == "get_paper_context_package"
    assert parameters["profile"]["schema"]["default"] == "standard"
    assert parameters["token_budget"]["schema"]["anyOf"][0]["minimum"] == 512


def test_summarize_cli_requires_no_import_time_services():
    arguments = build_parser().parse_args(
        [
            "--paper-id",
            "2504.18538v1",
            "--pdf",
            "paper.pdf",
        ]
    )

    assert arguments.paper_id == "2504.18538v1"
    assert arguments.pdf == "paper.pdf"


def test_research_index_cli_requires_no_import_time_services():
    arguments = build_index_parser().parse_args(
        [
            "--paper-id",
            "2504.18538v1",
        ]
    )

    assert arguments.paper_id == "2504.18538v1"


def test_end_to_end_paper_cli_requires_no_import_time_services():
    arguments = build_process_parser().parse_args(
        [
            "--paper-id",
            "2607.02134v1",
        ]
    )

    assert arguments.paper_id == "2607.02134v1"


def test_downloaded_batch_cli_requires_no_import_time_services():
    arguments = build_batch_parser().parse_args(
        [
            "--limit-per-category",
            "2",
        ]
    )

    assert arguments.limit_per_category == 2
