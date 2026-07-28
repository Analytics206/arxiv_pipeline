# Research Service Consumer-Quality Repair

Date: 2026-07-28

## Trigger

The external harness audited 194 distinct search chunks across ten queries and
reported four agent-blocking behaviors:

1. evidence resolution returned model-selected substrings cut at sentence
   boundaries;
2. implementation ideas flattened title, description, agent use, benefit, and
   a synthetic risk fallback into one repeated retrieval string;
3. `Risks: Not stated` was embedded as content;
4. RRF always returned nearest neighbors without a calibrated empty-result
   path or corpus coverage.

## Repair

- Stable evidence IDs still derive from the exact verified supporting
  substring.
- The public `quote` expands to the containing sentence(s) plus at most one
  surrounding sentence on each side, bounded to 1,200 characters.
- `supporting_quote` retains the exact matched substring and `truncated`
  identifies spans that cannot be reconstructed as prose.
- Truncated evidence and items left without complete evidence are omitted from
  the rebuildable index and normal token-budgeted contexts.
- Implementation ideas retain structured fields in Qdrant payload. One
  canonical description is displayed and embedded; null/sentinel risk strings
  are discarded.
- Weighted RRF keeps its raw score and adds a 0-1 agreement calibration. The
  strongest single-retriever rank-one contribution maps to zero and ideal
  dense/lexical rank-one agreement maps to one.
- The evaluated default `min_relevance=0.05` permits `hits=[]` with an explicit
  `no_match` reason. Callers may request zero for diagnostics.
- Search responses report total and filter-eligible paper/point coverage.

## Corpus migration

The dry run and write pass both validated every analysis against the exact PDF
hash before mutation.

| Measurement | Result |
| --- | ---: |
| Current papers | 53 |
| Evidence audited | 2,303 |
| Evidence expanded | 2,293 |
| Explicitly truncated/non-prose | 133 |
| Implementation ideas audited | 91 |
| PDF/hash failures | 0 |
| Qdrant schema | 2.1 |
| Indexed points after repair | 3,289 |

## Acceptance

- The reported `ev_dca959841d9d1cec51c6c8b1` reproduction now resolves to
  complete surrounding sentences and retains its original supporting quote.
- Twenty randomly sampled indexed evidence records all returned
  `truncated=false` and terminal punctuation.
- The unrelated query `zzzq wibble frobnicate purple monkey dishwasher`
  returned `result_status=no_match`, zero hits, and an explicit reason.
- The positive harness-RL query returned the expected OpenForgeRL claim with
  relevance `0.8766`.
- Implementation-idea search returned a single canonical text plus structured
  fields and no `Not stated` content.
- The live MCP validator passed tool discovery, read-only annotations, context,
  evidence, and resources under protocol `2025-11-25`.
- Automated suite: 76 tests passed.
