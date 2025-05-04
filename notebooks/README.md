# ArXiv Pipeline Jupyter Notebooks

This directory contains Jupyter notebooks for interactive exploration, testing, and analysis of the ArXiv Pipeline project.

## Available Notebooks

1. **01_database_connectivity.ipynb** - Tests connectivity to MongoDB, Neo4j, and Qdrant databases and provides basic exploration features.

## Setup Instructions

### Prerequisites

- Python 3.8+ installed
- Jupyter lab or notebook installed
- Docker containers running (if testing against containerized databases)

### Installation

1. Install Jupyter if not already installed:
   ```bash
   pip install jupyter jupyterlab
   ```

2. Install required Python packages:
   ```bash
   pip install pymongo neo4j qdrant-client pandas matplotlib ipywidgets python-dotenv
   ```
   
   Note: The notebooks will attempt to install missing packages automatically, but it's recommended to install them beforehand.

### Running the Notebooks

1. Start the necessary database containers using docker-compose:
   ```bash
   docker-compose up -d mongodb neo4j qdrant
   ```

2. Launch Jupyter Lab:
   ```bash
   jupyter lab
   ```

3. Navigate to the notebooks directory and open the desired notebook.

### Environment Configuration

The notebooks look for the following environment variables:

- **MONGO_URI** - MongoDB connection URI (default: `mongodb://localhost:27017/`)
- **MONGO_DB** - MongoDB database name (default: `arxiv_pipeline`)
- **NEO4J_URI** - Neo4j connection URI (default: `bolt://localhost:7687`)
- **NEO4J_USER** - Neo4j username (default: `neo4j`)
- **NEO4J_PASSWORD** - Neo4j password (default: `password`)
- **QDRANT_URI** - Qdrant host (default: `localhost`)
- **QDRANT_PORT** - Qdrant port (default: `6333`)

You can set these variables using:
1. A `.env` file in the project root
2. Environment variables in your shell
3. Direct modification in the notebook cells

## Notebook Descriptions

### 01_database_connectivity.ipynb

This notebook provides:
- Connection testing to MongoDB, Neo4j, and Qdrant
- Basic database exploration features
- Visualization of database content statistics
- Connection status summary

## Troubleshooting

- **Connection Issues**: Ensure the databases are running and accessible from your environment
- **Import Errors**: Check that all required packages are installed
- **Authentication Failures**: Verify credentials in `.env` file or notebook variables
