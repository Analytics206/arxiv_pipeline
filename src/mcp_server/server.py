"""Thin read-only MCP transport over the evaluated research REST API."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Protocol

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from src.mcp_server.client import ResearchApiClient, ResearchApiError

ResearchPointKind = Literal["evidence", "claim", "implementation_idea"]
ContextProfile = Literal["brief", "standard", "deep"]
McpTransport = Literal["stdio", "streamable-http"]

SERVER_NAME = "arxiv_research_mcp"
SERVER_INSTRUCTIONS = (
    "Read-only access to curated AI-paper analyses. Search first when the "
    "paper is unknown; use get_paper_context_package for normal agent work; "
    "resolve evidence IDs before making source-sensitive claims. No tool can "
    "modify papers, databases, indexes, or software projects."
)


class ApiClient(Protocol):
    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


ApiClientFactory = Callable[[], AbstractAsyncContextManager[ApiClient]]


@dataclass
class McpApplicationContext:
    api: ApiClient


def _default_client_factory() -> AbstractAsyncContextManager[ApiClient]:
    return ResearchApiClient(
        timeout_seconds=float(os.getenv("RESEARCH_MCP_API_TIMEOUT", "30"))
    )


def create_mcp_server(
    *,
    client_factory: ApiClientFactory = _default_client_factory,
    host: str | None = None,
    port: int | None = None,
) -> FastMCP:
    """Create the adapter with injectable REST I/O for protocol tests."""

    active_api: ApiClient | None = None

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[McpApplicationContext]:
        nonlocal active_api
        async with client_factory() as api:
            active_api = api
            try:
                yield McpApplicationContext(api=api)
            finally:
                active_api = None

    server = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        host=host or os.getenv("RESEARCH_MCP_BIND", "127.0.0.1"),
        port=port or int(os.getenv("RESEARCH_MCP_PORT", "8001")),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        lifespan=lifespan,
    )

    @server.tool(
        name="search_research",
        title="Search curated research",
        annotations=_read_only_annotations("Search curated research"),
    )
    async def search_research(
        query: Annotated[
            str,
            Field(
                min_length=3,
                max_length=2000,
                description=("Natural-language implementation or research question"),
            ),
        ],
        ctx: Context,
        limit: Annotated[
            int,
            Field(
                ge=1,
                le=50,
                description="Maximum ranked hits; eight is the evaluated default",
            ),
        ] = 8,
        paper_id: Annotated[
            str | None,
            Field(
                min_length=3,
                description="Optional raw arXiv ID or arXiv URL",
            ),
        ] = None,
        kind: Annotated[
            list[ResearchPointKind] | None,
            Field(
                description=(
                    "Optional knowledge-kind filters; omit to search all kinds"
                ),
            ),
        ] = None,
        min_relevance: Annotated[
            float | None,
            Field(
                ge=0,
                le=1,
                description=(
                    "Normalized relevance threshold. Omit for the service "
                    "default; use 0 only to inspect below-threshold neighbors."
                ),
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Search evaluated hybrid retrieval with provenance-preserving results."""

        return await _tool_get(
            ctx,
            "/research/search",
            params={
                "query": query,
                "limit": limit,
                "paper_id": paper_id,
                "kind": kind,
                "min_relevance": min_relevance,
            },
        )

    @server.tool(
        name="list_curated_papers",
        title="List curated papers",
        annotations=_read_only_annotations("List curated papers"),
    )
    async def list_curated_papers(
        ctx: Context,
        offset: Annotated[
            int,
            Field(ge=0, description="Zero-based catalog offset"),
        ] = 0,
        limit: Annotated[
            int,
            Field(ge=1, le=200, description="Maximum catalog items"),
        ] = 50,
    ) -> dict[str, Any]:
        """List papers that have a current evidence-backed analysis."""

        return await _tool_get(
            ctx,
            "/research/papers",
            params={"offset": offset, "limit": limit},
        )

    @server.tool(
        name="get_paper_context",
        title="Get complete paper context",
        annotations=_read_only_annotations("Get complete paper context"),
    )
    async def get_paper_context(
        paper_id: Annotated[
            str,
            Field(min_length=3, description="Raw arXiv ID or arXiv URL"),
        ],
        ctx: Context,
    ) -> dict[str, Any]:
        """Get the complete canonical analysis; prefer the budgeted tool normally."""

        return await _tool_get(
            ctx,
            "/research/papers/agent-context",
            params={"paper_id": paper_id},
        )

    @server.tool(
        name="get_paper_context_package",
        title="Get budgeted paper context",
        annotations=_read_only_annotations("Get budgeted paper context"),
    )
    async def get_paper_context_package(
        paper_id: Annotated[
            str,
            Field(min_length=3, description="Raw arXiv ID or arXiv URL"),
        ],
        ctx: Context,
        profile: Annotated[
            ContextProfile,
            Field(
                description=(
                    "Budget alias: brief=1500, standard=4000, deep=8000 "
                    "estimated tokens"
                )
            ),
        ] = "standard",
        token_budget: Annotated[
            int | None,
            Field(
                ge=512,
                le=32768,
                description="Optional explicit budget overriding profile size",
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Get deterministic, evidence-closed context for normal agent work."""

        return await _tool_get(
            ctx,
            "/research/papers/context-package",
            params={
                "paper_id": paper_id,
                "profile": profile,
                "token_budget": token_budget,
            },
        )

    @server.tool(
        name="get_evidence",
        title="Resolve verified evidence",
        annotations=_read_only_annotations("Resolve verified evidence"),
    )
    async def get_evidence(
        evidence_id: Annotated[
            str,
            Field(
                min_length=3,
                description="Stable evidence ID returned by search or context",
            ),
        ],
        ctx: Context,
    ) -> dict[str, Any]:
        """Resolve one evidence ID to its exact quote, page, and provenance."""

        return await _tool_get(
            ctx,
            f"/research/evidence/{evidence_id}",
        )

    @server.resource(
        "research://capabilities",
        name="research_capabilities",
        title="Research service capabilities",
        description="Canonical REST/OpenAPI discovery contract.",
        mime_type="application/json",
    )
    async def research_capabilities() -> str:
        if active_api is None:
            raise RuntimeError("MCP application context is unavailable")
        return _json_resource(await active_api.get("/research/capabilities"))

    @server.resource(
        "paper://arxiv/{paper_id}",
        name="paper_context",
        title="Standard agent paper context",
        description=("The standard 4,000-estimated-token package for one arXiv paper."),
        mime_type="application/json",
    )
    async def paper_context(paper_id: str, ctx: Context) -> str:
        return _json_resource(
            await _resource_get(
                ctx,
                "/research/papers/context-package",
                params={"paper_id": paper_id, "profile": "standard"},
            )
        )

    @server.resource(
        "evidence://arxiv/{evidence_id}",
        name="research_evidence",
        title="Verified research evidence",
        description="One exact source quote with paper and analysis provenance.",
        mime_type="application/json",
    )
    async def research_evidence(evidence_id: str, ctx: Context) -> str:
        return _json_resource(
            await _resource_get(
                ctx,
                f"/research/evidence/{evidence_id}",
            )
        )

    return server


async def _tool_get(
    ctx: Context,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return await _api(ctx).get(path, params=params)
    except ResearchApiError as error:
        raise ToolError(str(error)) from error
    except Exception as error:
        raise ToolError(f"Research API request failed: {error}") from error


async def _resource_get(
    ctx: Context,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await _api(ctx).get(path, params=params)


def _api(ctx: Context) -> ApiClient:
    application = ctx.request_context.lifespan_context
    if not isinstance(application, McpApplicationContext):
        raise RuntimeError("MCP application context is unavailable")
    return application.api


def _read_only_annotations(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )


def _json_resource(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only MCP adapter for ArXiv Research Intelligence"
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=os.getenv("RESEARCH_MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument(
        "--host",
        default=os.getenv("RESEARCH_MCP_BIND", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("RESEARCH_MCP_PORT", "8001")),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    server = create_mcp_server(host=args.host, port=args.port)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
