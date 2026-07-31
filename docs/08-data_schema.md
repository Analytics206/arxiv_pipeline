# Active MongoDB data schema

## Canonical research data

| Collection | Role |
| --- | --- |
| `papers` | Latest canonical arXiv metadata and PDF state by versionless paper ID |
| `papers_archive` | Superseded paper versions |
| `arxiv_kaggle` | Category-filtered metadata discovery corpus |
| `paper_analyses` | Immutable evidence-backed analysis versions |

## Search evaluation traces

| Collection | Identity | Role |
| --- | --- | --- |
| `research_search_runs` | `request_id` | Request, caller, lifecycle, timing, and returned target summary |
| `research_search_source_pulls` | `request_id + source` | Exact evidence/discovery candidates before fusion |
| `research_search_outputs` | `request_id` | Exact curated response delivered to the caller |

These collections are append-only evaluation history and never influence read
ranking.

## External harness feedback

`harness_feedback` stores one immutable document per client-generated
`feedback_id`. A unique index makes transport retries successful no-ops.

Each document retains the feedback record as received, including unknown
extension fields, plus:

- `schema_version`, `received_at`, client, project, contract, and taxonomy
  provenance;
- the optional `request_id` and `subject.point_id` used to verify the target
  against the immutable `research_search_outputs` response before insertion;
- `reason_known`, `reason_group`, and `signal_scope`;
- a normalized `resolved_paper_id` when the subject has a paper;
- `resolved_ingestion_sources`, drawn from `papers`, `arxiv_kaggle`, and
  `paper_analyses` when that paper currently resolves.

An unresolved paper is still stored. Project-relative signals including
`not_project_fit`, `transfer_risk`, and `already_covered` use
`signal_scope="project_only"` and must never enter global paper-quality
metrics.

Indexes cover `feedback_id`, `request_id`, `subject.paper_id`,
`subject.point_id`, `reason`, `project.id`, `occurred_at`, and the compound
ingestion-source/reason/project rollup.

The API has no feedback update or delete route. Corrections and later trial
outcomes are new records connected with `follow_up_of`.
