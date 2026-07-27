# Embedding Model Benchmark v2

## Decision

Keep `mxbai-embed-large:latest` as the production dense component. It is now
served from the evaluated `research_knowledge_hybrid_v1` collection alongside
sparse lexical retrieval.

`nomic-embed-text:v1.5` is the best efficiency fallback: it matched the
baseline's positive and grouped recall while using 59% less model storage,
indexing 47% faster, and answering 23% faster. It did not replace the baseline
because its cross-paper relevant results ranked substantially lower and its
unrelated-query score separation was weaker.

Do not switch production to Qwen3 Embedding or EmbeddingGemma from this result.
Both improved parts of cross-paper retrieval, but each missed paper-scoped
answers and was roughly four times slower per query on the current RTX 2070
Mobile.

## Method

- Date: July 27, 2026
- Suite: `agent-research-retrieval-v2`
- Corpus: five immutable, source-verified AI-paper analyses
- Index contents: 350 evidence, claim, and implementation-idea points per model
- Cases: 38 total; 35 positive and 3 unanswerable controls
- Positive scopes: 26 paper-scoped, 6 corpus-discovery, and 3 cross-paper
- Hardware: RTX 2070 Mobile with 8 GB VRAM
- Runtime: shared Ollama `0.32.4`
- Vector store: one isolated Qdrant collection per model

The suite records immutable document hashes and exact evidence IDs. The runner
rejects stale hashes, missing evidence, or evidence assigned to the wrong
paper before indexing.

Each model uses its documented asymmetric retrieval format:

| Model | Query format | Document format |
| --- | --- | --- |
| `mxbai-embed-large:latest` | `Represent this sentence for searching relevant passages:` | none |
| `qwen3-embedding:0.6b` | `Instruct: ...` plus `Query:` | none |
| `embeddinggemma:latest` | `task: search result \| query:` | `title: none \| text:` |
| `nomic-embed-text:v1.5` | `search_query:` | `search_document:` |

These formats follow the
[Qwen3 Embedding model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B),
[EmbeddingGemma model card](https://huggingface.co/google/embeddinggemma-300m),
and
[Nomic Embed Text v1.5 model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5).
An initial uniform-prefix pilot was discarded as a model-selection benchmark
after it confirmed that asymmetric model instructions materially affect
quality.

## Results

| Model | Stored size | Dimensions | Index time | Positive hit rate | MRR | Group recall | Mean / p95 query | Score separation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `mxbai-embed-large:latest` | 639 MiB | 1,024 | 16.63 s | **1.000** | 0.905 | **0.947** | 63 / 85 ms | 0.189 |
| `qwen3-embedding:0.6b` | 610 MiB | 1,024 | 26.83 s | 0.943 | 0.875 | 0.921 | 251 / 294 ms | **0.299** |
| `embeddinggemma:latest` | 593 MiB | 768 | 25.46 s | 0.971 | **0.910** | **0.947** | 271 / 324 ms | 0.218 |
| `nomic-embed-text:v1.5` | **262 MiB** | 768 | **8.85 s** | **1.000** | 0.891 | **0.947** | **49 / 66 ms** | 0.127 |

`Positive hit rate` means at least one judged relevant evidence item appeared
within that case's limit. `Group recall` additionally requires all independent
evidence groups in a synthesis question. `Score separation` is the within-model
difference between mean first-relevant score and mean top score for the three
unanswerable controls; it is not yet a calibrated rejection threshold.

### Results by scope

| Model | Paper recall / MRR | Corpus recall / MRR | Cross-paper group recall / MRR |
| --- | ---: | ---: | ---: |
| `mxbai-embed-large:latest` | 1.000 / 0.904 | 1.000 / 1.000 | 0.667 / 0.722 |
| `qwen3-embedding:0.6b` | 0.923 / 0.885 | 1.000 / 0.917 | **0.833** / 0.704 |
| `embeddinggemma:latest` | 0.962 / **0.912** | 1.000 / 1.000 | **0.833** / **0.722** |
| `nomic-embed-text:v1.5` | 1.000 / **0.930** | 1.000 / 1.000 | 0.667 / 0.344 |

Dense retrieval is already reliable for corpus discovery in this small corpus.
Its weakness is evidence coverage across multiple papers:

- `cross-paper-validation-workflows` misses the RL-task-synthesis evidence with
  `mxbai` and Nomic.
- `cross-paper-structured-motion-representations` retrieves only one of the two
  required approaches with every model.
- Qwen misses two paper-scoped cases; EmbeddingGemma misses one.

The follow-up
[Hybrid Retrieval Benchmark v1](hybrid_retrieval_v1.md) recovered these exact
failures with dense/sparse fusion and diversity reranking. Graph retrieval is
not justified by the current evaluated corpus.

## Reproduce

Ensure the four models are installed in the shared Ollama service, then run:

```powershell
docker compose run --rm --no-deps app `
  python -m src.pipeline.benchmark_embeddings `
  --resume `
  --summary-only
```

The detailed report is written to the ignored runtime path
`data/retrieval_evals/embedding_benchmark_v2.json`. Use repeated `--model`
arguments to run only selected exact model tags. Each model writes to a
separate collection defined in
`evals/retrieval/embedding_models_v2.json`; never reuse one collection across
embedding spaces.

## Limitations

- Five papers and 38 cases are sufficient to expose regressions, not to claim a
  universal embedding winner.
- The three negative controls are useful diagnostics but insufficient to set a
  production abstention threshold.
- Timings are single-machine operational measurements, not standardized model
  throughput benchmarks.
- Expand the judgments as new papers and real harness questions enter the
  corpus, and rerun this report before any production model migration.
