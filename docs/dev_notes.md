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
  - Add docker container metrics to prometheus
  - Add system metrics to prometheus
  - Add grafana dashboard for docker container metrics
  - Add grafana dashboard for system metrics

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
