import json
from contextlib import asynccontextmanager

import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from src.mcp_server.client import (
    ResearchApiClient,
    ResearchApiError,
    resolve_research_api_url,
)
from src.mcp_server.server import create_mcp_server


class FakeResearchApi:
    def __init__(self):
        self.calls = []

    async def get(self, path, *, params=None):
        self.calls.append((path, params))
        if path == "/research/papers/context-package":
            return {
                "contract": "agent-context-package",
                "paper": {"paper_id": params["paper_id"]},
                "budget": {
                    "profile": params.get("profile", "custom"),
                    "requested_tokens": params.get("token_budget") or 4000,
                },
            }
        if path == "/research/capabilities":
            return {
                "contract": "research-service-capabilities",
                "tools": [],
            }
        if path.startswith("/research/evidence/"):
            evidence_id = path.rsplit("/", 1)[-1]
            if evidence_id == "missing":
                raise ResearchApiError(404, "Evidence not found")
            return {
                "contract": "research-evidence",
                "evidence": {"evidence_id": evidence_id, "page": 3},
            }
        return {"contract": "fake", "path": path, "params": params}


def fake_client_factory(api):
    @asynccontextmanager
    async def factory():
        yield api

    return factory


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_research_api_url_resolution_is_strict(monkeypatch):
    monkeypatch.setenv("RESEARCH_API_URL", "http://api:8000/")

    assert resolve_research_api_url() == "http://api:8000"
    with pytest.raises(ValueError, match="absolute http"):
        resolve_research_api_url("api:8000")
    with pytest.raises(ValueError, match="without parameters"):
        resolve_research_api_url("http://api:8000?debug=true")


@pytest.mark.anyio
async def test_research_api_client_preserves_repeated_filters():
    async def handler(request):
        assert request.url.path == "/research/search"
        assert request.headers["x-research-client"] == "mcp"
        assert request.url.params.get_list("kind") == [
            "claim",
            "implementation_idea",
        ]
        return httpx.Response(
            200,
            json={"contract": "research-search-results", "hits": []},
        )

    async with ResearchApiClient(
        "http://research.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await client.get(
            "/research/search",
            params={
                "query": "agent harness validation",
                "kind": ["claim", "implementation_idea"],
                "paper_id": None,
            },
        )

    assert result["contract"] == "research-search-results"


@pytest.mark.anyio
async def test_research_api_client_surfaces_api_error_detail():
    async def handler(_):
        return httpx.Response(
            422,
            json={
                "detail": {
                    "message": "Budget too small",
                    "minimum_required_tokens": 571,
                }
            },
        )

    async with ResearchApiClient(
        "http://research.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(ResearchApiError) as caught:
            await client.get("/research/papers/context-package")

    assert caught.value.status_code == 422
    assert caught.value.detail["minimum_required_tokens"] == 571


@pytest.mark.anyio
async def test_mcp_discovers_only_the_five_read_only_tools():
    api = FakeResearchApi()
    server = create_mcp_server(
        client_factory=fake_client_factory(api),
    )

    async with create_connected_server_and_client_session(server) as session:
        result = await session.list_tools()

    assert {tool.name for tool in result.tools} == {
        "search_research",
        "list_curated_papers",
        "get_paper_context",
        "get_paper_context_package",
        "get_evidence",
    }
    for tool in result.tools:
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.openWorldHint is False
        assert tool.annotations.idempotentHint is (tool.name != "search_research")

    package_tool = next(
        tool for tool in result.tools if tool.name == "get_paper_context_package"
    )
    properties = package_tool.inputSchema["properties"]
    assert properties["profile"]["default"] == "standard"
    assert properties["token_budget"]["anyOf"][0]["minimum"] == 512

    search_tool = next(tool for tool in result.tools if tool.name == "search_research")
    search_properties = search_tool.inputSchema["properties"]
    assert search_properties["category"]["anyOf"][0]["items"]["type"] == "string"
    assert search_properties["start_year"]["anyOf"][0]["minimum"] == 1990
    assert search_properties["token_budget"]["default"] == 12000


@pytest.mark.anyio
async def test_mcp_tool_call_returns_structured_rest_contract():
    api = FakeResearchApi()
    server = create_mcp_server(
        client_factory=fake_client_factory(api),
    )

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "get_paper_context_package",
            {
                "paper_id": "2607.02134",
                "profile": "brief",
            },
        )

    assert result.isError is False
    assert result.structuredContent["contract"] == "agent-context-package"
    assert result.structuredContent["paper"]["paper_id"] == "2607.02134"
    assert api.calls == [
        (
            "/research/papers/context-package",
            {
                "paper_id": "2607.02134",
                "profile": "brief",
                "token_budget": None,
            },
        )
    ]


@pytest.mark.anyio
async def test_mcp_search_preserves_multi_source_filters():
    api = FakeResearchApi()
    server = create_mcp_server(
        client_factory=fake_client_factory(api),
    )

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "search_research",
            {
                "query": "retrieval augmented agents",
                "category": ["cs.AI", "cs.LG"],
                "start_year": 2024,
            },
        )

    assert result.isError is False
    assert api.calls == [
        (
            "/research/search",
            {
                "query": "retrieval augmented agents",
                "limit": 8,
                "paper_id": None,
                "kind": None,
                "category": ["cs.AI", "cs.LG"],
                "start_year": 2024,
                "end_year": None,
                "min_relevance": None,
                "evidence_per_paper": 3,
                "token_budget": 12000,
            },
        )
    ]


@pytest.mark.anyio
async def test_mcp_exposes_capability_paper_and_evidence_resources():
    api = FakeResearchApi()
    server = create_mcp_server(
        client_factory=fake_client_factory(api),
    )

    async with create_connected_server_and_client_session(server) as session:
        resources = await session.list_resources()
        templates = await session.list_resource_templates()
        capabilities = await session.read_resource("research://capabilities")
        paper = await session.read_resource("paper://arxiv/2607.02134")
        evidence = await session.read_resource("evidence://arxiv/ev-123")

    assert {str(item.uri) for item in resources.resources} == {
        "research://capabilities"
    }
    assert {item.uriTemplate for item in templates.resourceTemplates} == {
        "paper://arxiv/{paper_id}",
        "evidence://arxiv/{evidence_id}",
    }
    capabilities_payload = json.loads(capabilities.contents[0].text)
    paper_payload = json.loads(paper.contents[0].text)
    evidence_payload = json.loads(evidence.contents[0].text)
    assert capabilities_payload["contract"] == "research-service-capabilities"
    assert paper_payload["contract"] == "agent-context-package"
    assert paper_payload["budget"]["profile"] == "standard"
    assert evidence_payload["evidence"]["evidence_id"] == "ev-123"


@pytest.mark.anyio
async def test_mcp_converts_rest_failures_to_tool_errors():
    api = FakeResearchApi()
    server = create_mcp_server(
        client_factory=fake_client_factory(api),
    )

    async with create_connected_server_and_client_session(server) as session:
        result = await session.call_tool(
            "get_evidence",
            {"evidence_id": "missing"},
        )

    assert result.isError is True
    assert "HTTP 404" in result.content[0].text
    assert "Evidence not found" in result.content[0].text
