# Kaggle arXiv discovery workflow

## Outcome

The Kaggle corpus is a broad paper-discovery source. It does not replace the
curated, PDF-derived research index:

- `research_knowledge_hybrid_v1` contains evidence-backed claims, quotations,
  and implementation ideas.
- `arxiv_discovery_current` contains one lean title/abstract point for each
  Kaggle paper whose versionless ID also exists in the curated MongoDB
  `papers` collection, and returns explicitly labeled `metadata_only` leads.
- Federated search returns both tiers separately and removes metadata-only
  duplicates when an evidence-backed result exists for the same paper.

The retained MongoDB corpus categories come only from the comma-separated
`KAGGLE_RETAINED_CATEGORIES` value in `.env`. Other cleanup policy and safety
settings remain under `kaggle_corpus` in `config/default.yaml`. Category
matching uses exact arXiv tokens, so `cs.AI` does not accidentally match a
longer value. The date filter is disabled by default.

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

Apply cleanup and build the complete discovery index only when explicitly
wanted:

```powershell
python -m src.pipeline.prepare_kaggle_corpus --apply --index
```

Discovery indexing does not embed the whole cleaned Kaggle collection. Its
source snapshot is the exact intersection of `arxiv_kaggle.id` and
`papers.base_arxiv_id`. Cleanup never removes the nonmatching Kaggle records;
they remain available in MongoDB. The intersection count and ID hash are part
of the physical Qdrant collection identity, so changing `papers` selects a new
physical collection instead of resuming an incompatible checkpoint.

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

After MongoDB cleanup has already completed, run the restartable
discovery-only worker in the background:

```powershell
docker compose --profile manual up -d index-kaggle
docker compose --profile manual logs -f index-kaggle
```

`index-kaggle` resumes from `discovery_index_runs` after a transient failure.
It restarts only on failure and remains stopped after successful completion.

Set the category list once in `.env` before previewing or applying cleanup:

```dotenv
KAGGLE_RETAINED_CATEGORIES=<comma-separated exact category tokens>
```

The cleanup commands fail closed when this value is absent or empty.

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

Each paper in the MongoDB intersection produces a deterministic Qdrant point
containing:

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

Qdrant uses the Docker-managed `qdrant_native_data` volume. Keep active Qdrant
storage off Windows/OneDrive bind mounts: Qdrant segment optimization depends
on atomic filesystem renames, which those mounts can intermittently reject.
The legacy `qdrant_data` bind-volume declaration is retained only as a
non-destructive rollback source for existing installations.

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
