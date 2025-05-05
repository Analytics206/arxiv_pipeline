# ArXiv Pipeline Documentation

This directory contains comprehensive documentation for the ArXiv Pipeline project. Use this index to navigate through the various documentation files.

## Core Documentation

| Document | Description |
|----------|-------------|
| [system_design.md](./system_design.md) | Details the system architecture, design patterns, configuration options, and component relationships that comprise the ArXiv Pipeline. Includes sections on data organization, database integration, system monitoring, and pipeline components. |
| [tech_stack.md](./tech_stack.md) | Comprehensive overview of all technologies used in the project including infrastructure, monitoring, data storage, vector embeddings, APIs, and database schemas. Includes diagrams for system architecture and deployment options. |
| [release_notes.md](./release_notes.md) | Chronological record of all releases, with version details, features, enhancements, and dependencies for each update. Current version is 0.3.0 (May 4, 2025). |
| [business_requirements.md](./business_requirements.md) | Business requirements document (BRD) outlining the business goals, stakeholder needs, and success criteria for the project. |
| [product_requirements.md](./product_requirements.md) | Product requirements document (PRD) detailing specific product features, acceptance criteria, and prioritization. |

## Monitoring & Deployment Documentation

| Document | Description |
|----------|-------------|
| [prometheus_queries.md](./prometheus_queries.md) | Main reference guide for Prometheus queries used in monitoring the system. |
| [prometheus_basic_queries.md](./prometheus_basic_queries.md) | Simple Prometheus queries for troubleshooting and basic system monitoring. |
| [prometheus_custom_queries.md](./prometheus_custom_queries.md) | ArXiv pipeline-specific metrics and custom queries for monitoring application performance. |
| [prometheus_working_queries.md](./prometheus_working_queries.md) | Verified working queries that are currently implemented in dashboards. |
| [grafana_dashboard_guide.md](./grafana_dashboard_guide.md) | Instructions for customizing and managing Grafana dashboards for system monitoring. |
| [container_id_reference.md](./container_id_reference.md) | Reference guide for understanding container label formats and identification patterns. |
| [prometheus_id_format.md](./prometheus_id_format.md) | Documents the standardized format for Prometheus metric IDs and naming conventions. |
| [ollama_docker.md](./ollama_docker.md) | Instructions for running Ollama in a Docker container to enhance the ArXiv pipeline with image analysis capabilities. |

## Project Management & Analysis

| Document | Description |
|----------|-------------|
| [requirements_tracker.md](./requirements_tracker.md) | Tracking document for requirement implementation status and progress. |
| [dev_notes.md](./dev_notes.md) | Developer notes and informal documentation about ongoing development work. |
| [feedback_analysis.md](./feedback_analysis.md) | Comprehensive analysis of user feedback and feature requests with prioritized recommendations for product improvement. Includes quantitative usage metrics, qualitative feedback themes, and actionable development roadmap based on user needs. |
| [EmojiMe.md](./EmojiMe.md) | Emoji-based documentation or communication guidelines for the project. |
| [scratch.md](./scratch.md) | Working document for temporary notes and development ideas. |

## About This Documentation

The documentation in this repository follows these principles:

1. **Comprehensive Coverage**: Documentation covers technical, business, and operational aspects
2. **Chronological Tracking**: Release notes and version tracking provide historical record
3. **Clear Organization**: Documentation is categorized by purpose and target audience
4. **Technical Accuracy**: System specifications and configurations are precisely documented
5. **Ongoing Maintenance**: Documentation is updated alongside code changes

## Recent Major Developments

The most recent update (Version 0.3.0, May 4, 2025) added:

- **Interactive Database Testing**: Jupyter notebooks for testing connections and exploring database schemas
- **Comprehensive Monitoring**: Prometheus/Grafana monitoring stack with custom dashboards
- **Improved Documentation**: Enhanced documentation for monitoring and system components

## Guidelines for Documentation Contributors

When updating or adding documentation:

1. Follow the established formatting patterns
2. Update release_notes.md when adding new features
3. Keep system_design.md and tech_stack.md current with architectural changes
4. Use descriptive filenames that indicate document purpose
5. Ensure cross-references between documents are maintained

---

*This index was last updated: May 4, 2025*
