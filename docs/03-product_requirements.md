# Product Requirements

This document defines the active requirements for the agent-first research
system. Historical graph, topic-modeling, dashboard, and event-streaming work is
listed separately so it is not mistaken for the current critical path.

## Ingestion (FR-ING)

- **FR-ING-01:** Fetch normalized metadata from arXiv for exact IDs and
  configurable category/date queries.
- **FR-ING-02:** Upsert metadata without creating duplicate paper identities.
- **FR-ING-03:** Download exact paper versions into configurable, portable PDF
  storage.
- **FR-ING-04:** Validate PDFs and record their hash, path, and processing
  state.
- **FR-ING-05:** Support bounded, resumable single-paper and multi-paper
  workflows.

## Canonical data (FR-DAT)

- **FR-DAT-01:** Store source metadata and document-processing state in MongoDB.
- **FR-DAT-02:** Store immutable, versioned analyses keyed by paper, document
  hash, schema, prompt, and model.
- **FR-DAT-03:** Keep MongoDB records independent of local filesystem drive
  letters.
- **FR-DAT-04:** Expose repository interfaces rather than database-specific
  fields in public contracts.
- **FR-DAT-05:** Treat Qdrant and any future graph as rebuildable indexes, not
  sources of truth.

## Evidence-aware analysis (FR-ANL)

- **FR-ANL-01:** Extract page-aware text while excluding bibliography content
  from evidence generation.
- **FR-ANL-02:** Produce a versioned structured analysis with TLDR, concepts,
  methods, findings, limitations, implementation ideas, risks, and open
  questions.
- **FR-ANL-03:** Attach source page and exact quote evidence to material claims.
- **FR-ANL-04:** Reject generated evidence quotes that cannot be verified in the
  parsed source page.
- **FR-ANL-05:** Record document, schema, prompt, model, and generation
  provenance.
- **FR-ANL-06:** Use quality gates and cached intermediate work so failed or
  repeated runs do not silently degrade the corpus.

## Retrieval (FR-RET)

- **FR-RET-01:** Index evidence, claims, findings, limitations, and
  implementation ideas in a versioned Qdrant collection.
- **FR-RET-02:** Generate embeddings through the shared Ollama service with a
  configurable model.
- **FR-RET-03:** Use deterministic point identities so indexing is idempotent.
- **FR-RET-04:** Search by natural-language query with paper and knowledge-kind
  filters.
- **FR-RET-05:** Return rank score, explicit score semantics, stable paper URI,
  evidence, page, and analysis/embedding provenance with each result.
- **FR-RET-06:** Evaluate retrieval quality before adopting a new embedding
  model, sparse retrieval, or reranker.
- **FR-RET-07:** Support versioned named dense/sparse vectors, filtered
  candidate generation, weighted RRF, and provenance-safe diversity reranking.

## Agent and LAN API (FR-API)

- **FR-API-01:** Publish a stable, read-only REST API and OpenAPI document.
- **FR-API-02:** Advertise service capabilities and tool descriptors at
  `/research/capabilities`.
- **FR-API-03:** List curated papers with bounded pagination.
- **FR-API-04:** Return a complete paper context package by paper ID.
- **FR-API-05:** Resolve an evidence ID to its verified quote and provenance.
- **FR-API-06:** Bind API, MCP, and UI ports through configuration so trusted
  LAN clients can connect.
- **FR-API-07:** Keep MCP as a GET-only transport adapter over the canonical
  REST service, without database credentials or duplicated retrieval logic.
- **FR-API-08:** Return deterministic token-budgeted context packages with
  explicit estimator/selection metadata, complete evidence for every included
  claim, and included/omitted counts.

## Human research workspace (FR-UI)

- **FR-UI-01:** Show service health, curated-paper count, and the active API
  address.
- **FR-UI-02:** Search curated research with paper and knowledge-kind filters.
- **FR-UI-03:** Display ranked results with scores, source pages, and quotes.
- **FR-UI-04:** Open a paper context view with methods, findings, limitations,
  implementation ideas, and provenance.
- **FR-UI-05:** Resolve API addresses from the browser hostname so the UI works
  from another computer without a rebuild.

## Inference and runtime (FR-INF)

- **FR-INF-01:** Standardize maintained application code on Python 3.13 while
  Python 3.14 compatibility remains blocked by required packages.
- **FR-INF-02:** Lock Python dependencies reproducibly with `uv.lock`.
- **FR-INF-03:** Use the shared `ai-services` Ollama instance rather than owning
  another model server.
- **FR-INF-04:** Keep analysis and embedding models configurable.
- **FR-INF-05:** Keep the core runtime free of Torch, Transformers,
  sentence-transformers, BERTopic, and Top2Vec.
- **FR-INF-06:** Provide separate core, test, and legacy container targets.

## Operations (FR-OPS)

- **FR-OPS-01:** Log ingestion, download, analysis, and indexing state changes.
- **FR-OPS-02:** Make normal reruns safe and require explicit force flags for
  intentional regeneration.
- **FR-OPS-03:** Provide dry-run and bounded batch controls for expensive work.
- **FR-OPS-04:** Provide health endpoints and focused automated tests for
  contracts, persistence, and evidence.
- **FR-OPS-05:** Document the exact startup, LAN access, bulk-processing, and
  legacy commands.

## Optional graph (FR-GPH)

- **FR-GPH-01:** Keep Neo4j disabled in the default service set.
- **FR-GPH-02:** If evaluated, model useful methods, tasks, benchmarks, claims,
  citations, and software ideas rather than only authors/categories.
- **FR-GPH-03:** Add constraints and fixed read queries before graph ingestion.
- **FR-GPH-04:** Promote graph retrieval only after it improves a measured
  question that the evaluated hybrid retrieval path still misses.

## Security (FR-SEC)

- **FR-SEC-01:** Default the service to read-only research operations.
- **FR-SEC-02:** Disable arbitrary Cypher and mutation/debug routes unless an
  explicit legacy flag is enabled.
- **FR-SEC-03:** Configure CORS with an allowlist rather than unrestricted
  credentials.
- **FR-SEC-04:** Document the current trusted-LAN boundary and prohibit direct
  public-Internet exposure.
- **FR-SEC-05:** Require authentication, authorization, TLS, and rate limiting
  before use outside a trusted LAN or VPN.

## Deferred and legacy requirements

- BERTopic and Top2Vec topic pipelines are retained only under the `legacy`
  Compose profile and are not inputs to the current agent contracts.
- The original author-paper-category Neo4j graph is retained as a historical
  experiment.
- Kafka/Zookeeper, a generic autonomous-agent platform, public multi-user
  hosting, and a UI for starting pipelines are deferred.
- Prometheus/Grafana, notebooks, model metadata, and historical analytics remain
  optional utilities; they are not acceptance dependencies for research
  serving.
