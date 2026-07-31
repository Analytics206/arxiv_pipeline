# Research search history and feedback readiness

## Outcome

Every canonical `search_research` execution now receives a stable
`request_id` and writes a complete evaluation trace to MongoDB. Requests from
REST, the web UI, and MCP all use the same path and therefore produce the same
storage contract.

History is append-only evaluation data. It does not change papers, analyses,
Qdrant collections, ranking configuration, or future search results.

## Correlation identifiers

The identifiers needed by the upcoming feedback workflow already exist:

| Scope | Identifier |
| --- | --- |
| Delivered search | `request_id` |
| Returned paper | `paper_id` |
| Returned evidence, claim, or implementation idea | `point_id` |
| Verified source quote | `evidence_id` |

`request_id` is returned in the curated response and in the
`X-Research-Request-ID` HTTP response header. A typical value is
`rs_6b81712a73ad4dd1a9c42e1a1ca95039`.

The future feedback payload can reference a paper with
`request_id + paper_id` and a specific idea with
`request_id + paper_id + point_id`. The search history deliberately does not
define feedback labels yet; those will be added after the external coding
agent's return contract is finalized.

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
two separate run records. The future feedback sender should use the
`request_id` from the response it actually evaluated.

## Next feedback implementation

Once the coding agent's feedback contract is available:

1. Validate it without flattening project fit into content quality.
2. Store immutable feedback events in a separate collection.
3. Resolve every target against the saved curated output for its `request_id`.
4. Reject feedback for papers or point IDs that were not actually delivered.
5. Preserve the agent, project/context identity, timestamps, and schema
   version needed for later evaluation.
6. Derive aggregates or ranking experiments from raw events; do not overwrite
   the original search trace or feedback.

