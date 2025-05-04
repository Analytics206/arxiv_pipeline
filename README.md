# 🧠 ArXiv Deep Research Pipeline
## Overview
A modular, fully local, open-source pipeline for fetching, structuring, and exploring AI research papers from arXiv.org. This system enables offline graph-based and semantic search through an integrated architecture of MongoDB, Neo4j, and Qdrant using Hugging Face embeddings. All services run in Docker containers for easy, consistent local deployment.

## 🚀 Key Features
| Feature | Description |
|---------|-------------|
| 🏠 **Local-first** | Everything runs offline with no cloud dependencies. Can deploy to cloud in containers if desired. |
| 💾 **ArXiv Ingestion** | Fetches non-duplicate papers from configurable categories (e.g., cs.AI) with smart date filtering. |
| 🗒 **MongoDB Storage** | Stores structured metadata, paper information, and download statuses. |
| 🐙 **Graph Representation** | Neo4j graph database captures relationships between papers, authors, and categories. |
| 🤖 **LLM Category Summary** | Uses LLMs to categorize papers by subject, architecture, and mathematical models. |
| 💡 **Semantic Embeddings** | Creates vector embeddings using Hugging Face models, stored in Qdrant for similarity search. |
| 🔧 **Configurable & Modular** | Centralized settings allow switching categories, models, and components. |
| 👀 **User Interface** | User-friendly interface for exploring datasets, knowledge graphs, and similarity search. |
| 📦 **Containerized** | Fully Dockerized with persistent volumes for reliable data storage and consistent execution. |

![Image](https://github.com/user-attachments/assets/3233595b-ecbc-4029-a0f9-1e6723c026a7)

📦 System Components
| Component             | Purpose                                      |
| --------------------- | -------------------------------------------- |
| **Ingestion Service** | Fetches papers using arXiv Atom XML API      |
| **MongoDB**           | Stores raw and normalized metadata           |
| **Neo4j**             | Stores the author-paper-category graph       |
| **Qdrant**            | Stores vector embeddings for semantic search |
| **Config Manager**    | Central config for category, limits, model   |
| **User Interface**    | Web UI for interaction with graphs           |
| **Logger**            | Tracks events, errors, and skipped entries   |
| **Docker Compose**    | Brings it all together for local use         |


A local, platform-independent pipeline for processing research papers from arXiv.org.

## Setup Instructions

pdf save directory is set to E:\AI Research\ in "src\utils\download_pdfs.py"

PDF_DIR = r"E:\AI Research"

This project works on both Windows and Ubuntu/Linux environments.

---

## Prerequisites

- Git
- Python 3.9+ (Python 3.12-slim recommended)
- [UV](https://github.com/astral-sh/uv) (for fast Python dependency management)
- [Ollama](https://ollama.ai/) (optional, for enhanced image analysis)
- Docker and Docker Compose (for containerized deployment)
- NVIDIA GPU with CUDA support (optional, for faster vector operations)

---
## High Level Overview
 - Fetch papers from arXiv.org using arXiv Atom XML API
 - Store raw and normalized metadata in MongoDB with pdf_url for pdf download
 - Download PDFs from arXiv.org and store in local directory
 - Store the author-paper-category graph in Neo4j
 - Store vector embeddings for semantic search in Qdrant
 - Central config for category, limits, model
 - Web UI for interaction with graphs
 - Tracks events, errors, and skipped entries  

### Installation (Local, Non-Docker)

## Linux/macOS/WSL:
```bash
# Make the setup script executable
chmod +x scripts/setup_uv.sh

# Run the setup script
./scripts/setup_uv.sh

# Activate the virtual environment
source .venv/bin/activate
```

## Windows (PowerShell):
```powershell
# Run the setup script
.\scripts\setup_uv.ps1

# Activate the virtual environment
.venv\Scripts\Activate.ps1
```

---
## Running the Pipeline Locally
Not recommended better to run in docker and this option might be removed or unsupported.
```bash
python -m src.pipeline.run_pipeline --config config/default.yaml
```

---
## Dockerized Deployment - Docker Desktop Running
0. Suggested run in venv from scripts above for your OS

1. **Build and start all services:**
   ```bash
   docker compose up -d
   ```
2. **(Optional) Rebuild the app service after code changes:**
   ```bash
   docker compose up -d --build
   ```
3. **Build the app service wth logs:**
   run with logs
   ```bash
   docker compose up -d
   docker compose logs -f
   ```
   When you want to shutdown docker env *need it up to explore data*:
   ```bash
   docker compose down
   ```
# 4. Run Pipelines: MongoDB, Download PDFs, Neo4j, and Qdrant Pipelines

   *pipelines do not have to run in order if you have previously run them or starting where you left off

   *recommended to run them in order for processing new papers
   ## a. Run sync_mongodb pipeline to fetch papers from ArXiv API and store in MongoDB:
   ```bash
   echo $env:MONGO_URI
   $env:MONGO_URI="mongodb://localhost:27017/onfig"
   python -m src.pipeline.sync_mongodb --config config/default.yaml
   ```
   or
   ```bash
   docker compose up --build sync-mongodb
   ```

   ## b. Run sync-neo4j pipeline for new pdf metadata inserted from MongoDB:
   ```bash
   docker compose up --build sync-neo4j
   ```
   or
   ```bash
   echo $env:MONGO_URI
   $env:MONGO_URI="mongodb://localhost:27017/onfig"
   echo $env:MONGO_URI
   python -m src.graph.sync_mongo_to_neo4j
   ```
   
   ## c. Run download_pdfs pipeline to download PDFs from arxiv.org using metadata stored in MongoDB:
   ```bash
   echo $env:MONGO_URI
   $env:MONGO_URI="mongodb://localhost:27017/onfig"
   echo $env:MONGO_URI
   python -m src.utils.download_pdfs
   ```
   
   ## d. Run sync_qdrant pipeline to process downloaded PDFs and store as vector embeddings in Qdrant:
   ```bash
   python -m src.pipeline.sync_qdrant
   ```
   or
   ```bash
   docker compose up --build sync-qdrant
   ```
   
   **New Feature:** The sync_qdrant pipeline now includes **MongoDB tracking** to prevent duplicate processing of PDFs. Each processed PDF is recorded in the `processed_pdfs` collection with metadata including file hash, processing date, and chunk count.
   
   Note: set "MONGO_URI" env var to "mongodb://mongodb:27017/" for docker pipelines
   ```bash
   echo $env:MONGO_URI
   $env:MONGO_URI="mongodb://mongodb:27017/"
   echo $env:MONGO_URI
   ```

## 5. Web UI
   To restart Web UI docker service, starts with docker-compose up above:
   ```bash
   docker-compose up -d web-ui
   ```
   Access the web interface at: http://localhost:3000

### Web UI Development Setup

The web interface uses React with the Neo4j JavaScript driver. If you want to develop the web UI locally:

1. **Navigate to the web-ui directory**:
   ```bash
   cd src/web-ui
   ```

2. **Install dependencies including Neo4j JavaScript driver**:
   ```bash
   npm install
   # Or to install Neo4j driver specifically:
   npm install neo4j-driver@5.13.0
   ```

3. **Start the development server**:
   ```bash
   npm start
   ```

The web UI connects to Neo4j using environment variables defined in the docker-compose.yml file. For local development, you can create a `.env.local` file in the src/web-ui directory with the appropriate Neo4j connection details.

---
### Configuration
![Image](https://github.com/user-attachments/assets/7d68b38e-b4a1-49d9-acf4-17b74fb05e22)

The application is configured using YAML files in the `config/` directory. The default configuration is in `config/default.yaml`.

Key configuration options:

## Recent Feature Additions

### 1. MongoDB Tracking for Qdrant Vector Processing

The sync_qdrant pipeline now includes a tracking system to prevent duplicate processing and provide synchronization with Qdrant:

```yaml
# In config/default.yaml
qdrant:
  # ... other settings ...
  tracking:
    enabled: true # Whether to track processed PDFs
    collection_name: "processed_pdfs" # MongoDB collection to store tracking information
    sync_with_qdrant: true # Whether to sync tracking with actual Qdrant contents
```

This system:
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

## PDF Storage Location
To change where PDFs are stored, edit the pdf_storage.directory in the config:

```yaml
# In config/default.yaml
pdf_storage:
  directory: E:/AI Research
```

The `sync_qdrant` pipeline uses [Ollama](https://ollama.ai/) for analyzing images extracted from PDFs if available:

- **What Ollama does**: Enhances the vector database by adding AI-generated descriptions of diagrams and figures in papers
- **Installation**: Download and install Ollama from [ollama.ai](https://ollama.ai/)
- **Required model**: Run `ollama pull llama3` to download the required model
- **Without Ollama**: The pipeline still functions normally without Ollama, but image descriptions will be placeholders

## ArXiv Pipeline Configuration Settings
The system is configured through `config/default.yaml`. Key configuration sections include:

### Ollama Integration (Optional)

The `sync_qdrant` pipeline uses [Ollama](https://ollama.ai/) for analyzing images extracted from PDFs if available:

- **What Ollama does**: Enhances the vector database by adding AI-generated descriptions of diagrams and figures in papers
- **Installation**: Download and install Ollama from [ollama.ai](https://ollama.ai/)
- **Required model**: Run `ollama pull llama3` to download the required model
- **Without Ollama**: The pipeline still functions normally without Ollama, but image descriptions will be placeholders

### Important Note About PDF Paths in Docker

When running the `sync_qdrant` service in Docker, the PDF directory path specified in `config/default.yaml` is overridden by the volume mapping in `docker-compose.yml`:

```yaml
# In docker-compose.yml
volumes:
  - E:/AI Research:/app/data/pdfs  # Maps Windows path to container path
```

This means:
- Your PDFs should be stored in `E:/AI Research` on your Windows machine
- Inside the Docker container, they will be accessible at `/app/data/pdfs`
- The script automatically detects when running in Docker and adjusts paths accordingly

If you change your PDF storage location, make sure to update both:
1. The `pdf_storage.directory` in `config/default.yaml` (for local runs)
2. The volume mapping in `docker-compose.yml` (for Docker runs)
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
   - arxiv.max_papers_per_category: Maximum number of papers to download per category
   - arxiv.sort_by: Sort papers by this field
   - arxiv.sort_order: Sort papers in this order

   ## sync_qdrant pipeline
   - arxiv.max_papers: Maximum number of papers to process
   - arxiv.max_papers_per_category: Maximum number of papers to download per category
   - arxiv.sort_by: Sort papers by this field
   - arxiv.sort_order: Sort papers in this order

   ## download_pdfs pipeline
   - arxiv.max_papers: Maximum number of papers to process
   - arxiv.max_papers_per_category: Maximum number of papers to download per category
   - arxiv.sort_by: Sort papers by this field
   - arxiv.sort_order: Sort papers in this order

Config changes take effect when services are restarted. See `docs/system_design.md` for detailed information about configuration impact on system behavior.

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

The pipeline can use GPU acceleration for generating embeddings in the `sync_qdrant.py` script:

1. **Install PyTorch with CUDA support**:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```
Choose the appropriate CUDA version (cu118, cu121, etc.) based on your system. Check with `nvidia-smi`.

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
2. **Install Python driver**:
   ```bash
   pip install pymongo>=4.3.0
   ```

3. **Test your connection**:
   ```python
   from pymongo import MongoClient
   
   client = MongoClient('mongodb://localhost:27017/')
   db = client['arxiv_papers']
   print(f"Connected to MongoDB: {client.server_info()['version']}")
   ```

### Neo4j Installation

#### Option 1: With Docker (recommended)
The Docker setup includes Neo4j, so no additional installation is needed if using Docker Compose.

#### Option 2: Standalone Neo4j Installation
1. **Download Neo4j Desktop**: [https://neo4j.com/download/](https://neo4j.com/download/)
2. **Create a new database** with password 'password' to match configuration
3. **Install Python driver**:
   ```bash
   pip install neo4j>=5.5.0
   ```

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

### Database Connection Settings
```yaml
mongo:
  connection_string: "mongodb://mongodb:27017/"
  db_name: "arxiv_papers"
  
neo4j:
  url: "bolt://neo4j:7687"  # Neo4j connection URL
  user: "neo4j"
  password: "password"
qdrant:
  url: "http://localhost:6333"
  collection_name: "arxiv_papers"
  vector_size: 768  # For all-MiniLM-L6-v2 model
```

---

## Notes

- **Python Versions**: 
  - Docker containers use `python:3.11-slim`
  - Local development 'requires' Python ≥3.11 as specified in pyproject.toml
  - All dependencies are managed through pyproject.toml for consistent environments

- **Data Persistence**:
  - All persistent data (MongoDB, Neo4j, Qdrant) is stored in Docker volumes
  - PDF files are stored in the configured local directory

- **Development Approach**:
  - Either use the Python virtual environment with `python -m` commands
  - Or use Docker Compose for containerized execution
  - Both methods use the same configuration and produce consistent results

---

## Troubleshooting

- If you see `ModuleNotFoundError: No module named 'pymongo'`, ensure you have activated your virtual environment and installed dependencies.
- For Docker issues, ensure Docker Desktop is running and you have sufficient permissions.

---

## External Tools for Data Exploration

The following tools are recommended for exploring the data outside the pipeline:

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

These tools provide graphical interfaces to explore, query, and visualize the data stored in each component of the pipeline.

---
## 📊 Optional Future Enhancements

The following features are 'planned' for future development to enhance the research pipeline:

### Data Analysis and Visualization
- **Jupyter Lab Integration**: Add a dedicated Jupyter service with pre-built notebooks for research analysis
- **Example Notebooks for Research**: Create ready-to-use notebooks for common research tasks and analyses
- **Topic Modeling**: Implement BERTopic or LDA for automatic discovery of research themes
- **Time-Series Analysis**: Track the evolution of research topics over time

### Research Enhancement Tools
- **PDF Section Parsing**: Intelligently extract structured sections from research papers (abstract, methods, results, etc.)
- **Citation Parsing**: Extract and normalize citations from paper references
- **Mathematical Model Extraction**: Identify and extract mathematical formulas and models from papers
- **Citation Graph Analysis**: Build a graph of paper citations to identify seminal works
- **Researcher Networks**: Map collaboration networks among authors
- **Multi-Modal Analysis**: Extract and analyze figures and tables from papers

### Infrastructure Improvements
- **LangChain-based Research Assistant**: Natural language interface to query the database
- **Hybrid Search**: Combine keyword and semantic search for better results
- **Export Tools**: Add BibTeX and PDF collection exports

## To-Do List

- [ ] **Short-term Tasks**
  - [ ] Optimize PDF download with parallel processing
  - [ ] Add citation extraction from PDF full text
  - [ ] Implement paper similarity metrics
  - [ ] Create basic analytics dashboard
  - [ ] Develop basic PDF section parser to extract abstracts and conclusions

- [ ] **Medium-term Tasks**
  - [ ] Extend Neo4j schema to include citations between papers
  - [ ] Add full-text search capabilities
  - [ ] Implement comprehensive citation parsing system
  - [ ] Create example Jupyter notebooks for research workflows
  - [ ] Develop mathematical formula extraction and indexing
  - [ ] Implement automated paper summarization
  - [ ] Set up scheduled runs for continuous updates

- [ ] **Long-term Tasks**
  - [ ] Build a recommendation system for related papers
  - [ ] Develop a natural language query interface
  - [ ] Create a researcher profile system
  - [ ] Add support for other research paper repositories (e.g., PubMed, IEEE)

- [ ] **Infrastructure Tasks**
  - [ ] Add Prometheus/Grafana for monitoring
  - [ ] Implement automated testing
  - [ ] Set up CI/CD pipeline for continuous deployment
  - [ ] Optimize vector storage for large-scale collections

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
- **Paper Summarization**: Generate concise summaries of complex research papers
- **Similar Papers Discovery**: Use vector similarity to find related work not linked by citations
- **Research Idea Generation**: Use paper combinations with LLMs to explore novel research directions
- **Algorithm Implementation Assistance**: Extract mathematical models for implementation in your own projects

### Education & Learning
- **Personalized Learning Paths**: Create sequential reading lists for specific AI topics
- **Concept Visualization**: Extract and visualize key concepts across multiple papers
- **Interactive Research Exploration**: Navigate research spaces through concept and citation graphs
- **Teaching Material Preparation**: Curate papers and extract examples for courses and tutorials
---

## ArXiv API Address to fetch papers metadata
http://export.arxiv.org/api/query

List used is in config/defaults.yaml for reference, more categories available. 
---
- cs.AI - Artificial Intelligence
- cs.CL - Computation and Language
- cs.CV - Computer Vision and Pattern Recognition
- cs.DS - Data Structures and Algorithms
- cs.GT - Computer Science and Game Theory
- cs.LG - Machine Learning
- cs.LO - Logic in Computer Science
- cs.MA - Multiagent Systems
- cs.NA - Numerical Analysis
- cs.NE - Neural and Evolutionary Computing
- math.PR - Probability
- q-bio.NC - Neurons and Cognition
- stat - Statistics
- stat.ML - Machine Learning
- stat.TH - Statistics Theory
- physics.data-an - Data Analysis, Statistics and Probability

---
For more details about project and status, see the `docs/` directory.
