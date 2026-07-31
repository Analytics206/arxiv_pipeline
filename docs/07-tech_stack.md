# Technical Stack

## Runtime baseline

| Area | Choice | Notes |
| --- | --- | --- |
| Python | 3.13 | Project constraint is `>=3.13,<3.14`; Python 3.14 is deferred until required packages support it cleanly |
| Dependency management | `pyproject.toml`, `uv.lock`, uv | Cross-platform locked environment |
| Containers | Docker Compose | Normal runtime/test images plus a narrow retired-embedding image |
| Host OS | Windows or Linux | Project-relative PDF paths avoid drive-letter coupling |

The normal environment supports the repository's pipelines, notebooks,
importers, monitoring, and LLM evaluation tools. Only retired embedding and
topic-model processes are isolated in the optional `legacy` extra.

## Core application stack

| Layer | Technology | Responsibility |
| --- | --- | --- |
| API | FastAPI, Uvicorn, Pydantic | REST/OpenAPI contracts and validation |
| Agent protocol | MCP Python SDK 1.28, HTTPX | Read-only MCP tools/resources over canonical GET operations |
| MongoDB access | PyMongo, Motor | Canonical metadata and analysis persistence |
| Vector access | Qdrant Client | Named dense/sparse indexing, weighted RRF, filters, and hybrid search |
| PDF parsing | PyMuPDF | Page-aware source extraction |
| Model client | Ollama Python client | Shared remote/local analysis and embeddings |
| Ingestion | aiohttp, Requests, Beautiful Soup | arXiv Atom and paper-page access |
| Configuration | PyYAML, python-dotenv | Versioned defaults plus environment overrides |
| Tests | pytest | Repository, contract, storage, and workflow regression tests |

## Data services

### MongoDB

MongoDB is canonical for:

- normalized latest-version arXiv paper metadata in `papers`;
- superseded version history in `papers_archive`;
- local PDF path, hash, validation, and processing state;
- complete immutable analysis documents;
- current-analysis pointers and model/prompt/schema provenance.

The API repository creates indexes for analysis identity, current-paper lookup,
and evidence IDs. Paper ingestion records schema `2.0` identity fields
(`base_arxiv_id`, versioned `arxiv_id`, and numeric `arxiv_version`);
`base_arxiv_id` is unique in `papers`, while
`(base_arxiv_id, arxiv_version)` is unique in `papers_archive`.

### Qdrant

`research_knowledge_hybrid_v1` is the active hybrid index. It stores independently
retrievable knowledge units such as:

- verified evidence passages;
- claims and reported findings;
- limitations;
- implementation ideas.

Points include paper URI, analysis identity, source page/evidence, knowledge
kind, and embedding provenance. Each point has a 1,024-dimensional dense vector
and a stable hashed sparse lexical vector. Qdrant applies IDF and weighted RRF;
the application performs final paper-diversity reranking, RRF agreement
normalization, thresholding, and coverage reporting. Implementation ideas keep
structured fields in payload while embedding only one canonical description.
Incomplete evidence spans are not indexed. The index is rebuildable from
MongoDB.

The dense component remains `mxbai-embed-large:latest`, selected after
comparison with Qwen3 Embedding 0.6B, EmbeddingGemma, and Nomic Embed Text
v1.5. Hybrid retrieval was separately evaluated against the dense-only
collection before promotion.

### Neo4j

Neo4j is installed as an optional `manual` service, not as an API dependency or
part of default startup. The historical author-paper-category graph remains
available for reference. A richer graph must pass the evaluation gate described
in the system design before it becomes part of agent retrieval.

## AI inference

The project does not run its own Ollama container. It calls the shared
`ai-services` instance using:

- `AI_SERVICES_HOST`
- `AI_SERVICES_DOCKER_HOST`
- `AI_SERVICES_OLLAMA_PORT`
- optional full `OLLAMA_URL`

The current defaults are:

| Task | Model | Hardware rationale |
| --- | --- | --- |
| Structured paper analysis | `qwen3.5:4b` | Compact enough for an 8 GB RTX 2070 Mobile with configured 12K context |
| Hybrid retrieval dense component | `mxbai-embed-large:latest` | Evaluated 1,024-dimensional model combined with sparse IDF retrieval |

Model names are configuration, not public-contract fields. Every analysis and
search hit records the actual model/version provenance.

## API and agent integration

FastAPI publishes:

- a capability document for tool discovery;
- an OpenAPI schema for generated clients and harness tools;
- curated-paper catalog, complete context, and deterministic token-budgeted
  context contracts;
- evaluated hybrid search with filters, explicit score semantics, normalized
  relevance, honest empty results, and corpus coverage;
- stable evidence lookup;
- health and interactive documentation.

REST/OpenAPI and MCP Streamable HTTP are the current cross-computer
integrations. The MCP server also supports stdio for local harnesses. The SDK
is constrained to `mcp>=1.28.1,<2`: v1 is the current stable production line,
while the breaking v2 release was still a release candidate when this adapter
was implemented.

## Web UI

The human workspace currently uses React 18, React Router, Axios, Bootstrap,
and Recharts. It provides:

- service health and curated-corpus status;
- semantic research search;
- paper and knowledge-kind filters;
- ranked evidence-aware results;
- complete paper context and provenance views;
- dynamic API hostname resolution for LAN access.

The production image builds static assets with Node and serves them on port
3000. The current Create React App/`react-scripts` toolchain is functional but
old; migrating it to Vite and current frontend dependencies is a planned
maintenance task because the build-stage dependency audit reports known
vulnerabilities.

## Container targets and profiles

### Python images

| Target | Contents | Consumers |
| --- | --- | --- |
| `runtime` | Core ingestion, PDF, database, API, retrieval, and Ollama clients | API, app, Mongo sync |
| `test` | Runtime plus pytest/dev tools | CI and container verification |
| `legacy` | Runtime plus retired topic-model and Hugging Face/Qdrant embedding dependencies | Historical embedding experiments only |

### Compose profiles

| Profile | Services |
| --- | --- |
| Default | `mongodb`, `qdrant`, `api`, `web-ui` |
| `manual` | `app`, `sync-mongodb`, `neo4j`, `sync-neo4j`, Jupyter, Kafka utilities |
| `legacy` | `legacy-runtime`, `sync-bertopic`, `sync-top2vec` |

## Retired embedding stack

The optional `legacy` extra contains only BERTopic, Top2Vec,
sentence-transformers, the old LangChain embedding adapters, and their
clustering dependencies. It exists for `sync-bertopic`, `sync-top2vec`, and the
archived topic-modeling experiments. The historical PDF-chunk Qdrant sync is
not exposed as a Compose service and is not part of the active retrieval path.

PyTorch, Transformers, NumPy/pandas, Jupyter, evaluation metrics, Kaggle tools,
PubMed support, Kafka, monitoring, and other project utilities are normal
dependencies because non-legacy code still uses them.

## Network configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `RESEARCH_API_BIND` | `0.0.0.0` | API host-interface binding |
| `RESEARCH_API_PORT` | `8000` | Published API port |
| `RESEARCH_MCP_BIND` | `0.0.0.0` | MCP host-interface binding |
| `RESEARCH_MCP_PORT` | `8001` | Published Streamable HTTP port |
| `RESEARCH_MCP_API_TIMEOUT` | `30` | REST request timeout in seconds |
| `RESEARCH_UI_BIND` | `0.0.0.0` | UI host-interface binding |
| `RESEARCH_UI_PORT` | `3000` | Published UI port |
| `CORS_ALLOWED_ORIGINS` | `*` | Trusted-LAN browser origins; replace with allowlist where appropriate |
| `ENABLE_LEGACY_CYPHER_API` | `false` | Opt-in arbitrary legacy Cypher route |
| `ENABLE_LEGACY_MUTATION_API` | `false` | Opt-in legacy mutation/debug route |

The defaults are suitable only for a trusted private LAN. Binding to
`127.0.0.1` restricts a service to the research host.

## Deliberate exclusions

- Python 3.14 package workarounds or source-build forcing;
- a second project-owned Ollama model cache;
- BERTopic/Top2Vec in the production path;
- Neo4j as an always-on dependency;
- Kafka for the current bounded single-host workload;
- direct public-Internet serving without a security layer.
