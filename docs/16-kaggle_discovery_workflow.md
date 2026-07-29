# Kaggle arXiv discovery workflow

## Outcome

The Kaggle corpus is a broad paper-discovery source. It does not replace the
curated, PDF-derived research index:

- `research_knowledge_hybrid_v1` contains evidence-backed claims, quotations,
  and implementation ideas.
- `arxiv_discovery_current` contains one lean title/abstract point per paper
  and returns explicitly labeled `metadata_only` leads.
- Federated search returns both tiers separately and removes metadata-only
  duplicates when an evidence-backed result exists for the same paper.

The retained MongoDB corpus is controlled by `kaggle_corpus` in
`config/default.yaml`. Category matching uses exact arXiv tokens, so `cs.AI`
does not accidentally match a longer value. The default policy retains papers
with any of `cs.AI`, `cs.CV`, or `cs.LG`; its date filter is disabled.

## Safe post-import sequence

The preparation command owns the sequence: count, guard, rebuild, validate,
index MongoDB, atomically replace the production collection, build/resume the
physical Qdrant collection, validate its count, and finally activate the stable
Qdrant alias.

Preview the category cleanup without writing:

```powershell
python -m src.pipeline.prepare_kaggle_corpus
```

Apply only the MongoDB cleanup:

```powershell
python -m src.pipeline.prepare_kaggle_corpus --apply
```

Apply cleanup and build the complete discovery index:

```powershell
python -m src.pipeline.prepare_kaggle_corpus --apply --index
```

The indexer is resumable. A bounded smoke pass does not activate the alias:

```powershell
python -m src.pipeline.index_arxiv_discovery --max-papers 32
python -m src.pipeline.index_arxiv_discovery
```

The equivalent container entry point is read-only unless `--apply` is passed:

```powershell
docker compose --profile manual run --rm prepare-kaggle
docker compose --profile manual run --rm prepare-kaggle --apply --index
```

Repeated `--category` arguments override the configured category list for one
run:

```powershell
python -m src.pipeline.prepare_kaggle_corpus --apply `
  --category cs.AI --category cs.LG
```

## Replacement safety

Before any destructive replacement, the cleanup reports:

- source and retained counts;
- exact selected categories and optional date window;
- number and fraction that would be removed;
- retention-guard failures.

The default guard permits a retained fraction from 1% through 30%. An apply is
rejected when the result is empty or outside that range. A successful apply:

1. Writes filtered and normalized documents to a run-specific temporary
   collection using a server-side aggregation.
2. Verifies the expected count, policy conformance, required `id`, `title`, and
   `abstract` fields, and unique arXiv IDs.
3. Creates these MongoDB indexes on the temporary collection:
   - unique `id`;
   - `category_codes, update_date`;
   - descending `update_date`.
4. Atomically renames the temporary collection over the production target.

The original production collection remains unchanged if filtering, validation,
or indexing fails. A failed temporary collection is deliberately retained for
inspection. Cleanup run state is stored in `ingestion_stats`.

## Daily full-import hook

For the current one-time cleanup, both `import_collection` and
`collection_name` are `arxiv_kaggle`, so the command filters the imported
collection in place through an atomic replacement.

For future daily refreshes, import the full dataset into a staging collection
such as `arxiv_kaggle_import`, then set:

```yaml
kaggle_corpus:
  import_collection: "arxiv_kaggle_import"
  collection_name: "arxiv_kaggle"
```

The same preparation command will read staging and replace only the filtered
production collection. This keeps the previous production MongoDB collection
and Qdrant alias live until their replacements are fully validated. Import
scheduling is intentionally separate; the post-import command is the stable
hook a scheduler can call later.

## Discovery index contract

Each paper produces a deterministic Qdrant point containing:

- a dense title/abstract embedding;
- an IDF sparse title/abstract vector;
- versionless arXiv ID, title, categories, primary category, update date/year,
  latest version, corpus run ID, and metadata hash.

Abstracts and author details stay in MongoDB and are hydrated only for returned
hits. This avoids duplicating the full text payload across roughly half a
million Qdrant points.

Physical collection names include a hash of the cleaned corpus snapshot,
embedding model, and schema version. Progress is checkpointed in MongoDB
`discovery_index_runs`. The `arxiv_discovery_current` alias moves only after
the physical point count exactly matches the cleaned source count.

## Query and evaluation surfaces

REST/OpenAPI and MCP expose:

- `search_research`: evidence-backed research only;
- `search_paper_discovery`: broad metadata-only candidates;
- `search_federated_research`: both tiers, kept separate.

Run the smoke evaluation after alias activation:

```powershell
python -m src.pipeline.evaluate_discovery `
  --suite evals/discovery/arxiv_kaggle_smoke_v1.json `
  --output data/evaluations/arxiv_kaggle_smoke_v1.json
```

The report includes recall at the requested limit, mean reciprocal rank,
negative no-match rate, and latency.
