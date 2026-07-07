# Clinical Decision Ledger & Explainable Inspection Timeline

## Clinical Decision Ledger

`app/models/clinical_decision_ledger.py::ClinicalDecisionLedgerEntry` — a
permanent, append-only record of every decision made about an inspection.
Entries are never edited or deleted; a correction is a new entry, the same
pattern already used for `AuditLog` and `PilotValidationCase`.

### What's recorded, per entry

| Field | Answers |
|---|---|
| `decision_type` | `ai_recommendation`, `supervisor_approval`, or `supervisor_override` |
| `made_by` | `"ai"`, or the reviewing supervisor's email |
| `rationale` | Why — the recommendation's explanation, or the supervisor's written rationale |
| `evidence_json` | The reasoning chain (for AI decisions) or the corrected fields/final disposition (for supervisor decisions) |
| `confidence` | The AI's confidence score, where applicable |
| `model_version`, `knowledge_graph_version`, `ontology_version`, `architecture_version`, `inspection_pipeline_version` | The governance snapshot **active at the moment this entry was created** — never recomputed from current constants after the fact |

### When entries are written

1. **`ai_recommendation`** — every time `run_cios_pipeline()` runs
   (`GET /api/cios/run/{id}`, and internally by the certificate generator),
   recording the Recommendation Agent's output.
2. **`supervisor_approval`** / **`supervisor_override`** — every time a
   supervisor submits `POST /inspections/{id}/supervisor-review`
   (`app/routes/ai_clinical_review.py`), alongside the existing
   `SupervisorReview` row and Phase 18 `PilotValidationCase`. One
   submission now produces three linked records: the review itself, the
   ground-truth label, and the permanent ledger entry — no duplicate data
   entry, and no decision goes unrecorded.

### Reading the ledger

`GET /api/cios/decision-ledger/{inspection_id}` returns every entry for
that inspection, oldest first — a complete "who decided what, when, with
what evidence, under which platform version" history for a single
instrument's clinical review.

## Explainable Inspection Timeline

`app/cios/orchestrator.py::_timeline` builds the timeline shown in the
CIOS run result:

```
[inspection.created_at]  Inspection created — <instrument> image captured.
[trace[0].timestamp]     Instrument Agent completed.
[trace[1].timestamp]     Anatomy Agent completed.
...
[trace[9].timestamp]     Enterprise Agent completed.
[review.created_at]      Supervisor agree (or: Supervisor disagree (override: ...))
```

Every timestamp here is real:

- `inspection.created_at` is the actual row-creation time.
- Each agent's timestamp is captured with `datetime.now(timezone.utc)` the
  moment that agent's `run()` call returns, during the *live* pipeline
  execution — genuine wall-clock time, just very close together in real
  seconds since these are synchronous, deterministic function calls, not
  the multi-minute human-paced gaps an illustrative example might suggest.
- The supervisor step's timestamp is the real `SupervisorReview.created_at`
  — which genuinely can be minutes or hours after the AI steps, since a
  human has to actually look at the case.

No timestamp on this timeline is fabricated or interpolated to make the
gaps look more realistic than they are. This is what makes the timeline
usable as audit evidence.
