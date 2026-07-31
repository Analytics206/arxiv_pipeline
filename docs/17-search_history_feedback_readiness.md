# Research search history and feedback correlation

## Outcome

Every canonical `search_research` execution now receives a stable
`request_id` and writes a complete evaluation trace to MongoDB. Requests from
REST, the web UI, and MCP all use the same path and therefore produce the same
storage contract.

History is append-only evaluation data. It does not change papers, analyses,
Qdrant collections, ranking configuration, or future search results.

## Correlation identifiers

The identifiers available for feedback correlation are:

| Scope | Identifier |
| --- | --- |
| Delivered search | `request_id` |
| Returned paper | `paper_id` |
| Returned evidence, claim, or implementation idea | `point_id` |
| Verified source quote | `evidence_id` |

`request_id` is returned in the curated response and in the
`X-Research-Request-ID` HTTP response header. A typical value is
`rs_6b81712a73ad4dd1a9c42e1a1ca95039`.

The feedback v1 contract requires a subject `paper_id`, `evidence_id`, or
harness-side `idea_ref`, depending on the judgment. It does not require a
search `request_id` or research `point_id`. The harness should retain the
request ID in its own run/report and may send it as an extension field; the
endpoint stores unknown fields unchanged. This keeps the exact delivered
search output available for later cross-reading without making old feedback
invalid when a search trace is unavailable.

Project fit and content quality must remain separate feedback dimensions. For
example, “does not fit this project” must not be interpreted as low-quality or
incorrect research. The stored request, source candidates, curated output, and
stable target identifiers provide enough context to preserve that distinction.

## MongoDB collections

All collections use the configured `MONGO_DB`, currently `arxiv_papers`.

### `research_search_runs`

One small lifecycle document per delivered request:

- original query and all filters;
- effective candidate, ranking, evidence, and token-budget settings;
- caller channel such as `mcp`, `web-ui`, or `rest`;
- status, timings, warnings, and result summary;
- feedback target summary containing returned paper and point IDs.

The document `_id` and `request_id` are the same. Completed records use
`status="completed"`; source or embedding failures use `status="failed"`.

### `research_search_source_pulls`

One document per retrieval source and request:

- source role and resolved Qdrant collection;
- source status and elapsed milliseconds;
- returned candidate count;
- exact pre-fusion source response, including ranks, relevance, and payload;
- error text when that source was unavailable.

The deterministic document ID is `<request_id>:<source>`. Evidence and
discovery are stored separately so large candidate sets do not approach
MongoDB's single-document size limit.

The shared query embedding vector is not stored. It can be reproduced from the
query and recorded embedding model, and omitting it avoids large low-value
history documents.

### `research_search_outputs`

One document per request containing the exact
`curated-research-results` response returned to the client after fusion,
metadata hydration, deduplication, filtering, evidence selection, and token
budgeting.

This is the baseline against which future paper/idea feedback must be
interpreted. It prevents later index growth or ranking changes from obscuring
what the coding agent actually received.

## Configuration

The default configuration enables history:

```yaml
research_search:
  history:
    enabled: true
    runs_collection: "research_search_runs"
    source_pulls_collection: "research_search_source_pulls"
    outputs_collection: "research_search_outputs"
```

Environment overrides are:

```dotenv
RESEARCH_SEARCH_HISTORY_ENABLED=true
MONGO_SEARCH_RUNS_COLLECTION=research_search_runs
MONGO_SEARCH_PULLS_COLLECTION=research_search_source_pulls
MONGO_SEARCH_OUTPUTS_COLLECTION=research_search_outputs
```

History-write failures are logged but do not suppress an otherwise useful
research result. A source failure is preserved in both source-pull history and
the normal response coverage.

## Indexes

The API creates indexes for:

- run creation time and status;
- full-text request query search;
- feedback paper and point IDs;
- unique `request_id + source` source pulls;
- unique output request IDs;
- source-pull and output creation time.

No TTL index is used because the history is intended for longitudinal
retrieval and feedback evaluation.

## Retry behavior

`search_research` remains read-only with respect to research data, but it is
not marked idempotent in MCP because each invocation creates a new evaluation
trace and returns a new `request_id`. A transport retry can therefore produce
two separate run records. The feedback sender should use the
`request_id` from the response it actually evaluated in its own run/report,
even though feedback contract v1 does not require that identifier.

## Implemented feedback boundary

`POST /research/feedback` on REST port 8000 stores immutable events in MongoDB
`harness_feedback`. It intentionally bypasses the five-tool read-only MCP
adapter.

The feedback contract does not reject a record because its paper is absent
from the current corpus. A paper can be removed or a delayed spool can arrive
after a corpus rebuild; the feedback is still real. Instead, the response
flags the paper under `unresolved_papers`. This replaces the earlier
pre-contract idea of requiring every target to appear in a saved output.

Project-relative reasons such as `not_project_fit` are stored with
`signal_scope="project_only"`. They remain separate from retrieval,
evidence/analysis, and corpus-quality signals. Raw feedback events and raw
search traces are never overwritten by later aggregates or experiments.

The full feedback envelope, reason taxonomy, validation behavior, and retry
contract are documented in
[External AI Harness Feedback Endpoint Specification](16-harness_feedback_endpoint_spec.md).
