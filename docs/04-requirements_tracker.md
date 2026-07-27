# Requirements Tracker

Status legend: **Complete**, **In progress**, **Planned**, **Legacy**, or
**Deferred**.

## Active product

| Requirement | Status | Evidence or remaining work |
| --- | --- | --- |
| FR-ING-01..02 | Complete | Configurable arXiv ingestion and normalized MongoDB upserts |
| FR-ING-03..04 | Complete | Exact-version PDF download, validation, hashing, and portable paths |
| FR-ING-05 | Complete | `process_paper` and bounded `process_downloaded_papers` workflows |
| FR-DAT-01..05 | Complete | Canonical MongoDB analysis repository and rebuildable Qdrant index |
| FR-ANL-01..06 | Complete | Page-aware parsing, structured schema, verified evidence, provenance, cache, and quality gates |
| FR-RET-01..05,07 | Complete | `research_knowledge_hybrid_v1`, named dense/lexical vectors, deterministic IDs, filtered weighted RRF, diversity reranking, explicit score semantics, and provenance |
| FR-RET-06 | Complete | Five-paper reviewed suite, four-model benchmark, hybrid/RRF strategy benchmark, and cutoff-sensitive grouped recall |
| FR-API-01 | Complete | FastAPI REST service and `/openapi.json` |
| FR-API-02 | Complete | `/research/capabilities` advertises the read-only tool contract |
| FR-API-03 | Complete | Paginated `/research/papers` catalog |
| FR-API-04 | Complete | `/research/papers/agent-context` |
| FR-API-05 | Complete | `/research/evidence/{evidence_id}` |
| FR-API-06 | Complete | Configurable `0.0.0.0` API/MCP/UI bindings; validated from the host LAN address |
| FR-API-07 | Complete | Five read-only tools plus paper/evidence resources over stdio and Streamable HTTP; adapter has no database credentials |
| FR-API-08 | Complete | `/research/papers/context-package`; evaluated 1.5K/4K/8K profiles and explicit 512-32,768 budgets |
| FR-UI-01..05 | Complete | New home/research workspace, filters, ranked evidence, paper context, provenance, and dynamic LAN API address |
| FR-INF-01..06 | Complete | Python 3.13, uv lock, shared Ollama, configurable models, slim runtime, and separate test/legacy targets |
| FR-OPS-01..04 | Complete | State logging, idempotent workflows, bounded dry runs, health checks, and automated tests |
| FR-OPS-05 | Complete | README and system/stack/roadmap documents describe current operation |
| FR-SEC-01..04 | Complete | Read-only surface, guarded legacy operations, CORS allowlist, and trusted-LAN documentation |
| FR-SEC-05 | Planned | Required only before exposure beyond a trusted LAN/VPN |

## Optional graph

| Requirement | Status | Evidence or remaining work |
| --- | --- | --- |
| FR-GPH-01 | Complete | Neo4j uses the `manual` Compose profile and is not an API dependency |
| FR-GPH-02..04 | Planned | Build only after retrieval evaluation identifies a graph-shaped failure and define a measurable comparison |

## Legacy and deferred work

| Area | Status | Decision |
| --- | --- | --- |
| BERTopic | Legacy | Retained under the `legacy` profile; not used by the research API or Qdrant research index |
| Top2Vec | Legacy | Retained under the `legacy` profile; not used by the research API or Qdrant research index |
| Original author/category Neo4j graph | Legacy | Available manually for reference; too shallow for the active use case |
| Historical Hugging Face PDF/Qdrant pipeline | Legacy | Superseded by shared-Ollama evidence/claim/idea indexing |
| Kafka and Zookeeper | Deferred | Unnecessary for current single-host bounded workflows |
| Generic autonomous-agent platform | Deferred | External agents consume the curated research service |
| Public multi-user deployment | Deferred | Requires FR-SEC-05 before consideration |
| Pipeline-control/admin UI | Deferred | Research discovery and review are the current human workflow |
