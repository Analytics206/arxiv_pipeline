# 📘 Business Requirements Document (BRD)

## Project Name: ArXiv Local AI Research Pipeline

## 1. Overview
A modular, offline-capable pipeline that fetches and stores research papers from arXiv.org, beginning with the cs.AI category. Data will be structured in MongoDB, converted into a graph in Neo4j, and embedded into vector space using a Hugging Face model for indexing and search in Qdrant. The architecture is entirely local and open source. **All services will be containerized using Docker for local deployment and consistency.**

## 2. Goals
- Store and explore AI research papers with rich metadata.
- Create local-first infrastructure for graph-based and semantic exploration.
- Use modular components to allow category/model switching.
- Maintain all components and data sources within a single codebase.
- Use Docker containers to ensure repeatable local development and isolation of services.

## 3. Business Features

| BRD ID     | Feature Description | Linked PRD Requirement(s) |
|------------|---------------------|----------------------------|
| BRD-00     | Use Docker containers for all system components | FR-DCK-01 to FR-DCK-03 |
| BRD-01     | Ingest papers from arXiv in a configurable manner | FR-ING-01, FR-ING-02, FR-ING-03, FR-ING-04 |
| BRD-02     | Store and normalize metadata locally for querying | FR-DAT-01, FR-DAT-02, FR-DAT-03 |
| BRD-03     | Build author-paper-category graph | FR-GPH-01 to FR-GPH-05 |
| BRD-04     | Embed paper data using local models and index | FR-VEC-01 to FR-VEC-04 |
| BRD-05     | Central configuration to enable modularity | FR-CON-01 to FR-CON-03 |
| BRD-06     | Track system operation and errors | FR-LOG-01 to FR-LOG-03 |
| BRD-07     | Enable future expansion (PDFs, citations, UI) | FR-UI-01, FR-PDF-01, FR-REF-01, FR-CRON-01, FR-REP-01 |


