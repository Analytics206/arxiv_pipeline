# Hybrid Retrieval Benchmark v1

## Decision

Promote `research_knowledge_hybrid_v1` as the active research collection with:

- `mxbai-embed-large:latest` dense vectors;
- stable hashed lexical term-frequency vectors with Qdrant-managed IDF;
- weighted reciprocal-rank fusion with dense weight `1.1` and sparse weight
  `1.0`;
- a `0.2` repeated-paper diversity penalty;
- at least 50 dense and 50 sparse candidates before fusion/reranking.

This strategy recovered both measured cross-paper failures within the API's
default top eight without losing any positive query.

## Evaluation

- Date: July 27, 2026
- Suite: `agent-research-retrieval-v2`
- Corpus: five immutable AI-paper analyses
- Points: 350 per collection
- Cases: 38 total; 35 positive and 3 unanswerable controls
- Dense baseline: `research_knowledge_v1`
- Hybrid candidate: `research_knowledge_hybrid_v1`
- Hardware: RTX 2070 Mobile, 8 GB VRAM
- Qdrant: 1.18.3

| Metric | Dense baseline | Selected hybrid |
| --- | ---: | ---: |
| Positive hit rate | 1.000 | 1.000 |
| Mean reciprocal rank | 0.905 | **0.933** |
| Group recall at case limit | 0.947 | **1.000** |
| Group recall at 5 | 0.921 | **0.974** |
| Group recall at 8 | 0.947 | **1.000** |
| Full-case group recall at 8 | 0.943 | **1.000** |
| Provenance completeness | 1.000 | 1.000 |
| Mean query latency | 74 ms | 77 ms |
| p95 query latency | 109 ms | **92 ms** |

Latency is a local operational measurement and varied modestly across repeated
runs. The important result is that hybrid retrieval added no material latency
at this corpus size.

## Target failures

| Case | Dense group ranks | Hybrid group ranks |
| --- | --- | --- |
| External validation across replication and RL task synthesis | `1, missing` | **`1, 3`** |
| Rendered robot trajectories and sparse rigid motion bases | `6, missing` | **`3, 7`** |

The third cross-paper case, incomplete observations, returned its independent
evidence groups at ranks 1 and 5 under the selected strategy.

## Design

Each Qdrant point has two named vectors:

- `dense`: the existing 1,024-dimensional Ollama embedding;
- `lexical`: stable hashed term-frequency features.

Qdrant applies collection-level inverse document frequency to the lexical
query, retrieves dense and lexical candidates independently, and combines them
with weighted reciprocal-rank fusion. A final provenance-preserving reranker
penalizes repeated selections from the same paper while retaining the fused
relevance score.

The candidate minimum is important. Evaluation cases can request 5, 8, or 12
results; retrieving at least 50 candidates makes the final top-eight behavior
independent of the requested output limit. This was verified against the live
API after deployment.

Hybrid scores are RRF rank scores, not cosine similarity percentages. The API
therefore publishes:

```json
{
  "retrieval_mode": "hybrid",
  "score_semantics": "rrf"
}
```

The web UI displays the final hybrid rank rather than presenting the raw RRF
score as a similarity percentage.

The implementation follows Qdrant's documented
[named dense/sparse hybrid search](https://qdrant.tech/documentation/search/text-search/hybrid-search/),
[IDF modifier](https://qdrant.tech/documentation/manage-data/indexing/#idf-modifier),
and
[weighted reciprocal-rank fusion](https://qdrant.tech/documentation/search/hybrid-queries/#reciprocal-rank-fusion).

## Reproduce

Build or reuse the hybrid collection and evaluate all recorded strategies:

```powershell
docker compose run --rm --no-deps app `
  python -m src.pipeline.benchmark_retrieval_strategies `
  --summary-only

# Subsequent tuning runs can reuse the existing collection.
docker compose run --rm --no-deps app `
  python -m src.pipeline.benchmark_retrieval_strategies `
  --skip-index `
  --summary-only
```

The detailed report is written to the ignored runtime path
`data/retrieval_evals/hybrid_strategies_v1.json`. Strategy definitions and the
selected strategy ID are versioned in
`evals/retrieval/hybrid_strategies_v1.json`.

## Interpretation

The observed failures were retrieval/ranking failures, not evidence that a
knowledge graph is required. Hybrid lexical recall plus diversity-aware
reranking recovered them. Neo4j should remain optional until a new reviewed
question fails this evaluated path and has a relationship structure that a
graph can plausibly improve.

The next agent-facing infrastructure work is token-budgeted context packaging
and the thin read-only MCP adapter.
