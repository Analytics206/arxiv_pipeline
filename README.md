# ArXiv Research Pipeline

A local, platform-independent pipeline for processing research papers from arXiv.org.

## Setup Instructions

This project works on both Windows and Ubuntu/Linux environments.

---

### Prerequisites

- Git
- Python 3.8+ (Python 3.10 recommended)
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
python src/pipeline/run_pipeline.py --config config/default.yaml
```

---

### Dockerized Deployment

1. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```

2. **(Optional) Rebuild the app service after code changes:**
   ```bash
   docker-compose build app
   ```
   OR better option

   docker compose up -d app 
   docker compose logs -f app

3. **Access MongoDB, Neo4j, and Qdrant via their exposed ports.**

---

### Configuration

- Edit `config/default.yaml` to change categories, fetch limits, or database settings.

---

### Notes

- The default Python version for Docker is now `python:3.10-slim`.
- All persistent data (MongoDB, Neo4j, Qdrant) is stored in Docker volumes.
- For development, use the local virtual environment; for production or multi-service orchestration, use Docker Compose.

---

### Troubleshooting

- If you see `ModuleNotFoundError: No module named 'pymongo'`, ensure you have activated your virtual environment and installed dependencies.
- For Docker issues, ensure Docker Desktop is running and you have sufficient permissions.

---

For more details, see the `docs/` directory.