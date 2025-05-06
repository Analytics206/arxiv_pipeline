# ArXiv Deep Research Pipeline Release Notes

## Version 0.4.0 (May 6, 2025)

### Major Features

#### Web UI Enhancements
- **Home Page Implementation** - Added new home page to the web UI with centralized navigation
- **Integration Links** - Added links to Neo4j Explorer from previous web UI release
- **Placeholder Pages** - Created landing pages for MongoDB Reports, QDrant Search, Jupyter Notebooks, Config Editor, and Pipeline Management

#### Database Status Dashboard
- **Connection Status Indicators** - Added real-time status indicators for Neo4j, MongoDB, and Qdrant connections
- **Database Statistics** - Implemented counters for Papers, Authors, and Categories across all data stores
- **MongoDB Integration** - Added direct connection to MongoDB for accurate document counts

#### Infrastructure Improvements
- **Docker Environment Cleanup** - Optimized Docker container configuration and removed redundancies
- **Resource Utilization** - Improved memory and CPU usage across containerized services

### Documentation
- **User Interface Guide** - Added documentation for navigating the enhanced web UI
- **Database Status Documentation** - Created guide for interpreting database status indicators
- **Updated Setup Instructions** - Refreshed installation and configuration documentation

---

## Version 0.3.0 (May 4, 2025)

### Major Features

#### Remote GPU-Accelerated Qdrant Setup
- **WSL2-based GPU Acceleration** - Added support for running Qdrant with GPU acceleration on a separate Windows machine with WSL2
- **Native Rust Compilation** - Documented process for building Qdrant from source with CUDA support
- **Optimization for Research Papers** - Configured for optimal performance with 768-dimensional embeddings typical for research papers
- **Network Integration** - Created integration path for connecting ArXiv pipeline to remote Qdrant instance
- **Comprehensive Documentation** - Added detailed setup instructions in qdrant_setup directory
- **Benchmarking Tools** - Created tools for measuring performance improvements from GPU acceleration
- **Security Guidelines** - Added authentication and network security recommendations

#### Interactive Database Testing with Jupyter Notebooks
- **Database Connectivity Testing** - Added Jupyter notebook for testing connections to MongoDB, Neo4j, and Qdrant
- **Connection Status Visualization** - Implemented visual dashboard for database connectivity status
- **Database Schema Exploration** - Created interactive tools for exploring database schemas and contents
- **Environment Variable Support** - Added support for configuration via environment variables and .env files
- **MongoDB Analysis Notebook** - Created comprehensive MongoDB analytics for paper metadata, including:
  - Publication trends over time
  - Author analytics and rankings
  - Category distribution analysis
  - Text analysis of titles and abstracts
  - Database health and performance metrics
- **Neo4j Graph Analysis Notebook** - Implemented graph visualization and analysis capabilities, including:
  - Author collaboration networks
  - Category relationship visualization
  - Path analysis between researchers
  - Community detection algorithms
  - Citation network analysis
- **Qdrant Semantic Search Notebook** - Added vector database exploration tools, including:
  - Vector embedding visualization using t-SNE
  - Semantic search capabilities with examples
  - Topic clustering with K-means
  - Related papers exploration
  - Research recommendation system

#### System Monitoring with Prometheus/Grafana
- **Comprehensive Monitoring Stack** - Added Prometheus and Grafana for metrics collection and visualization
- **Container Metrics** - Implemented container monitoring with cAdvisor for resource usage tracking
- **System Metrics** - Added Node Exporter for host system metrics (CPU, memory, disk, network)
- **Database Monitoring** - Integrated MongoDB Exporter for database performance metrics
- **Custom Application Metrics** - Added framework for tracking application-specific metrics (paper processing, vector operations)
- **Specialized Dashboards** - Created data science-focused dashboards for monitoring the research pipeline:
  - **Data Science Dashboard** - Core metrics for paper processing and database performance
  - **Advanced Analytics Dashboard** - System correlation metrics and resource optimization
  - **Vector Embedding Dashboard** - Focused on vector database and embedding operations
  - **Basic Test Dashboard** - Simple connectivity verification dashboard
- **Separate Deployment Stack** - Implemented as a separate docker-compose.monitoring.yml for independent deployment

#### Documentation Updates
- **Monitoring Documentation** - Added comprehensive documentation for the monitoring system in dev_notes.md
- **System Design Updates** - Updated system_design.md with monitoring architecture details
- **Prometheus Query Documentation** - Created reference documentation for Prometheus queries:
  - **Basic Queries** - Simple queries for troubleshooting (prometheus_basic_queries.md)
  - **General Purpose Queries** - Standard monitoring queries (prometheus_queries.md)
  - **Custom Queries** - ArXiv pipeline specific metrics (prometheus_custom_queries.md)
  - **Working Queries** - Verified working queries for dashboards (prometheus_working_queries.md)
- **Container ID Reference** - Added container_id_reference.md for understanding container label formats
- **Dashboard Guide** - Created grafana_dashboard_guide.md with dashboard customization instructions
- **README Updates** - Enhanced README.md with detailed monitoring documentation

### Configuration Enhancements
- **Prometheus Configuration** - Added central configuration in config/prometheus/prometheus.yml
- **Grafana Datasources** - Added auto-provisioned datasource for Prometheus
- **Dashboard Provisioning** - Configured automatic dashboard loading for Grafana

### Dependencies and Tools
- **Prometheus** - Added as a containerized time series database for metrics
- **Grafana** - Added as a visualization platform for monitoring dashboards
- **cAdvisor** - Added for container metrics collection
- **Node Exporter** - Added for host system metrics collection
- **MongoDB Exporter** - Added for database-specific metrics
- **Prometheus Client Library** - Added for custom application metrics instrumentation

### Diagnostic Tools
- **Metrics Analyzer** - Enhanced check_prometheus_metrics.py diagnostic script with:
  - MongoDB metrics verification
  - Dashboard query validation
  - Data science recommendation features
  - Comprehensive error handling

---
## Version 0.2.0 (May 3, 2025)

### Major Features

#### PDF Processing and Vector Storage
- **MongoDB Tracking System** - Added tracking of processed PDFs in `vector_processed_pdfs` collection to prevent duplicate processing
- **PDF Processing Tracking** - Each processed PDF is tracked with file hash, chunk count, and processing date
- **Category-Based Processing** - Implemented selective vector processing based on configured research categories
- **Papers per Category Limit** - Added configurable limit for papers to process per category

#### GPU Acceleration
- **GPU Support for Vector Operations** - Added GPU acceleration for both Qdrant vector database and embedding generation
- **Multi-GPU Support** - Implemented configurable GPU device selection for optimal performance
- **Automatic Device Detection** - Added graceful fallback to CPU when GPU is unavailable or not properly configured

#### Deployment Improvements
- **Hybrid Deployment Architecture** - Added support for running Qdrant locally with GPU while other services run in Docker
- **Host.Docker.Internal Integration** - Enhanced Docker services to communicate with local Qdrant instance
- **Standalone Qdrant Configuration** - Added documentation for running Qdrant with GPU acceleration
- **Docker Volume Path Handling** - Improved Windows path compatibility for mounted volumes

#### Error Handling
- **Ollama Integration Improvements** - Made Ollama optional with graceful fallback when not available
- **Better Error Recovery** - Added robust error handling for PDF processing failures

### Configuration Enhancements
- **Centralized PDF Directory Config** - Moved PDF directory configuration to central config file
- **Dynamic MongoDB Connection** - Improved connection handling to automatically adjust for local vs Docker environments
- **Ollama Configuration** - Added controls for enabling/disabling Ollama image analysis

### Documentation
- **Deployment Options** - Added documentation for both Docker and standalone deployment options
- **GPU Configuration Guide** - Documented GPU setup and acceleration options
- **Database Installation Guides** - Added detailed instructions for MongoDB, Neo4j, and Qdrant installation
- **Development Notes** - Added developer notes document for tracking ongoing work
- **Release Notes** - Added this release notes document

### Dependencies and Libraries
- **PyTorch with CUDA** - Updated PyTorch requirements to include CUDA support
- **Neo4j JavaScript Driver** - Added documentation for the JS driver required for the web UI

---

## Version 0.1.0 (April 26, 2025)

### Major Features

#### Data Ingestion and Storage
- **ArXiv API Integration** - Implemented paper ingestion from ArXiv Atom XML API
- **MongoDB Storage** - Created document storage for paper metadata with appropriate indexing
- **Neo4j Graph Database** - Established graph representation for papers, authors, and categories
- **PDF Downloading** - Added functionality to download and organize research papers in PDF format
- **Vector Embedding** - Implemented basic text vectorization using Hugging Face models
- **Qdrant Integration** - Set up vector similarity search with Qdrant database

#### Docker Containerization
- **Multi-Container Setup** - Built initial Docker Compose configuration for all services
- **Volume Persistence** - Implemented persistent storage for MongoDB and Neo4j data
- **Network Configuration** - Established internal container communication and port mapping
- **Service Orchestration** - Created coordinated startup/shutdown of all system components

#### Web Interface
- **Neo4j Visualization** - Created basic web interface for exploring the knowledge graph
- **Browsing Interface** - Implemented paper browsing and navigation features
- **Web UI Container** - Dockerized the web interface with appropriate connections to backend services

### Configuration Enhancements
- **YAML Configuration** - Created initial configuration file structure
- **Environment Variables** - Implemented environment variable support for container configuration
- **API Rate Limiting** - Added configurable rate limiting for ArXiv API access

### Documentation
- **Setup Instructions** - Created installation and setup documentation
- **README** - Established initial project documentation with overview and features
- **Configuration Guide** - Documented configuration options and their effects

### Dependencies and Libraries
- **MongoDB Python Driver** - Integrated PyMongo for database access
- **Neo4j Python Driver** - Added Neo4j connectivity for graph operations
- **Hugging Face Transformers** - Integrated for text embedding generation
- **Docker and Docker Compose** - Established containerization foundation
