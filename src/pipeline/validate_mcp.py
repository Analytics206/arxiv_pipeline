"""Validate the live MCP transport against one curated paper."""

from __future__ import annotations

import argparse
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

EXPECTED_TOOLS = {
    "search_research",
    "list_curated_papers",
    "get_paper_context",
    "get_paper_context_package",
    "get_evidence",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an MCP handshake and read-only research tool calls"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8001/mcp",
        help="Streamable HTTP MCP endpoint",
    )
    parser.add_argument(
        "--paper-id",
        default="2607.02134",
        help="Curated paper used for context/evidence validation",
    )
    return parser


async def validate(url: str, paper_id: str) -> dict:
    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            await session.send_ping()
            tools_result = await session.list_tools()
            resources_result = await session.list_resources()
            templates_result = await session.list_resource_templates()
            capabilities_resource = await session.read_resource(
                "research://capabilities"
            )
            paper_resource = await session.read_resource(f"paper://arxiv/{paper_id}")
            package_result = await session.call_tool(
                "get_paper_context_package",
                {"paper_id": paper_id, "profile": "standard"},
            )
            if package_result.isError:
                raise RuntimeError(package_result.content[0].text)
            package = package_result.structuredContent
            if not isinstance(package, dict):
                raise RuntimeError("Context package did not return structured content")
            evidence_items = package.get("analysis", {}).get("evidence", [])
            if not evidence_items:
                raise RuntimeError("Context package did not include evidence")
            evidence_id = evidence_items[0]["evidence_id"]
            evidence_result = await session.call_tool(
                "get_evidence",
                {"evidence_id": evidence_id},
            )
            if evidence_result.isError:
                raise RuntimeError(evidence_result.content[0].text)
            evidence = evidence_result.structuredContent
            if not isinstance(evidence, dict):
                raise RuntimeError("Evidence tool did not return structured content")
            evidence_resource = await session.read_resource(
                f"evidence://arxiv/{evidence_id}"
            )

    tool_names = {tool.name for tool in tools_result.tools}
    capabilities_payload = _resource_json(capabilities_resource)
    paper_payload = _resource_json(paper_resource)
    evidence_payload = _resource_json(evidence_resource)
    all_read_only = all(
        tool.annotations is not None
        and tool.annotations.readOnlyHint is True
        and tool.annotations.destructiveHint is False
        for tool in tools_result.tools
    )
    checks = {
        "expected_tools": tool_names == EXPECTED_TOOLS,
        "all_tools_read_only": all_read_only,
        "context_contract": package.get("contract") == "agent-context-package",
        "evidence_contract": evidence.get("contract") == "research-evidence",
        "capabilities_resource": (
            capabilities_payload.get("contract") == "research-service-capabilities"
        ),
        "paper_resource": (
            paper_payload.get("contract") == "agent-context-package"
            and paper_payload.get("budget", {}).get("profile") == "standard"
        ),
        "evidence_resource": (
            evidence_payload.get("contract") == "research-evidence"
            and evidence_payload.get("evidence", {}).get("evidence_id") == evidence_id
        ),
    }
    report = {
        "contract": "research-mcp-validation",
        "mcp_url": url,
        "protocol_version": initialized.protocolVersion,
        "server_name": initialized.serverInfo.name,
        "tools": sorted(tool_names),
        "resources": [str(resource.uri) for resource in resources_result.resources],
        "resource_templates": sorted(
            template.uriTemplate for template in templates_result.resourceTemplates
        ),
        "paper_id": package["paper"]["paper_id"],
        "context_profile": package["budget"]["profile"],
        "context_requested_tokens": package["budget"]["requested_tokens"],
        "context_estimated_tokens": package["budget"]["estimated_tokens"],
        "context_evidence_count": package["budget"]["included"]["evidence"],
        "resolved_evidence_id": evidence["evidence"]["evidence_id"],
        "resolved_evidence_page": evidence["evidence"]["page"],
        "checks": checks,
        "all_passed": all(checks.values()),
    }
    if not report["all_passed"]:
        raise RuntimeError(f"MCP validation failed: {checks}")
    return report


def _resource_json(result) -> dict:
    if not result.contents or not hasattr(result.contents[0], "text"):
        raise RuntimeError("MCP resource did not return text content")
    payload = json.loads(result.contents[0].text)
    if not isinstance(payload, dict):
        raise RuntimeError("MCP resource did not return a JSON object")
    return payload


def main() -> None:
    args = build_parser().parse_args()
    report = asyncio.run(validate(args.url, args.paper_id))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
