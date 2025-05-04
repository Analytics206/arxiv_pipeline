# ArXiv Pipeline Development Notes

This document contains developer notes and reminders for ongoing work on the ArXiv pipeline project.

## To-Do Items

### Vector Processing & Tracking

- Add synchronization between Qdrant and MongoDB tracking:
  - This sync needs to run before the sync_qdrant pipeline inserts new papers into Qdrant but in same process
  - If papers exist in Qdrant but not in MongoDB `vector_processed_pdfs`, insert entries into MongoDB
  - If papers exist in MongoDB `vector_processed_pdfs` but not in Qdrant, remove the tracking entries
  - Implement within the `sync_qdrant_with_tracking()` function in `src/pipeline/sync_qdrant.py`

### System monitoring with Prometheus/Grafana

The ArXiv pipeline project now includes a comprehensive monitoring solution using Prometheus and Grafana to track system and container metrics.

#### Overview

This monitoring stack consists of:
- **Prometheus**: Time series database for metrics collection and storage
- **Grafana**: Visualization platform for metrics dashboards
- **cAdvisor**: Container metrics collector
- **Node Exporter**: Host system metrics collector
- **MongoDB Exporter**: MongoDB-specific metrics collector

#### Setup Instructions

1. **Configuration Files**
   - Prometheus configuration: `config/prometheus/prometheus.yml`
   - Grafana dashboards: `config/grafana/dashboards/`
   - Grafana datasources: `config/grafana/datasources.yaml`
   - Docker Compose file: `docker-compose.monitoring.yml`

2. **Starting the Monitoring Stack**
   ```bash
   # Start the main ArXiv pipeline services
   docker-compose up -d
   
   # Start the monitoring stack
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

3. **Accessing Dashboards**
   - Prometheus UI: http://localhost:9090
   - Grafana UI: http://localhost:3001
     - Default credentials: admin/admin
     - Preconfigured dashboards:
       - Docker Containers: System-level view of container performance
       - System Metrics: Host machine metrics (CPU, memory, disk, network)

4. **Adding Custom Metrics**
   
   To expose custom metrics from the ArXiv pipeline application:
   
   ```python
   from prometheus_client import Counter, Gauge, start_http_server

   # Initialize metrics
   PAPERS_PROCESSED = Counter('papers_processed_total', 'Number of papers processed')
   VECTOR_PROCESSING_TIME = Gauge('vector_processing_seconds', 'Time taken to process vectors')
   
   # Start metrics server (typically in your app's main entry point)
   start_http_server(8000)
   
   # Update metrics in your code
   def process_paper(paper_id):
       start_time = time.time()
       # Processing logic
       PAPERS_PROCESSED.inc()
       VECTOR_PROCESSING_TIME.set(time.time() - start_time)
   ```

5. **Alert Configuration**
   
   To set up alerts for critical conditions:
   
   1. Create an alerting configuration in `config/prometheus/alerts.yml`
   2. Update the Prometheus configuration to include alerts
   3. Configure notification channels in Grafana (email, Slack, etc.)

#### Monitoring Best Practices

1. **Key Metrics to Monitor**
   - Container resource usage (CPU, memory)
   - Host system resources
   - MongoDB performance metrics
   - Application-specific metrics:
     - Paper processing rate
     - PDF download success/failure rate
     - Vector embedding generation times
     - Neo4j query performance

2. **Dashboard Organization**
   - System-level dashboards: Infrastructure health
   - Application-level dashboards: Business logic and performance
   - Service-specific dashboards: MongoDB, Neo4j, Qdrant

3. **Performance Optimization**
   - Use metrics to identify bottlenecks in the pipeline
   - Monitor GPU utilization for vector processing tasks
   - Track memory usage patterns for large embeddings operations

#### Completed Enhancements (May 4, 2025)

- ✓ **Vector Database Monitoring**: Added specific metrics for MongoDB and vector operations in the vector embedding dashboard
- ✓ **Comprehensive Dashboards**: Created multiple dashboards for tracking different aspects of the pipeline:
  - Basic test dashboard for monitoring system connectivity
  - Data science dashboard for core metrics
  - Advanced analytics dashboard for system correlation
  - Vector embedding dashboard for research paper processing
- ✓ **Documentation**: Created comprehensive Prometheus query documentation in several files:
  - prometheus_basic_queries.md
  - prometheus_queries.md
  - prometheus_custom_queries.md
  - prometheus_working_queries.md
- ✓ **Diagnostic Script**: Enhanced the check_prometheus_metrics.py script to verify dashboard queries

#### Future Enhancements

- Implement custom notifications for failed pipeline steps
- Add business metrics dashboards for research paper trends
- Set up automatic alerts based on performance thresholds
- Create custom metrics for paper processing stages

#### Troubleshooting

- If metrics aren't appearing, check Prometheus targets at http://localhost:9090/targets
- For container metrics issues, ensure cAdvisor has proper access to Docker socket
- Log metrics can be added using the Loki stack (consider adding in future updates)

### Documentation Updates
- Update README.md with new features and instructions
- Update business_requirements.md with new features and instructions
- Update product_requirements.md with new features and instructions
- Update system_design.md with new features and instructions
- Update release_notes.md with new features and instructions
- Update dev_notes.md with new features and instructions  
- Update tracker.md with new features and instructions

### GPU Optimization

- Test performance with different GPU devices and batch sizes
- Consider adding a fallback mechanism for when GPU memory is insufficient
- Benchmark and document performance improvements

### Web UI Improvements
- Add home page with navigation to graph(neo4j), search pages, mongodb, similarity search(qdrant)
- Add pipeline status page connected to mongodb tracking collection `vector_processed_pdfs`
- Add a search bar to the web UI to search for papers by title, author, or category, and load pdf
- Add a paper details page to the web UI to view paper metadata and vector embeddings
- Add a paper comparison page to the web UI to compare paper metadata and vector embeddings

### Deployment Improvements

- Create a script to easily switch between Docker and standalone Qdrant deployment
- Add monitoring for GPU usage and vector operation performance
- Document resource requirements for different dataset sizes

## Known Issues

- LangChain deprecation warnings need to be addressed
- Neo4j schema could be optimized for more efficient queries
- PDF chunking strategy might need refinement for better semantic search results

## Ideas for Future Development

- Consider implementing a more sophisticated tracking system that includes paper versions
- Explore adding OCR capabilities for better extraction of text from image-heavy PDFs
- Implement an analytics dashboard for tracking paper trends and statistics

---

*Last updated: May 4, 2025*
