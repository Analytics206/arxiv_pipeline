# ArXiv Pipeline Development Notes

This document contains personal development notes and reminders for ongoing work on the ArXiv pipeline project.

## To-Do Items

### Vector Processing & Tracking

- Add synchronization between Qdrant and MongoDB tracking:
  - This sync needs to run before the sync_qdrant pipeline inserts new papers into Qdrant but in same process
  - If papers exist in Qdrant but not in `vector_processed_pdfs`, insert entries into MongoDB
  - If papers exist in `vector_processed_pdfs` but not in Qdrant, remove the tracking entries
  - Implement within the `sync_qdrant_with_tracking()` function in `src/pipeline/sync_qdrant.py`

### GPU Optimization

- Test performance with different GPU devices and batch sizes
- Consider adding a fallback mechanism for when GPU memory is insufficient
- Benchmark and document performance improvements

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
