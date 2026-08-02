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
harness-side `idea_ref`, depending on the judgment. It recommends the search
`request_id` and accepts an optional research `point_id`. When `request_id` is
present, the endpoint resolves the immutable archived response and rejects a
paper or point that was not delivered by that request. Records without a
request ID remain valid for older senders and human follow-ups.

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
  recency_weight: 0.0
  recency_half_life_days: 365
  history:
    enabled: true
    runs_collection: "research_search_runs"
    source_pulls_collection: "research_search_source_pulls"
    outputs_collection: "research_search_outputs"
```

Every run records both recency settings under `request.execution`. The default
zero weight leaves ranking unchanged while preserving an auditable lever for
the fast-moving LLM, coding-agent, and harness research corpus. A future
non-zero setting should be evaluated against request-correlated feedback
before it becomes the default.

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
`request_id` from the response it actually evaluated.

## Implemented feedback boundary

`POST /research/feedback` on REST port 8000 stores immutable events in MongoDB
`harness_feedback`. It intentionally bypasses the five-tool read-only MCP
adapter.

When a record carries `request_id`, its target is checked against
`research_search_outputs`: the request must exist, its `paper_id` must have
been delivered, and an optional `point_id` must belong to that delivered
paper. A mismatch is a per-record error and does not reject valid neighbors in
the same batch.

When `request_id` is absent, the feedback contract does not reject a record
because its paper is absent from the current corpus. A paper can be removed or
a delayed spool can arrive after a corpus rebuild; the feedback is still real.
Instead, the response flags the paper under `unresolved_papers`.

Project-relative reasons such as `not_project_fit` are stored with
`signal_scope="project_only"`. They remain separate from retrieval,
evidence/analysis, and corpus-quality signals. Raw feedback events and raw
search traces are never overwritten by later aggregates or experiments.

The full feedback envelope, reason taxonomy, validation behavior, and retry
contract are documented in
[External AI Harness Feedback Endpoint Specification](16-harness_feedback_endpoint_spec.md).
