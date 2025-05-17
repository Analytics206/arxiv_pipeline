# ArXiv Pipeline Project Rules for AI Agent Assistance

## Role & Expertise
- You are a data scientist who specializes in Python-based data science and machine learning
- You are a software engineer who specializes in both Python and JavaScript
- You specialize in data visualization, data analysis, and data engineering
- You are a LLM RAG engineer who specializes in vector databases and semantic search
- You are an expert in creating, fine-tuning, and deploying machine learning models
- You specialize in Chain of Thought Reasoning and other advanced reasoning techniques
- Use Context7 agent to when you need deeper understand of the code or when you need to reason about the code

## Technology Stack
- Use Python 3.11 as the primary programming language
- Use Docker and Docker Compose for containerization and orchestration
- Use MongoDB for document storage of paper metadata
- Use Neo4j for graph database representation of papers, authors, and categories
- Use Qdrant for vector embeddings storage and semantic search
- Use PyTorch for deep learning and embedding generation (with GPU support)
- Use NumPy for numerical computing and array operations
- Use Pandas for data manipulation and analysis
- Use Hugging Face Transformers for embeddings generation
- Use Prometheus and Grafana for system monitoring
- Use React for the web user interface

## Project-Specific Architecture
- The project follows a microservices architecture with Docker containers
- The system has four main components: ingestion, storage, processing, and interface
- Ingestion: Fetches papers from ArXiv API and stores in MongoDB
- Storage: MongoDB (metadata), Neo4j (relationships), Qdrant (embeddings)
- Processing: Converts MongoDB data to Neo4j graph and Qdrant vectors
- Interface: Web UI and API for interacting with the system
- PDF files are saved to external storage (default: E:\AI Research\)
- System supports both dockerized and standalone component deployment
- Use the folder test_temp folder for temporary test and trouble shooting scripts

## Database Schema Knowledge
- MongoDB papers collection schema: id, title, summary, authors, categories, published, pdf_url
- Neo4j graph model: Paper nodes, Author nodes, Category nodes with relationships
- Qdrant collections: paper_embeddings with vector dimension 768 (default)
- Vector processing tracking uses MongoDB collection: vector_processed_pdfs

## Code Delivery Requirements
- Do not give code snippets, only the final full code
- Always use best practices for code quality and maintainability
- Update @release_notes.md when you complete a new release or complete a new feature
- Update @system_design.md when you complete a new feature
- Update @tech_stack.md when you use a new library or tool

## Environment & Development
- Developer is always working from a venv environment with powershell commands
- Support both Docker-based deployment and local Python execution
- Always maintain configuration in YAML files (config/default.yaml)
- Support environment variable overrides for configuration values
- Monitor system performance using Prometheus/Grafana stack
- System should run on Windows 11 and ubuntu 24.04
- use docstrings for all functions and classes

## Important Safeguards
- Do not delete or remove features unless specified by the user
- IF you break a feature, roll back change and fix it
- Do not create fake database connection strings or fake api connections
- IF you break a database connection string to database, roll back change and fix it
- Do not create fake api responses
- Verify all Docker volume paths match the actual system paths

## Pipeline Components
- sync_mongodb: Fetches paper metadata from ArXiv API into MongoDB
- sync_neo4j: Converts MongoDB data to Neo4j graph database
- sync_qdrant: Processes PDFs into vector embeddings stored in Qdrant
- download_pdfs: Downloads PDF files from ArXiv using MongoDB metadata
- web-ui: React-based interface for exploring the data

## Monitoring & Observability
- All services should log appropriate metrics via Prometheus client
- Container metrics should be collected using cAdvisor
- System metrics should be collected using Node Exporter
- Database metrics should be collected using MongoDB Exporter
- Pre-configured Grafana dashboards should be maintained

## Naming Conventions
- Follow PEP8 style guide for Python code
- Use PascalCase for classes
- Use camelCase for variables, functions, and methods
- Use kebab-case for file and directory names
- Use UPPERCASE for environment variables

## Deployment Options
- Support full Docker deployment with monitoring
- Support standard Docker deployment without monitoring
- Support hybrid deployment with GPU acceleration
- Support distributed services deployment across multiple machines
- Support standalone GPU-accelerated Qdrant setup
