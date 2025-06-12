# 📘 Business Requirements Document (BRD)

## 🏗️ Project Name: ArXiv Local AI Research Pipeline

## 🧭 1. Overview
A modular, offline-capable pipeline that fetches and stores research papers from arXiv.org, beginning with the cs.AI category. Data will be structured in MongoDB, converted into a graph in Neo4j, and embedded into vector space using a Hugging Face model for indexing and search in Qdrant. The architecture is entirely local and open source. **All services will be containerized using Docker for local deployment and consistency.**

## 🎯 2. Goals
- Store and explore AI research papers with rich metadata.
- Create local-first infrastructure for graph-based and semantic exploration.
- Use modular components to allow category/model switching.
- Maintain all components and data sources within a single codebase.
- Use Docker containers to ensure repeatable local development and isolation of services.

## 🗂️ 3. Business Features

| 🆔 BRD ID     | 📝 Feature Description | 🔗 Linked PRD Requirement(s) |
|------------|---------------------|----------------------------|
| 🐳 BRD-00     | Use Docker containers for all system components | FR-DCK-01 to FR-DCK-03 |
| 📥 BRD-01     | Ingest papers from arXiv in a configurable manner | FR-ING-01, FR-ING-02, FR-ING-03, FR-ING-04 |
| 💾 BRD-02     | Store and normalize metadata locally for querying | FR-DAT-01, FR-DAT-02, FR-DAT-03 |
| 🧩 BRD-03     | Build author-paper-category graph | FR-GPH-01 to FR-GPH-05 |
| 🧠 BRD-04     | Embed paper data using local models and index | FR-VEC-01 to FR-VEC-04 |
| ⚙️ BRD-05     | Central configuration to enable modularity | FR-CON-01 to FR-CON-03 |
| 📊 BRD-06     | Track system operation and errors | FR-LOG-01 to FR-LOG-03 |
| 🚀 BRD-07     | Enable future expansion (PDFs, citations, UI) | FR-UI-01, FR-PDF-01, FR-REF-01, FR-CRON-01, FR-REP-01 |
| 🖥️ BRD-08     | Web UI to explore graph/search | FR-UI-01 |
| 🧿 BRD-09     | System monitoring with Prometheus/Grafana | FR-MON-01 to FR-MON-05 |
| 🧪 BRD-10     | Interactive database exploration and testing via Jupyter notebooks | FR-REP-01, FR-REP-02 |
| ⚡ BRD-11     | GPU-accelerated vector search with dedicated remote setup | FR-VEC-05, FR-VEC-06, FR-VEC-07 |
| 📄 BRD-12     | PDF download and storage | FR-PDF-01 |
| 🤖 BRD-13     | LLM Evaluation Framework | FR-LLM-01 to FR-LLM-04 |
| 🤖 BRD-19     | Configurable AI Agent platform | FR-AGT-01 |
| 🖥️ BRD-14     | Web UI to start/stop pipelines, view logs, database status | FR-UI-02 |
| ⚙️ BRD-15     | Web UI to manage configurations for pipelines | FR-UI-03 |
| 🛰️ BRD-16     | Standalone deployment of key services on external machines | FR-DCK-04, FR-DCK-05, FR-DCK-06 |
| 📊 BRD-17     | Interactive data validation dashboards | FR-VAL-01, FR-VAL-02, FR-VAL-03, FR-VAL-04 |
| 📈 BRD-18     | Temporal analysis of paper publications with multi-dimensional filtering | FR-VAL-02, FR-VAL-03, FR-ANL-01 |
| 🛡️ BRD-20     | Data Governance and Compliance | FR-DGV-01 to FR-DGV-05 |
