# [<img src="src/web-ui/public/images/drp_logo_blue.png" width="250"/>](src/web-ui/public/images/drp_logo_blue.png)
🧠 Deep Research Pipeline  
## Overview
A local, open-source research-intelligence system optimized for AI and coding
agents. It turns AI papers into structured, evidence-backed knowledge that an
agent can retrieve, cite, compare, and apply to software projects. Humans use
the same underlying research service through the web interface.

MongoDB is the source of truth for paper metadata and versioned analyses.
Qdrant provides the active rebuildable hybrid dense/lexical index. Neo4j is an optional
experiment and is no longer required by the API, UI, or processing workflow.
BERTopic and Top2Vec are retired from the active architecture and retained only
under the `legacy` profile. See
[`docs/14-agent_research_system_plan.md`](docs/14-agent_research_system_plan.md)
for the current product direction and phased implementation plan.

## 🚀 Key Features
| Feature                  | Description |
| ------------------------ |-------------|
| **Local-first** | Runs on personally controlled infrastructure and serves trusted computers on the LAN. |
| **Evidence-backed analysis** | Produces structured methods, findings, limitations, and implementation ideas with verified page quotes. |
| **ArXiv ingestion** | Fetches normalized metadata and exact PDF versions from configurable categories/date ranges. |
| **Canonical MongoDB storage** | Stores paper state and immutable, versioned analyses with full provenance. |
| **Agent hybrid retrieval** | Combines shared-Ollama embeddings, lexical IDF retrieval, weighted RRF, and paper-diversity reranking across separate evidence-backed and metadata-discovery tiers. |
| **Agent interfaces** | Publishes the same read-only capability, catalog, search, token-budgeted context, and evidence contracts through REST/OpenAPI and MCP. |
| **Human research workspace** | Searches the same curated knowledge and opens complete evidence-aware paper context. |
| **Reproducible containers** | Keeps only retired embedding/topic-modeling processes in an optional image. |
---

### Neo4j Graph Database
![alt text](<images/neo4j-graph.png>)
### Dashboard reporting
![alt text](<images/web-ui-home.png>)
### Qdrant Vector Database
![alt text](<images/qdrant-graph.png>)
### Qdrant Vector Database similarity search
![alt text](<images/qdrant-cluster.png>)
---

## 📦 System Components
| Component                  | Purpose                                      |
| -------------------------- | -------------------------------------------- |
| **Ingestion and PDF pipeline** | Fetches metadata, validates exact PDFs, analyzes, and indexes papers |
| **MongoDB** | Stores canonical metadata, PDF state, and versioned analyses |
| **Qdrant** | Stores separate rebuildable evidence-backed and paper-discovery dense/lexical indexes |
| **Shared Ollama** | Runs configurable analysis and embedding models from the separate `ai-services` project |
| **Research API** | Serves stable read-only REST/OpenAPI tools to UI and external agents |
| **MCP adapter** | Maps seven read-only research/discovery contracts and stable resources to MCP over Streamable HTTP or stdio |
| **Web UI** | Provides human semantic search, paper context, evidence, and provenance |
| **Neo4j** | Optional manual relationship experiment; not a default dependency |
| **Legacy embedding runtime** | Isolates only BERTopic, Top2Vec, and the historical Hugging Face/Qdrant embedding processes |

---
## 🧵 High Level Overview
 - Fetch metadata of papers from arXiv.org using arXiv Atom XML API
 - Store normalized metadata in MongoDB with pdf_url for pdf download
 - Download PDFs from arXiv.org and store in local directory
 - Create structured, page-cited analyses through shared Ollama
 - Store evidence, claims, limitations, and implementation ideas in Qdrant
 - Manage paper processing tracking in MongoDB
 - Dynamic configuration for paper category, paper limits, models, and pdf save directory
 - Serve the curated research through a read-only LAN API and human web UI
 - Keep Neo4j, topic modeling, notebooks, and monitoring as optional profiles
 - Tracks events, errors, and skipped entries  

For more deep dive into project and status, see the `docs/` directory.

---
## 💡 Use Cases
### Research & Knowledge Management
- **Build Personal Research Libraries**: Create customized collections of AI papers organized by category and relevance
- **Offline Semantic Paper Search**: Find relevant papers without relying on online search engines
- **Research Gap Identification**: Analyze research areas to identify unexplored topics and opportunities
- **Literature Review Automation**: Quickly build comprehensive literature reviews for specific research questions

### Data Science & Analysis
- **Research Trend Analysis**: Apply time-series analysis to identify emerging and declining research topics
- **Citation Impact Visualization**: Build network graphs to identify the most influential papers and authors
- **Cross-Domain Knowledge Transfer**: Discover applications of techniques across different research domains
- **Research Benchmarking**: Track performance improvements in specific algorithms or methods over time

### AI-Assisted Research
- **Model Metadata Viewer**: Explore and compare machine learning models from Hugging Face and Ollama in a unified interface
  - View detailed metadata for local and available models
  - Filter and search models by name, type, and capabilities
  - Compare model architectures and performance metrics
- **Paper Summarization**: Generate concise summaries of complex research papers
- **Similar Papers Discovery**: Use vector similarity to find related work not linked by citations
- **Research Idea Generation**: Use paper combinations with LLMs to explore novel research directions
- **Algorithm Implementation Assistance**: Extract mathematical models for implementation in your own projects
- **Research Agent**: Add specific research agents for specific use cases
- **Fine-tuning**: Fine-tune pipelines for specific use cases

### Education & Learning
- **Personalized Learning Paths**: Create sequential reading lists for specific AI topics
- **Concept Visualization**: Extract and visualize key concepts across multiple papers
- **Interactive Research Exploration**: Navigate research spaces through concept and citation graphs
- **Teaching Material Preparation**: Curate papers and extract examples for courses and tutorials
---

# 🛠️ Setup Instructions
  ### This system runs on a single machine but recommend a multiple machine setup.*
  - Current development machine: RTX 2070 Mobile with 8 GB VRAM
  - Qwen 3.5 4B is the default analysis model and
    `mxbai-embed-large:latest` is the initial dense-retrieval baseline
  - Stateless AI inference is provided by the shared `ai-services` project
    rather than an Ollama instance owned by this Compose stack
  - Most components run in docker containers that can be move to own/shared docker machines
  - Qdrant recommend setup on a separate machine with nvidia GPU for faster vector operations
  - Default Qdrant running locally with out docker *see below Qdrant Setup*
  - PDFs default to ignored project runtime storage under `data/pdfs`
  - Set `PDF_STORAGE_DIR` only when a larger external drive is actually needed
  * edit config/default.yaml before running the pipelines
  * Project works on both Windows and Ubuntu/Linux environments.

---
# ⚠️ Prerequisites
- Git
- Python 3.13
- [UV](https://github.com/astral-sh/uv) (for fast Python dependency management)
- A reachable shared `ai-services` Ollama server (required for paper analysis;
  optional for metadata-only ingestion)
- Docker and Docker Compose (for containerized deployment)
- NVIDIA GPU with CUDA support (optional, for faster vector operations)
- Prometheus and Grafana (included in docker-compose.monitoring.yml)

---
### Installation (Local)
* Note: installs all dependencies in a virtual environment 
## Linux/macOS/WSL:
```bash
# Make the setup script executable
chmod +x scripts/setup_uv.sh

# Install Python 3.13 and the locked project dependencies
./scripts/setup_uv.sh

# Activate the virtual environment
source .venv/bin/activate
```

## Windows (PowerShell):

### Recommended: build `.venv` from the lockfile

```powershell
# Install Python 3.13 and the locked project dependencies
.\scripts\setup_uv.ps1

# If PowerShell reports that running scripts is disabled, allow scripts only
# for this PowerShell process (the setting disappears when the window closes)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

### Manual: build or rebuild `.venv`

Use this when you want to recreate the environment yourself. The removal step
intentionally discards only the existing project `.venv`.

```powershell
# If needed, remove the existing project environment
Remove-Item -LiteralPath .venv -Recurse -Force

# Create .venv with Python 3.13
uv venv --python 3.13 .venv

# If PowerShell reports that running scripts is disabled
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install the exact locked dependencies for the supported pipelines and
# development tools
uv sync --python 3.13 --extra agent --extra dev --frozen
```

Both setup scripts install a uv-managed Python 3.13 runtime and synchronize
the supported pipelines and development tools from `uv.lock` into `.venv`.
The uv-managed environment intentionally does not need a separate `pip`
installation. Retired BERTopic, Top2Vec, and historical local-model workflows
are available only when explicitly requested with `--extra legacy`.

## Process a paper end to end (recommended)

The canonical agent-first process fetches exact arXiv metadata, downloads and
validates the versioned PDF, stores its portable path in MongoDB, creates an
evidence-backed analysis, and idempotently indexes it in Qdrant:

```powershell
# Create the consumer configuration once.
Copy-Item .env.example .env

# Start the persistent services. The app itself is an on-demand command.
docker compose up -d mongodb qdrant api mcp web-ui

# Process one exact paper version from arXiv through semantic search.
docker compose run --rm --no-deps app python -m src.pipeline.process_paper `
  --paper-id 2607.02134v1
```

PDFs are stored at
`data/pdfs/<primary-arxiv-category>/<versioned-arxiv-id>.pdf`. The entire
`data/` directory is ignored by Git and mounted at `/app/data` for project
containers, so the same relative location works on Windows and in Docker.

Rerunning the command is safe: existing PDFs are reused, a matching immutable
analysis skips model generation, and Qdrant receives the same stable point
identities. Useful overrides include:

```powershell
# Use another host directory without editing YAML.
$env:PDF_STORAGE_DIR = "D:\AI Research\arxiv-pdfs"

# Intentionally download or regenerate again.
docker compose run --rm --no-deps app python -m src.pipeline.process_paper `
  --paper-id 2607.02134v1 `
  --force-download `
  --force-analysis
```

When using an external directory, add an explicit Docker bind mount for that
directory or run the command from the host virtual environment. The portable
project-local default requires no extra mapping.

## Analyze an existing local PDF manually

Phase 1 accepts an explicit local PDF and uses the shared `ai-services` Ollama
server to create a versioned, page-cited analysis in MongoDB.

```powershell
# One-time fallback if ai-services is not configured to pull these models
docker exec ai-ollama ollama pull qwen3.5:4b
docker exec ai-ollama ollama pull mxbai-embed-large:latest

# Analyze one PDF. The paper ID can also be an arXiv abs/pdf URL.
python -m src.pipeline.summarize_paper `
  --paper-id 2504.18538v1 `
  --pdf "C:\path\to\2504.18538v1.pdf"
```

The 4B Q4 model is approximately 3.4 GB and the analyzer requests a 12K context,
which fits fully on the current 8 GB GPU. If that changes after a model or driver
upgrade, reduce `analysis.context_length` before changing models.

Measured on the RTX 2070 Mobile after a structured-output request:

| Model | Context | Offload | Total GPU memory in use |
| --- | ---: | ---: | ---: |
| `qwen3.5:4b` | 8,192 tested; 12,288 configured | 100% GPU | ~4.16 GB / 8 GB at 8K |

For Windows commands, `AI_SERVICES_HOST=localhost`. Project containers receive
`host.docker.internal` automatically. If Ollama moves to another computer, set
`AI_SERVICES_HOST` and `AI_SERVICES_DOCKER_HOST` to that machine's LAN or
Tailscale hostname; application code does not change.

The command is idempotent for the same document hash, schema, prompt, and
model. Add `--force` only when you intentionally want to rerun that exact
analysis.

With the API running, agents and the web UI can discover and read the canonical
research contracts:

```text
GET http://localhost:8000/research/capabilities
GET http://localhost:8000/research/papers?limit=20
GET http://localhost:8000/research/papers/agent-context?paper_id=2504.18538
GET http://localhost:8000/research/papers/context-package?paper_id=2504.18538&profile=standard
GET http://localhost:8000/research/papers/context-package?paper_id=2504.18538&token_budget=2500
GET http://localhost:8000/research/papers/analysis?paper_id=2504.18538
GET http://localhost:8000/research/evidence/<evidence-id>
GET http://localhost:8000/openapi.json
```

Use `agent-context` when a human or large-context process needs the complete
canonical analysis. Agent harnesses should normally use `context-package`.
Its `brief`, `standard`, and `deep` profiles target 1,500, 4,000, and 8,000
estimated JSON tokens; `token_budget` accepts a custom 512-32,768 budget.
Every package reports the estimator, realized estimate, selection policy,
included/omitted counts, and whether it was truncated. Claims and
implementation ideas are included only with all of their verified evidence
records. The provider-neutral estimator is intentionally approximate, so a
harness can perform an exact final count with its target model tokenizer. If a
custom budget cannot hold the mandatory TLDR, evidence, and provenance, the API
returns 422 with the minimum estimated budget for that paper.

An AI harness can generate tools from `/openapi.json` or connect to the MCP
adapter at `http://<research-host>:8001/mcp`. MCP exposes the same five names:

- `search_research`
- `list_curated_papers`
- `get_paper_context`
- `get_paper_context_package`
- `get_evidence`

Every MCP tool advertises `readOnlyHint=true`, `destructiveHint=false`, and
`idempotentHint=true`. The adapter has no MongoDB or Qdrant credentials and
calls only the canonical GET-only research API.

For a network-capable MCP harness, configure the Streamable HTTP URL:

```json
{
  "mcpServers": {
    "arxiv-research": {
      "type": "http",
      "url": "http://<research-host>:8001/mcp"
    }
  }
}
```

For a local stdio client, run the same server without publishing a port:

```json
{
  "mcpServers": {
    "arxiv-research": {
      "command": "C:\\path\\to\\arxiv_pipeline\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "src.mcp_server.server",
        "--transport",
        "stdio"
      ],
      "cwd": "C:\\path\\to\\arxiv_pipeline",
      "env": {
        "RESEARCH_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

Client configuration field names vary slightly by harness, but the command,
environment variable, and MCP URL are transport-standard inputs.

The complete cross-computer handoff for the separate AI harness project,
including architecture, agent usage guidance, firewall diagnostics, and a
standalone test with observed data, is
[`docs/15-external_ai_harness_mcp_handoff.md`](docs/15-external_ai_harness_mcp_handoff.md).

Validate a running Streamable HTTP adapter end to end:

```powershell
python -m src.pipeline.validate_mcp `
  --url http://localhost:8001/mcp `
  --paper-id 2607.02134
```

Evaluate package invariants over the current corpus:

```powershell
python -m src.pipeline.evaluate_context_packages
```

This checks budget compliance, evidence closure, deterministic output,
provenance retention, and monotonic selection across all three profiles. The
default detailed report is written to
`data/context_evals/agent_context_packages_v1.json`.

Index the newest canonical analysis in the agent-facing research collection:

```powershell
docker compose run --rm --no-deps app python -m src.pipeline.index_research `
  --paper-id 2504.18538v1
```

The command uses shared Ollama for embeddings and idempotently upserts
page-cited evidence, claims, and implementation ideas into
`research_knowledge_hybrid_v1`. MongoDB remains the source of truth; this Qdrant
collection can be rebuilt. Changing the embedding model requires a new
versioned collection name because vector dimensions and embedding spaces are
not interchangeable.

Search from an agent, browser, or PowerShell:

```text
GET http://localhost:8000/research/search?query=How%20does%20the%20harness%20record%20RL%20training%20data%3F&limit=8
GET http://localhost:8000/research/search?query=lightweight%20GUI%20containers&paper_id=2607.21557&kind=implementation_idea
```

Every hit includes its stable paper URI, analysis/model provenance, evidence
IDs, exact quotes, and source pages. `retrieval_mode` identifies dense versus
hybrid retrieval, and `score_semantics` distinguishes cosine similarity from
RRF rank scores. Hybrid responses also include:

- `relevance`, a normalized 0-1 retriever-agreement signal on every hit;
- `score_calibration`, including the raw RRF floor/ceiling and its meaning;
- `result_status=matches|no_match` plus `no_match_reason`;
- indexed and filter-eligible paper/point counts under `coverage`.

The default `min_relevance=0.05` removes single-retriever nearest-neighbor
leftovers. Pass `min_relevance=0` only when intentionally inspecting every
candidate. RRF and normalized relevance are ranking/agreement signals, not
probabilities that a result is topically applicable.

Evidence lookup returns a complete sentence-aware `quote`, the original exact
`supporting_quote`, and `truncated`. Search and normal context packages exclude
records marked truncated. Implementation-idea hits expose their title,
description, agent use, expected benefit, and risks under
`implementation_idea`; the indexed `text` contains only one canonical
description.

Repair and reindex existing canonical analyses after upgrading an older corpus:

```powershell
docker compose run --rm --no-deps app python -m src.pipeline.repair_research_quality `
  --config /app/config/default.yaml
```

Use `--dry-run` first to validate PDF hashes and inspect the proposed corpus
repair without writing MongoDB or Qdrant.

### Evaluate retrieval and embedding models

The reviewed retrieval suite covers 38 coding-agent questions across five
immutable paper analyses, including paper-scoped paraphrases, corpus discovery,
cross-paper synthesis, and unanswerable controls. The benchmark validates its
document hashes and evidence judgments, then indexes each embedding model into
an isolated Qdrant collection using that model's documented query/document
format.

Ensure these exact tags are installed in the shared Ollama service:

```powershell
docker exec ai-ollama ollama pull mxbai-embed-large:latest
docker exec ai-ollama ollama pull qwen3-embedding:0.6b
docker exec ai-ollama ollama pull embeddinggemma:latest
docker exec ai-ollama ollama pull nomic-embed-text:v1.5
```

Add the same exact tags to the `ai-services` project's
`OLLAMA_PULL_MODELS` setting if they should be restored automatically on a new
machine or fresh Ollama volume.

Run or resume the complete comparison:

```powershell
docker compose run --rm --no-deps app `
  python -m src.pipeline.benchmark_embeddings `
  --resume `
  --summary-only
```

The detailed runtime report is saved under
`data/retrieval_evals/embedding_benchmark_v2.json`. The July 2026 result keeps
`mxbai-embed-large:latest` in production and identifies Nomic v1.5 as the best
small/fast fallback. See
[`docs/evaluations/embedding_benchmark_v2.md`](docs/evaluations/embedding_benchmark_v2.md)
for the model metrics and limitations.

Evaluate the promoted hybrid retrieval strategy against the dense baseline:

```powershell
docker compose run --rm --no-deps app `
  python -m src.pipeline.benchmark_retrieval_strategies `
  --skip-index `
  --summary-only
```

The selected strategy combines hashed lexical IDF retrieval with the existing
dense embedding, weighted RRF, and paper-diversity reranking. It recovered all
reviewed evidence groups within the default top eight. See
[`docs/evaluations/hybrid_retrieval_v1.md`](docs/evaluations/hybrid_retrieval_v1.md)
for the design, results, and exact target ranks.

## Use the research service across a trusted LAN

The API and UI publish on all host interfaces by default:

```powershell
Copy-Item .env.example .env
docker compose up -d mongodb qdrant api mcp web-ui

# Find the research computer's IPv4 address on Windows.
ipconfig
```

From another computer on the same network, open:

```text
Human workspace: http://<research-host-ip>:3000
API docs:        http://<research-host-ip>:8000/docs
OpenAPI:         http://<research-host-ip>:8000/openapi.json
MCP:             http://<research-host-ip>:8001/mcp
Health:          http://<research-host-ip>:8000/health
```

The UI uses the browser hostname to locate port 8000, so no frontend rebuild is
needed for a different LAN address. If another computer cannot connect, allow
inbound TCP 3000 and 8000 in the research host's firewall.

This configuration assumes a trusted private LAN. Do not forward these ports to
the public Internet. For local-only use, set both bind variables in `.env` to
`127.0.0.1`. For remote use, prefer a private VPN/Tailscale; add authentication,
authorization, TLS, and rate limiting before serving an untrusted network.

When running the analyzer through the `app` container, place the PDF below the
project `data/` directory and use its container path:

```powershell
docker compose run --rm app python -m src.pipeline.summarize_paper `
  --paper-id 2504.18538v1 `
  --pdf /app/data/2504.18538v1.pdf
```

# Dockerized Deployment - Docker Desktop Running
## 0. Suggested run in venv from scripts above for your operating system

## 1. **Build and start persistent services:**
   ```bash
    docker compose up -d mongodb qdrant api mcp web-ui
    # or to rebuild
    docker compose up -d --build
   ```
The `app` and bulk synchronization services are on-demand commands and do not
start as background services.

## 2. Managing Pipeline Service Containers
   * pipelines do not have to run in order if you have previously run them or starting where you left off
   * recommended to run them in order for processing new papers
   * manual services (Jupyter, Kafka, etc.) are only started when needed with the `--profile manual` flag
   
  ### a. Download arXiv dataset from Kaggle (optional):
  
  The pipeline includes a script to download the complete arXiv dataset from Kaggle. This is useful for bulk processing or offline analysis.
  
  #### Prerequisites
  The official `kaggle` client is included in the normal project environment;
  do not install a separate package for this command.

  1. Set up Kaggle credentials:
     - Create a `secure` directory in your project root (if it doesn't exist)
     - Copy `kaggle.json.example` to `secure/kaggle.json`
     - Update the file with your Kaggle API credentials:
       ```json
       {
           "username": "your_kaggle_username",
           "key": "your_kaggle_api_key"
       }
       ```

  #### Usage
  ```bash
  # Basic usage with default settings
  python -m src.pipeline.download_kaggle_arxiv
  
  # Override download path (optional)
  python -m src.pipeline.download_kaggle_arxiv --path "C:\Users\mad_p\Downloads"
  ```
  
  #### Configuration
  The downloader can be configured in `config/default.yaml`:
  ```yaml
  kaggle:
    dataset: "Cornell-University/arxiv"
    download_path: "X:/kaggle_arxiv"
    credentials:
      path: "secure/kaggle.json"
    logging:
      level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  ```
  > **Note**: The `secure` directory is in `.gitignore` to protect your credentials.

  ### b. Prepare a full Kaggle import for discovery

  The post-import workflow retains exact configured categories, validates and
  atomically replaces the MongoDB production collection, then resumably builds
  a separate metadata-only Qdrant index:

  ```powershell
  # Read-only count and retention preview
  python -m src.pipeline.prepare_kaggle_corpus

  # Cleanup plus complete discovery index and alias activation
  python -m src.pipeline.prepare_kaggle_corpus --apply --index
  ```

  See
  [`docs/16-kaggle_discovery_workflow.md`](docs/16-kaggle_discovery_workflow.md)
  for guardrails, staging imports, Docker usage, query tiers, and evaluation.

  ### Bulk agent-first test workflow

  This is the ordered multi-paper equivalent of `process_paper`. Each command
  is idempotent and can be rerun after an interruption:

  ```powershell
  # Build the small agent/API/MCP/ingestion runtime.
  docker compose build api
  docker compose up -d mongodb qdrant api mcp web-ui

  # 1. Upsert the configured arXiv category pages into MongoDB. The command
  # finishes by retaining the latest version in papers and moving older
  # versions into papers_archive.
  docker compose run --rm --no-deps sync-mongodb

  # 2. Download, validate, hash, and record the configured PDF corpus.
  docker compose run --rm --no-deps app python -m src.utils.download_pdfs `
    --config /app/config/default.yaml

  # 3. Preview the next batch. Exact analyses already completed with the
  # configured PDF hash, schema, prompt, and model are skipped.
  docker compose run --rm --no-deps app `
    python -m src.pipeline.process_downloaded_papers `
    --config /app/config/default.yaml `
    --dry-run

  # 4. Analyze and index the next bounded cross-category batch.
  docker compose run --rm --no-deps app `
    python -m src.pipeline.process_downloaded_papers `
    --config /app/config/default.yaml
  ```

  Use `--dry-run` on either PDF/batch command to inspect its exact manifest
  without writing anything. `pdf_storage.papers_per_category` bounds the
  downloaded corpus; `research_processing.papers_per_category` separately
  bounds expensive local-model analysis. The default of one per category is a
  three-paper sequential batch on the 8 GB GPU. Repeat the command to advance
  the queue, or use `--limit-per-category 2` for up to six papers. Papers run
  sequentially inside the batch rather than competing for GPU memory.

  Paper metadata uses schema 2.0. `papers` is keyed uniquely by
  `base_arxiv_id` and contains only the latest observed arXiv version;
  `papers_archive` retains superseded versions keyed by base ID and numeric
  version. The import command enforces this invariant after all categories
  finish. To inspect or rerun that cleanup independently:

  ```powershell
  # Report the expected move without changing MongoDB.
  docker compose run --rm --no-deps app `
    python -m src.pipeline.cleanup_paper_versions `
    --config /app/config/default.yaml

  # Archive older versions and normalize the current collection.
  docker compose run --rm --no-deps app `
    python -m src.pipeline.cleanup_paper_versions `
    --config /app/config/default.yaml `
    --apply
  ```

  A paper is skipped only when its PDF hash, analysis schema, prompt version,
  and model match a stored analysis. Failed or changed analyses remain eligible
  on the next run. `--force-analysis` intentionally includes matching papers
  and starts again from the newest paper in each category.

  ### Legacy enrichment workflows (optional)

  These commands support only the older topic/embedding experiments. They are not
  required by agent context or the `research_knowledge_hybrid_v1` index. Build the
  separate legacy image once before running BERTopic, Top2Vec, or the old
  Qdrant experiment:

  ```powershell
  docker compose --profile legacy build legacy-runtime
  ```

  The legacy image adds only BERTopic, Top2Vec, sentence-transformers,
  LangChain embedding adapters, and their clustering dependencies. Notebooks,
  evaluation tools, importers, monitoring, and general data utilities are part
  of the normal project environment.

  ### a. Run sync-neo4j pipeline for new metadata inserted in MongoDB:
  ```bash
   docker compose --profile manual run --rm sync-neo4j
  ```

  ### b. Run sync-bertopic pipeline for topic creation from paper summaries from mongodb:
  ```bash
   docker compose --profile legacy run --rm sync-bertopic
  ```
  ### c. Run sync-top2vec pipeline for topic creation from paper summaries from mongodb:
  ```bash
   docker compose --profile legacy run --rm sync-top2vec
  ```

   ### d. Legacy PDF/image Qdrant experiment:
   ```bash
   docker compose --profile legacy run --rm sync-qdrant
   ```
## 3. (optional) Managing Monitoring Containers with Prometheus & Grafana
a. **Start the monitoring stack:**
   ```bash
   docker compose -f docker-compose.monitoring.yml up -d
   ```
  or
  **For monitoring containers, use the monitoring compose file:**
  ```bash
  # Start Prometheus
  docker compose -f docker-compose.monitoring.yml start prometheus
  # Start Grafana
  docker compose -f docker-compose.monitoring.yml start grafana
  # View Grafana logs
  docker compose -f docker-compose.monitoring.yml logs grafana
  ```
b. **Access monitoring services:**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3001 (default login: admin/password)

c. **Explore metrics** for:
   - System resources
   - Docker containers
   - MongoDB performance
   - Application-specific metrics

d. **Monitoring Dashboards**
   Pre-configured Grafana dashboards are available in the repository:
   - `config/grafana/dashboards/basic_test_dashboard.json` - Basic connectivity testing dashboard
   - `config/grafana/dashboards/arxiv_data_science_dashboard.json` - Core monitoring for ArXiv pipeline
   - `config/grafana/dashboards/arxiv_advanced_analytics_dashboard.json` - Advanced system correlation metrics
   - `config/grafana/dashboards/arxiv_vector_embedding_dashboard.json` - Vector database performance metrics

   * These dashboards provide visualization for MongoDB operations, system resources, container performance, 
   and vector embedding generation metrics critical for the research paper processing pipeline.

e. **Prometheus Query Documentation**
   Comprehensive documentation for Prometheus queries is available in:
   - `docs/prometheus_basic_queries.md` - Simple queries for troubleshooting
   - `docs/prometheus_queries.md` - General purpose monitoring queries
   - `docs/prometheus_custom_queries.md` - ArXiv pipeline specific metrics
   - `docs/prometheus_working_queries.md` - Verified working queries for dashboards

f. **Monitoring Diagnostics**
   Use the diagnostic script to verify your monitoring setup:
   ```bash
   python scripts/check_prometheus_metrics.py
   ```
   * This script analyzes your Prometheus setup and verifies that critical metrics
   for the ArXiv pipeline are available and functioning correctly.

* Refer to `docs/grafana_dashboard_guide.md` for details on customizing and extending these dashboards.**

## 4. Managing Manual Services

The following services are configured with the `manual` profile in Docker Compose, which means they will only start when explicitly requested:

### a. Jupyter Notebooks for Data Analysis
```bash
# Build and start the project-owned Python 3.13 notebook image. It uses the
# normal project environment.
docker compose --profile manual up jupyter-scipy
# Stop Jupyter SciPy notebook server
docker compose --profile manual down jupyter-scipy
```
* Access at: http://localhost:8888 (check console for token)
* Note: If token access is lost, restart the Jupyter docker container to get a new token

### b. Kafka Messaging System
```bash
# Start Kafka with required Zookeeper service
docker compose --profile manual up zookeeper kafka
# Stop Kafka and Zookeeper services
docker compose --profile manual down zookeeper kafka
```
* Kafka broker accessible at: localhost:9092 (from host) or kafka:9092 (from other containers)

### c. Kafka UI Management Interface
```bash
# Start complete Kafka stack with UI
docker compose --profile manual up zookeeper kafka kafka-ui
# Stop complete Kafka stack
docker compose --profile manual down zookeeper kafka kafka-ui
```
* Access Kafka UI at: http://localhost:8080

## 5. Database Connection Settings
```yaml
mongo:
  connection_string: "mongodb://mongodb:27017/" # or http://localhost:27017
  db_name: "arxiv_papers"
  
neo4j:
  url: "bolt://neo4j:7687"  # or http://localhost:7474
  user: "neo4j"
  password: "password"

qdrant:
  url: "http://localhost:6333" #Access Qdrant UI http://localhost:6333/dashboard
  collection_name: "arxiv_papers"

# Qdrant API Metrics
# The database dashboard displays the following Qdrant metrics:
# - Papers: Number of vector embeddings stored in Qdrant (paper count)
# - Authors: Vector dimensions (typically 768 for research paper embeddings)
# - Categories: Number of collections in Qdrant
  vector_size: 768  # For all-MiniLM-L6-v2 model
```
## 6. Web UI
* Start or rebuild the research workspace:
   ```bash
   docker compose up -d --build web-ui
   ```
* Open `http://localhost:3000` on the host or
  `http://<research-host-ip>:3000` on another trusted LAN computer.

### Web UI Development Setup

The current UI uses React and calls only the research API for its active
workspace. It does not connect directly to MongoDB, Qdrant, or Neo4j.

a. **Navigate to the web-ui directory**:
   ```bash
   cd src/web-ui
   ```

b. **Install the locked frontend dependencies**:
   ```bash
   npm ci
   ```
c. **Start the development server**:
   ```bash
   npm start
   ```
When running locally, it uses `http://localhost:8000`. From another computer,
it derives `http://<browser-hostname>:8000`.

## 7. Data Visualization and Analysis Dashboards

### Paper Analysis Dashboard
The ArXiv Pipeline includes an interactive Paper Analysis Dashboard that provides visual insights into publication trends and patterns. This dashboard is accessible through the MongoDB Reports section of the web interface.

**Key Features:**
- **Time-based Analysis**: View paper publication trends by year, month, or day
- **Multi-dimensional Filtering**: Filter papers by date range, specific year, and research category
- **Dynamic Category Selection**: Choose from the top 50 research categories in your collection
- **Interactive Charts**: Toggle between different time granularities with responsive visualizations
- **Formatted Metrics**: Clear display of total papers with proper numerical formatting

**How to Access:**
1. Navigate to the web UI (http://localhost:3000) when services are running
2. Click on "MongoDB Reports" in the navigation menu
3. Use the filter options to refine your analysis

![Paper Analysis Dashboard](<images/paper_analysis_dashboard.png>)

## 8. Data Validation and Analysis Utilities

The ArXiv Pipeline includes comprehensive data validation and analysis utilities in `src/agents_core/logging_utils.py`. These utilities help ensure data quality, perform temporal analysis, and validate MongoDB collections.

### Paper Schema Validation
```python
from src.agents_core.logging_utils import validate_paper_schema

# Validate a paper document
is_valid, errors = validate_paper_schema(paper_document)
if not is_valid:
    print(f"Paper validation failed with errors: {errors}")
```

### Temporal Analysis
```python
from src.agents_core.logging_utils import count_papers_by_date
from src.storage.mongo import MongoStorage

# Connect to MongoDB
with MongoStorage() as mongo:
    # Count papers by year
    yearly_counts = count_papers_by_date(mongo.papers, date_field="published", group_by="year")
    
    # Count papers by month
    monthly_counts = count_papers_by_date(mongo.papers, date_field="published", group_by="month")
    
    # Count papers by day of week
    weekday_counts = count_papers_by_date(mongo.papers, date_field="published", group_by="weekday")
```

### MongoDB Collection Analysis
```python
from src.agents_core.logging_utils import analyze_mongodb_collection, validate_mongodb_data
from src.storage.mongo import MongoStorage

# Connect to MongoDB
with MongoStorage() as mongo:
    # Analyze collection structure
    analysis = analyze_mongodb_collection(mongo.papers)
    
    # Validate collection data
    validation_results = validate_mongodb_data(mongo.papers, validate_paper_schema)
```

### Data Integrity Checking
```python
from src.agents_core.logging_utils import check_data_integrity
from src.storage.mongo import MongoStorage

# Connect to MongoDB
with MongoStorage() as mongo:
    # Check data integrity with date range
    integrity_results = check_data_integrity(
        mongo.papers, 
        date_range=("2024-01-01T00:00:00Z", "2025-12-31T23:59:59Z")
    )
```

### Formatted Reports
```python
from src.agents_core.logging_utils import generate_date_distribution_report, count_papers_by_date
from src.storage.mongo import MongoStorage

# Connect to MongoDB
with MongoStorage() as mongo:
    # Generate monthly report
    monthly_counts = count_papers_by_date(mongo.papers, group_by="month")
    report = generate_date_distribution_report(monthly_counts, title="Monthly Paper Distribution")
    print(report)
```

These utilities help maintain data quality and provide insights into the ArXiv paper collection. They can be used for monitoring, debugging, and generating reports.

## 9. Managing Individual Docker Containers
* For more fine-grained control over system components, you can start, stop, restart, and inspect specific containers:

### a. Starting Individual Required Containers
* Services: 
```bash
# Start MongoDB
docker compose start mongodb
# Start Neo4j
docker compose start neo4j
# Start Qdrant
docker compose start qdrant
# Start Web UI
docker compose start web-ui
# Start API
docker compose start api
# Start APP
docker compose start app
```

### b. Restarting Individual Containers
```bash
# Restart MongoDB
docker compose restart mongodb
# Restart Neo4j
docker compose restart neo4j
# Restart Qdrant
docker compose restart qdrant
# Restart Web UI
docker compose restart web-ui
```

### c. Viewing Container Logs

```bash

# View MongoDB logs
docker compose logs mongodb
# View Neo4j logs
docker compose logs neo4j
# View Qdrant logs
docker compose logs qdrant
# View Web UI logs
docker compose logs web-ui
# Follow logs (real-time updates)
docker compose logs --follow mongodb
```

### d. Inspecting Container Status
```bash
# Check status of all containers

docker compose ps

# Detailed information about a specific container

docker inspect arxiv_pipeline-mongodb-1
```

## 6. Optional: GPU-Accelerated Qdrant Setup on Remote Windows Machine
* For enhanced vector search performance, you can set up Qdrant with GPU acceleration on a separate Windows machine within the same network. This configuration is beneficial for:
- Processing large volumes of papers with faster embedding searches
- Leveraging dedicated GPU resources for vector operations
- Scaling the vector database independently from other components

### Quick Overview
a. **Hardware Requirements**:
   - Windows 11 with WSL2 enabled
   - NVIDIA GPU with CUDA 12.x support (8GB VRAM minimum)
   - 16GB RAM (32GB recommended)
   - IP address on your local network


b. **Setup Approach**:
   - Install WSL2 with Ubuntu
   - Configure CUDA in WSL2
   - Build Qdrant from source with GPU support
   - Configure for optimal performance with research paper embeddings


c. **Integration with ArXiv Pipeline**:
   - After setup, update the Qdrant connection settings in your config/default.yaml
   - Run the pipeline as usual, with vector operations now GPU-accelerated

### Detailed Instructions

* Complete step-by-step instructions are available in the `qdrant_setup` directory:

```bash

# View the detailed setup guide

cat qdrant_setup/README.md

```

#### The guide includes:
- Full installation procedures
- Configuration optimized for 768-dimensional embeddings (typical for research papers)
- Testing and benchmarking tools
- Maintenance and backup procedures
- Security recommendations

## Updating Configuration

* After setting up GPU-accelerated Qdrant, update your configuration:

```yaml

# In config/default.yaml

qdrant:
  host: "192.168.1.x"  # Replace with your Qdrant server's IP
  port: 6333
  collection_name: "arxiv_papers"

```

* **New Feature:** The sync_qdrant pipeline now includes **MongoDB tracking** to prevent duplicate processing of PDFs. Each processed PDF is recorded in the `vector_processed_pdfs` collection with metadata including file hash, processing date, and chunk count.

---

### Configuration
![Image](https://github.com/user-attachments/assets/7d68b38e-b4a1-49d9-acf4-17b74fb05e22)

The application is configured using YAML files in the `config/` directory. The default configuration is in `config/default.yaml`.

Key configuration options:

## Recent Feature Additions
### 1. MongoDB Tracking for Qdrant Vector Processing
* The sync_qdrant pipeline now includes a tracking system to prevent duplicate processing and provide synchronization with Qdrant:

```yaml

# In config/default.yaml

qdrant:
  # ... other settings ...

  tracking:
    enabled: true # Whether to track processed PDFs

    collection_name: "vector_processed_pdfs" # MongoDB collection to store tracking information

    sync_with_qdrant: true # Whether to sync tracking with actual Qdrant contents

```

### This system:
- Tracks each processed PDF in a MongoDB collection
- Prevents duplicate processing of the same document
- Stores metadata including file hash, processing date, and chunk count
- Maintains consistency between MongoDB tracking and Qdrant vector storage

### 2. GPU Acceleration for Vector Operations

The pipeline now supports GPU acceleration for both:

#### A. Qdrant Vector Database

```yaml
# In config/default.yaml
qdrant:
  # ... other settings ...
  gpu_enabled: true # Enable GPU for vector operations
  gpu_device: 1 # GPU device index (0 for first GPU, 1 for second, etc.)
```

#### B. Standalone Qdrant with GPU
For better performance with large vector collections, you can run Qdrant as a standalone application with GPU support as documented in the "Qdrant Deployment Options" section.

---

## Shared Ollama integration

This project is an `ai-services` consumer and does not run its own Ollama
container. Paper analysis uses Ollama structured output, while `sync_qdrant`
can send extracted diagrams to the same vision-capable model.

- Default model: `qwen3.5:4b`
- Native API: `http://<AI_SERVICES_HOST>:<AI_SERVICES_OLLAMA_PORT>`
- Windows default: `http://localhost:11434`
- Container default: `http://host.docker.internal:11434`
- Full URL override: `OLLAMA_URL`

Metadata ingestion still works while Ollama is unavailable. Paper analysis
requires it; diagram descriptions fall back to placeholders.

Do not run the native Windows Ollama app on the same port as `ai-ollama`.
Otherwise Windows and project containers can reach different model stores even
though both URLs appear to use port 11434.

## ArXiv Pipeline Configuration Settings
The system is configured through `config/default.yaml`. Key configuration sections included

### Portable PDF paths in Docker

The project uses one storage tree rather than separate host and container
drive-letter settings:

```yaml

volumes:
  - ./data:/app/data
```

This means:

- Host path: `<project>/data/pdfs`
- Application-container path: `/app/data/pdfs`
- Jupyter path: `/home/jovyan/work/data/pdfs`
- MongoDB stores a portable relative path such as
  `data/pdfs/cs.AI/2607.02134v1.pdf`

Set `PDF_STORAGE_DIR` to override `pdf_storage.directory`. An external absolute
host path also needs a corresponding Docker bind mount; the project-local
default does not.
   ## sync_mongodb pipeline
   - arxiv.categories: Research categories to fetch papers from api into mongodb
   - arxiv.max_results: Number of papers to fetch per API call
   - arxiv.rate_limit_seconds: Number of seconds to wait between API calls
   - arxiv.max_iterations: Number of API calls per category
   - arxiv.start_date: Only process papers published after this date
   - arxiv.end_date: Only process papers published before this date

   ## sync_neo4j pipeline
   - arxiv.process_categories: Categories to prioritize for vector storage into qdrant
   - arxiv.max_papers: Maximum number of papers to process
   - arxiv.max_papers_per_category: Maximum number of papers to insert per category
   - arxiv.sort_by: Sort papers by this field
   - arxiv.sort_order: Sort papers in this order

   ## sync_qdrant pipeline
   - arxiv.max_papers: Maximum number of papers to process
   - arxiv.max_papers_per_category: Maximum number of papers to insert per category
   - arxiv.sort_by: Sort papers by this field
   - arxiv.sort_order: Sort papers in this order

   ## download_pdfs pipeline
   - pdf_storage.process_categories: Categories to select from MongoDB
   - pdf_storage.papers_per_category: Maximum unique papers selected per category
   - pdf_storage.request_interval_seconds: Delay between new arXiv PDF requests
   - pdf_storage.download_date_filter: Published-date range and sorting

   ## process_downloaded_papers pipeline
   - research_processing.process_categories: Categories represented in the agent test
   - research_processing.papers_per_category: Maximum analyses selected per category
   - The command requires a recorded `local_pdf_path`, skips matching immutable
     analyses, and idempotently indexes stable points in
     `research_knowledge_hybrid_v1`

Mounted `config/` changes apply to on-demand commands immediately. Restart
persistent services after changing settings they consume. See
`docs/06-system_design.md` for configuration impact.

## 🔍 Project Analysis
The project includes a metadata generator in the `dev_utils` directory that helps analyze and document the codebase structure. This tool is particularly useful for understanding module dependencies and system architecture.

### Generating System Metadata
```bash
# Generate metadata for the entire project (saved to dev_utils/system_metadata.yaml by default)
python -m dev_utils.metadata_generator .

# Generate metadata for a specific module (e.g., llm_eval)
python -m dev_utils.metadata_generator src/llm_eval -o dev_utils/llm_eval_metadata.yaml
```

### Metadata Includes
- Complete module structure and dependencies
- Function and class definitions
- Entry points and their relationships
- External library dependencies
- Code documentation strings

### Usage Examples
1. **Documentation Generation**:
   ```bash
   # Generate comprehensive project documentation
   python -m dev_utils.metadata_generator . -o docs/system_architecture.yaml
   ```

2. **Dependency Analysis**:
   ```bash
   # Analyze dependencies for a specific component
   python -m dev_utils.metadata_generator src/ingestion -o ingestion_dependencies.yaml
   ```

For more detailed documentation and advanced usage, see the [dev_utils/README.md](dev_utils/README.md) file.

The generated YAML files can be used for:
- System architecture visualization
- Codebase documentation
- Dependency analysis
- Onboarding new developers
- Code quality assessment

## Qdrant Deployment Options
This pipeline supports two options for running Qdrant (vector database):

### Option 1: Running Qdrant in Docker (Default)

In the `docker-compose.yml` file, we provide a pre-configured Qdrant container:

```yaml
qdrant:
  image: qdrant/qdrant:latest
  ports:
    - "6333:6333"
    - "6334:6334"
  volumes:
    - qdrant_data:/qdrant/storage
  restart: unless-stopped
```

### Option 2: Running Qdrant Locally with GPU Support

For better performance with large vector collections, you can run Qdrant as a standalone application with GPU acceleration:

1. **Download Qdrant** from [GitHub Releases](https://github.com/qdrant/qdrant/releases)
2. **Create a config file** at `config/qdrant_config.yaml` with GPU settings:

```yaml
storage:
  # Path to the directory where collections will be stored
  storage_path: ./storage
  # Vector data configuration with GPU support
  vector_data:
    # Enable CUDA support
    enable_cuda: true
    # GPU device index (0 for first GPU, 1 for second, etc.)
    cuda_device: 0
```

3. **Run Qdrant with the config**:
```
qdrant.exe --config-path config/qdrant_config.yaml
```

4. **Update the docker-compose.yml file** to comment out the Qdrant service but keep other services:
```yaml
# Comment out the Qdrant service
#qdrant:
#  image: qdrant/qdrant:latest
#  ...
# Update service connections to use host.docker.internal
app:
  environment:
    - QDRANT_URL=http://host.docker.internal:6333
```

## GPU Support for Embeddings Generation
* The pipeline can use GPU acceleration for generating embeddings in the `sync_qdrant.py` script:

1. **Use the locked PyTorch installation from the normal project setup.**
   Check GPU visibility with `nvidia-smi`; do not replace project packages with
   an ad hoc pip installation.

2. **Enable GPU in configuration**:
```yaml
# In config/default.yaml
qdrant:
  gpu_enabled: true  # Enable GPU for vector operations
  gpu_device: 0      # GPU device index (0 for first GPU)
```

3. **Verify GPU detection** by checking script output when running:
```

Using GPU for embeddings: cuda:0

```
## Database Installation & Connection Settings
### MongoDB Installation
#### Option 1: With Docker (recommended)
The Docker setup includes MongoDB, so no additional installation is needed if using Docker Compose.
#### Option 2: Standalone MongoDB Installation
1. **Download MongoDB Community Server**: [https://www.mongodb.com/try/download/community](https://www.mongodb.com/try/download/community)
2. **Use the PyMongo driver included by the normal project setup.**

3. **Test your connection**:
   ```python
   from pymongo import MongoClient
   client = MongoClient('mongodb://localhost:27017/')
   db = client['arxiv_papers']
   print(f"Connected to MongoDB: {client.server_info()['version']}")
   ```

### Neo4j Installation
#### Option 1: With Docker (recommended)
* The Docker setup includes Neo4j, so no additional installation is needed if using Docker Compose.
* Neo4j Desktop is recommended for local development and data exploration.

#### Option 2: Standalone Neo4j Installation
1. **Download Neo4j Desktop**: [https://neo4j.com/download/](https://neo4j.com/download/)
2. **Create a new database** with password 'password' to match configuration
3. **Use the Neo4j driver included by the normal project setup.**

4. **Test your connection**:
   ```python
   from neo4j import GraphDatabase
   uri = "bolt://localhost:7687"
   driver = GraphDatabase.driver(uri, auth=("neo4j", "password"))
   with driver.session() as session:
       result = session.run("MATCH (n) RETURN count(n) AS count")
       print(result.single()["count"])
   driver.close()
   ```

---

## Notes
- **Python Versions**: 
  - Application, agent, and Jupyter containers use `python:3.13-slim-bookworm`
  - Local development requires Python 3.13 as specified in `pyproject.toml`
  - Dependencies are declared in `pyproject.toml` and reproducibly locked in `uv.lock`

- **Data Persistence**:
  - All persistent data (MongoDB, Neo4j, Qdrant) is stored in Docker volumes or local directories
  - PDF files are stored in the configured local directory

- **Development Approach**:
  - Either use the Python virtual environment with `python -m` commands
  - Or use Docker Compose for containerized execution
  - Both methods use the same configuration and produce consistent results
  - Deveoper commonly uses both methods running in python env, docker compose and standalone databases

---

## Troubleshooting
- If you see `ModuleNotFoundError: No module named 'pymongo'`, ensure you have activated your virtual environment and installed dependencies.
- For Docker issues, ensure Docker Desktop is running and you have sufficient permissions.

---

## External Tools for Data Exploration
* The following tools are recommended for exploring the data outside the pipeline:

### MongoDB
- **MongoDB Compass** - A GUI for MongoDB that allows you to explore databases, collections, and documents
- Download: [https://www.mongodb.com/products/compass](https://www.mongodb.com/products/compass)
- Connection string: `mongodb://localhost:27017/onfig` (when connecting to the Docker container)

### Neo4j
- **Neo4j Desktop** - A complete development environment for Neo4j projects
- Download: [https://neo4j.com/download/](https://neo4j.com/download/)
- Or use the Neo4j Browser at: http://localhost:7474/ (default credentials: neo4j/password)

### Qdrant
- **Qdrant Web UI** - A built-in web interface for exploring vector collections
- Access at: http://localhost:6333/dashboard when Qdrant is running
- Also consider **Qdrant Cloud Console** for more advanced features if you're using Qdrant Cloud
- Check Jupyter notebooks for more advanced features
These tools provide graphical interfaces to explore, query, and visualize the data stored in each component of the pipeline.
---
## 📊 Optional Future Enhancements
The following features are 'planned' for future development to enhance the research pipeline:
### Data Analysis and Visualization
- **Structured research themes**: Use evidence-aware concepts/tags and measured
  retrieval rather than reviving BERTopic or Top2Vec clusters
- **Time-Series Analysis**: Track the evolution of research topics over time

### Research Enhancement Tools
- **PDF Section Parsing**: Intelligently extract structured sections from research papers (abstract, methods, results, etc.)
- **Citation Parsing**: Extract and normalize citations from paper references
- **Mathematical Model Extraction**: Identify and extract mathematical formulas and models from papers
- **Citation Graph Analysis**: Build a graph of paper citations to identify seminal works
- **Researcher Networks**: Map collaboration networks among authors
- **Multi-Modal Analysis**: Extract and analyze figures and tables from papers
- **Fine-tuning Pipelines**: Fine-tune pipelines for specific use cases
- **Research comparison tools**: Add evaluated method-comparison primitives
  over the token-budgeted context service. Private project-context matching is
  owned by the separate AI harness project.

### Infrastructure Improvements
- **MCP client coverage**: Validate the read-only adapter with each harness used in production
- **Retrieval evaluation growth**: Add real harness queries as the curated corpus expands
- **Export Tools**: Add BibTeX and PDF collection exports
- **Web Admin Interface**: Add web admin interface for configuration and running pipelines

## To-Do List
- [ ] **Short-term Tasks**
  - [ ] Optimize PDF download with parallel processing
  - [ ] Add citation extraction from PDF full text
  - [ ] Implement paper similarity metrics
  - [ ] Create basic analytics dashboard
  - [ ] Develop basic PDF section parser to extract abstracts and conclusions
  - [ ] Add web admin interface for configuration and running pipelines

- [ ] **Medium-term Tasks**
  - [ ] Fine-tuning pipelines for specific use cases
  - [x] Add a read-only MCP adapter over the token-budgeted harness tools
  - [ ] Evaluate whether graph-assisted retrieval adds value before extending Neo4j
  - [ ] Add full-text search capabilities
  - [ ] Implement comprehensive citation parsing system
  - [x] Create example Jupyter notebooks for research workflows
  - [ ] Develop mathematical formula extraction and indexing
  - [ ] Implement automated paper summarization
  - [ ] Set up scheduled runs for continuous updates

- [ ] **Long-term Tasks**
  - [ ] Build a recommendation system for related papers
  - [ ] Develop a natural language query interface
  - [ ] Create a researcher profile system
  - [ ] Add support for other research paper repositories (e.g., PubMed, IEEE)

- [ ] **Infrastructure Tasks**
  - [x] Add Prometheus/Grafana for monitoring
  - [ ] Implement automated testing
  - [ ] Set up CI/CD pipeline for continuous deployment
  - [ ] Optimize vector storage for large-scale collections
---

## ArXiv API Address to fetch papers metadata

http://export.arxiv.org/api/query

List used is in config/defaults.yaml for reference, more categories available. 

---

- cs.AI - Artificial Intelligence
- cs.AR - Computer Architecture
- cs.CC - Computational Complexity
- cs.CE - Computational Engineering, Finance, and Science
- cs.CL - Computation and Language
- cs.CR - Cryptography and Security
- cs.CV - Computer Vision and Pattern Recognition
- cs.CY - Cybersecurity and Privacy
- cs.DB - Databases
- cs.DC - Distributed, Parallel, and Cluster Computing
- cs.DS - Data Structures and Algorithms
- cs.GT - Computer Science and Game Theory
- cs.IT - Information Theory
- cs.LG - Machine Learning
- cs.LO - Logic in Computer Science
- cs.MA - Multiagent Systems
- cs.NE - Neural and Evolutionary Computing
- cs.OH - Other Computer Science
- cs.RO - Robotics
- cs.SI - Social and Information Networks
- math.AP - Analysis of Partial Differential Equations
- math.PR - Probability
- math.ST - Statistics
- physics.data-an - Data Analysis, Statistics and Probability
- q-bio.NC - Neurons and Cognition
- stat.AP - Applied Statistics
- stat.CO - Computation Statistics
- stat.ME - Methodology
- stat.ML - Machine Learning
- stat.OT - Other Statistics

---
For more details about project and status, see the `docs/` directory.
