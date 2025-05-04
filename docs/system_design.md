# ArXiv Pipeline System Design

## Overview

This document tracks the system design features, architectural decisions, and implementation details of the ArXiv Research Pipeline. It serves as a reference for design patterns, configuration options, and system behaviors that may not be explicitly documented in the BRD or PRD.

## Document Purpose

Unlike the Business Requirements Document (BRD) and Product Requirements Document (PRD), this document focuses on:

1. Technical implementation details
2. System architecture decisions
3. Design patterns used in the codebase
4. Configuration options and their impacts
5. Data flow between system components

## System Design Features

### Configuration Management

| Feature | Description | Implementation Date |
|---------|-------------|---------------------|
| Centralized YAML Configuration | All system settings stored in `config/default.yaml` | Initial |
| Environment Variable Override | Environment variables can override configuration settings (e.g., `MONGO_URI`) | Initial |
| Configuration Loading Utilities | Common utilities for loading configuration across services | May 2025 |

### Data Organization

| Feature | Description | Implementation Date |
|---------|-------------|---------------------|
| Category-Based PDF Storage | PDFs are automatically organized in subdirectories by primary arXiv category | May 3, 2025 |
| Paper Limit Per Category | Configurable limit on number of papers to download per category | May 3, 2025 |
| Incremental Download Tracking | Download limits apply only to newly downloaded papers | May 3, 2025 |
| Automatic Directory Creation | System automatically creates directory structures as needed | May 3, 2025 |

### Database Integration

| Feature | Description | Implementation Date |
|---------|-------------|---------------------|
| MongoDB Storage | Paper metadata stored in MongoDB | Initial |
| Neo4j Graph Database | Paper relationships represented in Neo4j | Initial |
| Qdrant Vector Database | Paper content vectorized and stored in Qdrant | Initial |
| Selective Vector Processing | Only specific categories are processed into vector database | May 3, 2025 |
| Vector PDF Processing Tracking | MongoDB-based tracking in vector_processed_pdfs collection to prevent duplicate vector processing | May 4, 2025 |
| Qdrant-MongoDB Sync | Synchronization between Qdrant contents and MongoDB tracking | May 4, 2025 |
| GPU Acceleration | Support for GPU-accelerated vector operations in Qdrant and embeddings | May 4, 2025 |
| Multi-GPU Support | Configurable GPU device selection for performance optimization | May 4, 2025 |

### System Monitoring

| Feature | Description | Implementation Date |
|---------|-------------|---------------------|
| Prometheus Metrics | Time series database for metrics collection and storage | May 4, 2025 |
| Grafana Dashboards | Visualization platform for metrics with preconfigured dashboards | May 4, 2025 |
| Container Monitoring | Container metrics collection using cAdvisor | May 4, 2025 |
| System Metrics | Host system metrics collection using Node Exporter | May 4, 2025 |
| MongoDB Metrics | Database-specific monitoring using MongoDB Exporter | May 4, 2025 |
| Custom Application Metrics | Python Prometheus client for application-specific metrics | May 4, 2025 |
| Separate Docker Compose | Isolated monitoring stack via docker-compose.monitoring.yml | May 4, 2025 |

### Pipeline Components

| Feature | Description | Implementation Date |
|---------|-------------|---------------------|
| ArXiv Ingestion | Fetches metadata from ArXiv API | Initial |
| PDF Downloader | Downloads PDFs based on database records | Initial |
| PDF Processor | Extracts and processes PDF content for vector database | Initial |
| Neo4j Synchronizer | Synchronizes MongoDB data to Neo4j graph | Initial |
| Web UI | Browser-based interface for exploring data | Initial |

## Design Decisions

### Module-Based Execution

The system supports both direct script execution and module-based execution patterns:
- Module execution pattern (`python -m src.module.script`) is preferred
- This pattern properly handles package imports and dependencies
- The system is designed as a proper Python package structure

### Docker Containerization

- Each service runs in its own Docker container
- Data persistence handled via Docker volumes
- Inter-service communication via Docker network
- Configuration mounted from host to containers

### PDF Processing Flow

1. ArXiv API → MongoDB (metadata storage)
2. MongoDB → Local PDF Storage (organized by category)
3. Local PDFs → Qdrant Vector DB (selective by category)
4. MongoDB → Neo4j (graph relationships)

## Monitoring Architecture

The monitoring system follows a sidecar pattern with the following components:

1. **Prometheus**: Central metrics collection service
   - Scrapes metrics from all system components
   - Stores time-series data with retention policies
   - Configuration in `config/prometheus/prometheus.yml`

2. **Grafana**: Visualization and dashboard platform
   - Auto-provisioned dashboards in `config/grafana/dashboards/`
   - Preconfigured Prometheus datasource
   - Accessible on port 3001 to avoid conflict with Web UI

3. **Exporters**: Purpose-built metrics collectors
   - cAdvisor: Container resource usage metrics
   - Node Exporter: Host system metrics
   - MongoDB Exporter: Database performance metrics

4. **Application Metrics**: Custom instrumentation points
   - Papers processed counter
   - Processing time measurements
   - Success/failure rate tracking

## Future Design Considerations

- Asynchronous processing pipeline
- Event-driven architecture for better component decoupling
- Improved error handling and retry mechanisms
- Performance optimization for large-scale paper collections
- Automated alerts based on monitoring thresholds

---

*This document is maintained alongside code changes to track design decisions and system architecture evolution.*
