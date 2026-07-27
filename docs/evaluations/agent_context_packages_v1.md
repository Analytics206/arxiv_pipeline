# Agent Context Package Evaluation v1

## Decision

The token-budgeted context package contract is ready for agent harness and
future MCP use on the current corpus. All 15 paper/profile combinations passed
the required invariants.

The complete `agent-context` response remains available for human review and
large-context workflows. `context-package` is the default machine surface.

## Contract

| Profile | Requested estimated tokens | Intended use |
| --- | ---: | --- |
| `brief` | 1,500 | Fast orientation or a constrained subagent |
| `standard` | 4,000 | Normal coding-agent planning and implementation work |
| `deep` | 8,000 | Full paper analysis when the harness has room |

An explicit `token_budget` from 512 through 32,768 overrides the profile size.
The selection policy remains `coding-agent-v1`. If that budget is below the
mandatory TLDR/evidence/provenance core, the API returns 422 with the
paper-specific minimum.

The estimator `utf8-bytes-div-4-v1` measures the compact serialized JSON using
one estimated token per four UTF-8 bytes. This keeps the service
provider-neutral and dependency-free. It is an estimate, not an exact token
count for Qwen, OpenAI, Anthropic, or another tokenizer; a harness may perform
an exact final count for its target model.

## Selection and safety invariants

The selector always keeps the TLDR and all evidence it references. It then
considers whole units in this order:

1. implementation ideas;
2. methods;
3. results;
4. limitations;
5. contributions;
6. problem statements;
7. concepts;
8. tags.

Each claim or idea is atomic with every verified evidence record it references.
Selection stops when the next complete unit does not fit. This fixed-prefix
behavior makes selection deterministic and monotonic as a budget grows.

Every response includes analysis/document provenance, realized budget use,
available/included/omitted counts, and an explicit `truncated` flag. A canonical
analysis with a dangling evidence ID is rejected instead of partially packaged.

## Corpus

The evaluation used the five current immutable analyses:

- `2607.22518`
- `2607.22535`
- `2607.22534`
- `2607.02134`
- `2607.21557`

Run:

```powershell
python -m src.pipeline.evaluate_context_packages `
  --paper-id 2607.22518 `
  --paper-id 2607.22535 `
  --paper-id 2607.22534 `
  --paper-id 2607.02134 `
  --paper-id 2607.21557
```

## Results

| Invariant | Result |
| --- | ---: |
| Budget compliance | 15/15 |
| Evidence closure | 15/15 |
| Repeat determinism | 15/15 |
| Analysis provenance | 15/15 |
| TLDR retention | 15/15 |
| Paper-level monotonicity across tiers | 5/5 |

| Profile | Mean estimated tokens | Maximum | Mean semantic-unit retention | Mean evidence retention | Complete packages |
| --- | ---: | ---: | ---: | ---: | ---: |
| `brief` | 1,418.2 | 1,467 | 14.4% | 30.3% | 0/5 |
| `standard` | 3,574.4 | 3,999 | 73.1% | 94.4% | 2/5 |
| `deep` | 3,916.8 | 5,412 | 100% | 100% | 5/5 |

Deep has room above the current maximum by design, allowing analyses to grow
without changing the public tier. Standard is the recommended harness default.
Brief deliberately prioritizes implementation ideas before general paper
description; callers needing only source facts can use search results or a
future evaluated focus policy instead of changing this versioned policy
silently.

The detailed machine report is generated at
`data/context_evals/agent_context_packages_v1.json` and is ignored as runtime
data.
