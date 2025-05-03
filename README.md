# ArXiv Research Pipeline

🧠 ArXiv Local AI Research Pipeline
A modular, fully local, open-source pipeline for fetching, structuring, and exploring AI research papers from arXiv.org. It allows offline graph-based and semantic search through MongoDB, Neo4j, and Qdrant using Hugging Face embeddings. All services run in Docker for easy, consistent local deployment.

🚀 Key Features
Local-first: Everything runs offline—no cloud dependencies but can deploy to cloud in containers. Fetching papers requires internet connection.

arXiv Ingestion: Fetch papers from the cs.AI category (configurable) see list bottom of document. Duplicate papers are discarded.

MongoDB Storage: Stores structured and raw metadata.

Graph Representation: Neo4j graph database captures relationships between papers, authors, and categories.

LLM Category Summary: LLM reads papers to categories by subject, architecture and mathatical models.

Semantic Embeddings: Embeds text using Hugging Face models, stored in Qdrant for similarity search.

Configurable & Modular: Centralized settings let you switch categories, models, and components.

User Inferace: User friendly interface for explore datasets, knowledge graphs and similarity search.

Containerized: Fully Dockerized for isolated, repeatable setup.

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

## Setup InstructionsPDF_DIR = r"E:\AI Research"

pdf directory is set to E:\AI Research\ in utils/download_pdfs.py

PDF_DIR = r"E:\AI Research"

This project works on both Windows and Ubuntu/Linux environments.

---

### Prerequisites

- Git
- Python 3.9+ (Python 3.12-slim recommended)
- [UV](https://github.com/astral-sh/uv) (for fast Python dependency management)
- Docker and Docker Compose (for containerized deployment)

---

### Installation (Local, Non-Docker)

#### Linux/macOS/WSL:
```bash
# Make the setup script executable
chmod +x scripts/setup_uv.sh

# Run the setup script
./scripts/setup_uv.sh

# Activate the virtual environment
source .venv/bin/activate
```

#### Windows (PowerShell):
```powershell
# Run the setup script
.\scripts\setup_uv.ps1

# Activate the virtual environment
.venv\Scripts\Activate.ps1
```

---
### Running the Pipeline Locally

```bash
python -m src.pipeline.run_pipeline --config config/default.yaml
```

---

### Dockerized Deployment
0. Suggested run in venv from scripts above for your OS
1. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```
2. **(Optional) Rebuild the app service after code changes:**
   ```bash
   docker-compose build app
   ```
   OR run with logs
   ```bash
   docker compose up -d app 
   docker compose logs -f app
   ```
   To shutdown docker env
   ```bash
   docker-compose down
   ```
3. **Access MongoDB, Neo4j, and Qdrant via their exposed ports.**

   ---
   ```bash
   docker compose up --build sync-neo4j
   ```
   Download papers *issue, sometimes you need to you use
   mongodb://localhost:27017/onfig
   
   or default in config/defaults.yaml
   below changes default and runs. Default may not need to be changed though
   
   mongodb://mongodb:27017/
   ```bash
   $env:MONGO_URI="mongodb://localhost:27017/onfig"
   python src/utils/download_pdfs.py
   ```
---
### Configuration

- Edit `config/default.yaml` to change categories, fetch limits, or database settings.

---

### Notes

- The default Python version for Docker is now `python:3.12-slim`.
- All persistent data (MongoDB, Neo4j, Qdrant) is stored in Docker volumes.
- For development, use the local virtual environment; for production or multi-service orchestration, use Docker Compose.

---

### Troubleshooting

- If you see `ModuleNotFoundError: No module named 'pymongo'`, ensure you have activated your virtual environment and installed dependencies.
- For Docker issues, ensure Docker Desktop is running and you have sufficient permissions.

---
📊 Optional Enhancements
These features are supported or planned:

Local web dashboard for visual exploration

PDF downloading and section parsing

Citation parsing

Scheduled updates (cron)

Example notebooks for research

All components are modular and can be swapped or extended via config.

---
💡 Use Cases
Build local AI paper libraries

Graph analysis of research trends

Offline semantic paper search

Prototyping citation or influence mapping tools

---
## API Address 
http://export.arxiv.org/api/query
---
cs.AI - Artificial Intelligence

cs.GT - Computer Science and Game Theory

cs.CV - Computer Vision and Pattern Recognition

cs.CL - Computation and Language

cs.DS - Data Structures and Algorithms

cs.LO - Logic in Computer Science

cs.LG - Machine Learning

cs.MA - Multiagent Systems

cs.NE - Neural and Evolutionary Computing

cs.NA - Numerical Analysis

stat - Statistics

stat.ML - Machine Learning

stat.TH - Statistics Theory

math.PR - Probability

q-bio.NC - Neurons and Cognition

physics.data-an - Data Analysis, Statistics and Probability

cs.AI, cs.GT, cs.CV, cs.DS, cs.LO, cs.LG, cs.MA, cs.NE
cs.NA, stat, stat.ML, math.PR, q-bio.NC, physics.data-an

---
For more details, see the `docs/` directory.
