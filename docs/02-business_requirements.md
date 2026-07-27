# Business Requirements

## Product

ArXiv Research Intelligence is a local-first system that turns AI research
papers into trustworthy, implementation-oriented knowledge for coding agents
and AI workflow tools. A human-facing research workspace uses the same service,
contracts, and evidence as machine clients.

The system is not an autonomous-agent platform. It curates research knowledge
and serves it to external agents through stable, read-only interfaces.

## Business goals

1. Make cutting-edge AI research reusable in software projects without making
   an agent read every paper from scratch.
2. Preserve enough source evidence and provenance for a human or agent to
   verify important claims.
3. Support semantic discovery across methods, findings, limitations, and
   implementation ideas.
4. Run on personally controlled hardware, including an 8 GB GPU and a shared
   Ollama service.
5. Make the curated knowledge usable by other computers on a trusted local
   network.
6. Keep storage and model choices replaceable without changing the public
   research contract.

## Business requirements

| ID | Requirement | Product requirements |
| --- | --- | --- |
| BRD-01 | Ingest configurable arXiv metadata and exact paper PDFs | FR-ING-01 to FR-ING-05 |
| BRD-02 | Keep paper metadata, processing state, and versioned analyses in a canonical local store | FR-DAT-01 to FR-DAT-05 |
| BRD-03 | Produce structured, evidence-backed paper analyses for coding-agent use | FR-ANL-01 to FR-ANL-06 |
| BRD-04 | Provide provenance-preserving semantic discovery over curated knowledge | FR-RET-01 to FR-RET-06 |
| BRD-05 | Serve stable, read-only, budget-aware research tools to other applications and trusted LAN computers | FR-API-01 to FR-API-08 |
| BRD-06 | Give humans a practical workspace for search, review, and evidence inspection | FR-UI-01 to FR-UI-05 |
| BRD-07 | Use shared, configurable local inference and reproducible containers | FR-INF-01 to FR-INF-06 |
| BRD-08 | Make processing resumable, idempotent, observable, and safe to rerun | FR-OPS-01 to FR-OPS-05 |
| BRD-09 | Add graph relationships only when they improve measured research tasks | FR-GPH-01 to FR-GPH-04 |
| BRD-10 | Limit network exposure and protect mutation/debug operations | FR-SEC-01 to FR-SEC-05 |

## Success criteria

- A paper can move from arXiv ID to stored PDF, cited analysis, and searchable
  knowledge through one repeatable workflow.
- Search results identify the paper, knowledge kind, model/prompt version, and
  source evidence.
- An external coding-agent harness can discover and call the service from its
  OpenAPI document without database access.
- An agent can request a bounded paper context without breaking the connection
  between a selected claim and its verified evidence.
- A human can search the same collection, inspect a paper context package, and
  trace derived statements to page-level quotes.
- The core API/ingestion image does not require Torch, Transformers, BERTopic,
  or Top2Vec.

## Scope decisions

- MongoDB is the source of truth for metadata and analyses.
- Qdrant is the active, rebuildable hybrid dense/lexical index.
- Neo4j is optional and experimental until a graph evaluation demonstrates
  value beyond vector retrieval.
- BERTopic and Top2Vec are retired from the active architecture. Their code is
  retained only behind the `legacy` profile for reproducibility.
- MCP is an active thin read-only transport over the evaluated REST service.
  Project matching and feedback records remain planned; sparse retrieval and
  reranking are active only because they passed the reviewed retrieval suite.
- Kafka, a generic autonomous-agent manager, public-Internet deployment, and
  restoration of old databases are outside the current product scope.
