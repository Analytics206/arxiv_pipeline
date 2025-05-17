# ArXiv Deep Research Pipeline Release Notes

---
## Version 0.5.3 (May 16, 2025)

### Major Features

#### BERTopic Processing Pipeline
- **Topic Modeling** - Added BERTopic-based topic extraction from paper summaries
- **Batch Processing** - Implemented memory-efficient batch processing with configurable size
- **Filtering System** - Added category and date-based filtering for paper selection
- **MongoDB Integration** - Created new `paper_topics` collection for storing topic data
- **Docker Support** - Added `sync-bertopic` service with manual execution profile

### Technical Improvements
- **Consistent Pagination** - Enhanced MongoDB queries with consistent sorting by _id
- **Documentation** - Added comprehensive docstrings to BERTopic processing code
- **Error Handling** - Improved logging and error handling in processing pipeline

### Configuration Updates
- **BERTopic Settings** - Added new section in default.yaml for BERTopic configuration
  - MongoDB connection settings for both Docker and local environments
  - Batch processing parameters (batch_size, max_papers)
  - Category and date filters for paper selection

---
## Version 0.5.2 (May 15, 2025)

### PDF Download Improvements
- **Invalid URL Tracking** - Added tracking of invalid PDF URLs in MongoDB's `invalid_pdfs` collection
- **Efficient Filtering** - Enhanced download script to skip papers that are either downloaded or marked as invalid
- **Detailed Error Logging** - Improved error handling to log HTTP status codes and reasons for failed downloads
- **Configuration Update** - Reduced `papers_per_category` limit from 500 to 100 in default configuration

---

## Version 0.5.1 (May 9, 2025)

### Major Features

#### Data Validation and Analysis Utilities
- **MongoDB Schema Validation** - Added comprehensive validation for paper document schema in MongoDB
- **Publication Date Analysis** - Implemented flexible date analysis (year/month/day/weekday) for ArXiv papers
- **Collection Analysis Tools** - Created utilities for analyzing MongoDB collection structure and content
- **Data Integrity Checking** - Added functions to identify data integrity issues (duplicates, missing fields, temporal anomalies)
- **Reporting Framework** - Created standardized reporting for temporal data with visualization

#### Web UI Enhancements
- **Paper Analysis Dashboard** - Added interactive charts displaying paper publication trends by year/month/day
- **MongoDB Analysis Integration** - Integrated analysis data from `analyze_papers_by_year_month_day.py` into the web UI
- **API-driven Data Visualization** - Created new API endpoints to provide temporal analysis data
- **Interactive Filtering** - Added date range, year, and category filtering capabilities to analysis dashboard
- **Multi-view Charts** - Implemented yearly, monthly, and daily data visualization options
- **Category Filter** - Added research category filtering using MongoDB's categories field with dynamic dropdown menu
- **Formatted Metrics Display** - Enhanced numerical formatting with thousands separators for improved readability

### Technical Improvements
- **Centralized Logger** - Added configurable logging system with standardized formatting
- **Date Format Handling** - Implemented flexible handling of different date string formats in publications
- **Validation Sampling** - Created efficient random sampling for validating large MongoDB collections
- **Error Categorization** - Added systematic error categorization and counting for data quality monitoring
- **Temporal Consistency Checks** - Implemented algorithms to detect time gaps and inconsistencies in paper collections

### Documentation
- **README Updates** - Added section on data validation utilities with code examples
- **Validation Examples** - Created example scripts demonstrating validation usage
- **Command-line Interface** - Added CLI tools for validating MongoDB collections

### New Utilities
- **count_papers_by_date.py** - Added utility to analyze paper publication dates with daily/monthly/yearly breakdowns
- **analyze_papers_by_year_month_day.py** - Created hierarchical date analysis tool with visualization
- **validate_mongodb_data.py** - Added comprehensive MongoDB validation utility with reporting

---


## Version 0.5.0 (May 7, 2025)

### Major Features

#### Paper Summaries Vector Database Integration
- **Summary Vector Collection** - Created new Qdrant collection for paper summaries independent from full-text embeddings
- **MongoDB Integration** - Implemented direct extraction of paper summaries from the MongoDB papers collection
- **Configurable Categories** - Added separate category configuration for summary processing
- **Date-based Filtering** - Added start/end date filtering for paper summaries processing
- **Tracking System** - Implemented MongoDB-based tracking for processed summaries with the vector_processed_summary collection
- **API Integration** - Added FastAPI endpoints for managing and monitoring summary vector processing
- **Background Processing** - Implemented asynchronous background task processing for summary vectors
- **Full Summary Storage** - Embedded complete paper summaries in vector payloads for direct access during similarity searches

### Technical Improvements
- **Process Isolation** - Created isolated process for summary vectors separate from PDF-based vectors
- **Configuration Structure** - Enhanced YAML configuration with dedicated paper_summaries section
- **Batch Processing** - Implemented batch-based processing for efficient summary vectorization
- **Status Monitoring** - Added API endpoints for checking processing status
- **Direct Qdrant Integration** - Used direct Qdrant client operations for enhanced control over vector insertion
- **Deterministic Point IDs** - Created hash-based point IDs for stable references to vectors
- **Automatic Dimension Detection** - Automatically adjusts vector dimensions to match embedding model output
- **Collection Reset Logic** - Added intelligent collection management for handling dimension mismatches
- **Duplicate Prevention** - Implemented robust tracking system to prevent duplicate entries in Qdrant
- **Bulk Operations** - Used MongoDB bulk operations for efficient tracking updates
- **Two-way Synchronization** - Added bidirectional sync between Qdrant and MongoDB tracking

### Documentation
- **Tech Stack Update** - Updated tech stack documentation with new Qdrant collection details
- **Configuration Documentation** - Added documentation for the new configuration options
#### External Service Deployment Options
- **External Docker Environments** - Added standalone Docker configurations for running key services on separate machines
- **Ollama External Setup** - Created dedicated Docker setup for running Ollama on a separate machine with detailed model management instructions
- **MongoDB External Setup** - Implemented standalone MongoDB Docker configuration with security and performance optimizations
- **Neo4j External Setup** - Created external Neo4j deployment with persistent storage and optimized configuration
- **Qdrant GPU Setup** - Enhanced existing GPU-accelerated Qdrant setup with updated Docker configuration
- **Network Integration** - Streamlined connectivity between externally deployed services and the main pipeline
- **Configuration Independence** - Ensured each service can be deployed independently without dependencies on the main project

## Version 0.4.0 (May 6, 2025)

### Major Features

#### Web UI Enhancements
- **Home Page Implementation** - Added new home page to the web UI with centralized navigation
- **Integration Links** - Added links to Neo4j Explorer from previous web UI release
- **Placeholder Pages** - Created landing pages for MongoDB Reports, QDrant Search, Jupyter Notebooks, Config Editor, and Pipeline Management
- **API Integration** - Implemented web UI connection to FastAPI backend for live data ingestion from MongoDB and Qdrant
- **Pipeline API Access** - Added direct link to Pipeline API Swagger documentation in the navigation bar
- **Qdrant Connection** - Established API connectivity between web-ui and Qdrant through FastAPI backend

#### Database Status Dashboard
- **Connection Status Indicators** - Added real-time status indicators for Neo4j, MongoDB, and Qdrant connections
- **Database Statistics** - Implemented counters for Papers, Authors, and Categories across all data stores
- **MongoDB Integration** - Added direct connection to MongoDB for accurate document counts
- **Qdrant Integration** - Implemented Qdrant connection and metrics retrieval through API endpoints
- **Enhanced Qdrant Metrics** - Added reliable paper counts, vector dimensions, and collection metrics for Qdrant in the database dashboard
- **Fallback Mechanism** - Implemented robust fallback to known good values when API connections experience issues

#### Infrastructure Improvements
- **Docker Environment Cleanup** - Optimized Docker container configuration and removed redundancies
- **Resource Utilization** - Improved memory and CPU usage across containerized services
- **FastAPI Backend** - Added new FastAPI docker container with MongoDB connection for data ingestion (Qdrant and Neo4j planned next release)
- **API Documentation** - Implemented automatic Swagger documentation for the API endpoints

#### Messaging System Integration
- **Kafka Integration** - Added Apache Kafka for distributed messaging and event streaming
- **Event-Driven Architecture** - Established foundation for event-driven data processing
- **Producer/Consumer Framework** - Created infrastructure for asynchronous data flow between components
- **Confluent Platform** - Implemented industry-standard Kafka ecosystem components
- **Kafka UI** - Added modern web interface for Kafka management and monitoring

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
