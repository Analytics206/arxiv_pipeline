# Read-Only MCP Adapter Evaluation v1

## Decision

The MCP adapter is ready for trusted-LAN and local stdio harness use. It is a
transport-only component: all research behavior remains in the canonical REST
service.

The adapter is intentionally unable to connect directly to MongoDB, Qdrant,
Ollama, PDF storage, or a software-project workspace.

## SDK and transport

The implementation uses the official MCP Python SDK constrained to
`mcp>=1.28.1,<2`. On July 27, 2026, v1.28.1 was the latest stable release and
the SDK maintainers still recommended the v1 line for production; v2 was a
release candidate with a breaking stable release planned for July 28.

- Official SDK:
  <https://github.com/modelcontextprotocol/python-sdk>
- Stable v1 documentation:
  <https://github.com/modelcontextprotocol/python-sdk/tree/v1.x>

The network transport is stateless JSON Streamable HTTP at `/mcp`. The same
server supports stdio for a harness running on the research computer. Legacy
SSE is not enabled.

## Tool mapping

| MCP tool | Canonical REST operation |
| --- | --- |
| `search_research` | `GET /research/search` |
| `list_curated_papers` | `GET /research/papers` |
| `get_paper_context` | `GET /research/papers/agent-context` |
| `get_paper_context_package` | `GET /research/papers/context-package` |
| `get_evidence` | `GET /research/evidence/{evidence_id}` |

Every tool declares:

- `readOnlyHint=true`
- `destructiveHint=false`
- `idempotentHint=true`
- `openWorldHint=false`

Input schemas retain the REST constraints, including the evaluated default
search limit, context profiles, and explicit 512-32,768 context budget.
Successful JSON objects are returned as MCP structured content. REST error
status and detail are returned as MCP tool errors.

## Resources

| Resource | Behavior |
| --- | --- |
| `research://capabilities` | Current REST/OpenAPI capability contract |
| `paper://arxiv/{paper_id}` | Standard 4,000-estimated-token context package |
| `evidence://arxiv/{evidence_id}` | Verified quote/page/provenance record |

The evidence resource is a transport alias; its response still contains the
canonical paper evidence URI.

## Automated protocol checks

Seven focused tests use the official in-memory MCP client/server transport.
They cover:

- initialization and exact tool discovery;
- all four tool safety annotations;
- generated input constraints;
- structured tool output;
- fixed and templated resource discovery/read;
- repeated REST query filters;
- REST error conversion.

The complete project suite passes 67 tests.

## Live validation

The Compose `mcp` service was built and started on port 8001, then validated
with:

```powershell
python -m src.pipeline.validate_mcp `
  --url http://localhost:8001/mcp `
  --paper-id 2607.02134
```

Observed:

| Check | Result |
| --- | --- |
| MCP protocol version | `2025-11-25` |
| Server | `arxiv_research_mcp` |
| Expected tools | 5/5 |
| Read-only annotations | 5/5 |
| Fixed resources | 1/1 |
| Resource templates | 2/2 |
| Standard context budget | 4,000 requested / 3,916 estimated |
| Included evidence | 26 |
| Evidence tool resolution | Passed, source page 1 |
| Capability resource read | Passed |
| Paper resource read | Passed |
| Evidence resource read | Passed |

All live checks passed through Streamable HTTP. The validated endpoint is
`http://<research-host>:8001/mcp` on the trusted LAN.

## Security boundary

This remains an unauthenticated trusted-LAN service. It must not be forwarded
to the public Internet. Before crossing that boundary, add MCP-compatible
authentication, TLS, authorization, rate limiting, and an explicit allowed-host
policy.
