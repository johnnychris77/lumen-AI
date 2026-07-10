# AI-Assisted RCA Engine

Codename: Project Guardian · LumenAI Quality v2.9

## The existing constraint this had to respect

`root_cause_service.py` (v1.5) already establishes, in its own docstring,
that root cause is "categorized by probable root cause only by a human —
never inferred automatically, since guessing 'why' a finding occurred
without a human judgment would be a fabricated causal claim." That
constraint predates this sprint and isn't renegotiable by it.

## How the draft/approval split honors that

`RCADraft` (`rca_engine_service.py`) is an AI-*drafted* analysis — never a
`RootCauseAssignment`. It generates:

- `likely_process_stage` — derived from the event's SPD taxonomy category
  (e.g. `organic_residue` → "Manual Cleaning")
- `evidence` — the original narrative, classification result, and every
  tracked correlation found
- `contributing_factors` — real signals only: incomplete inspection
  coverage, missing approved baseline, prior repair history
  (`readiness_engine.has_repair_history`), elevated event severity
- `historical_recurrence_count` — count of same-finding-type events in the
  trailing 90 days
- `similar_events` — reuses `similar_case_finder_service.find_similar_cases`
  when an inspection is correlated (same instrument *family* + finding
  type), falling back to recent same-finding-type quality events otherwise
- `investigation_questions` — a fixed template per taxonomy category

A supervisor edits the draft (`PATCH .../rca-drafts/{id}`) and either:

- **Approves** it with a `root_cause` from the existing `ROOT_CAUSES`
  vocabulary — this calls `root_cause_service.assign_root_cause` directly,
  creating the one real, human-confirmed `RootCauseAssignment`. Approval is
  rejected with 422 if no inspection was correlated — a root cause
  assignment is meaningless without a real inspection to attach to.
- **Rejects** it with a reason — the draft is marked `rejected` and no
  `RootCauseAssignment` is ever created.

The engine itself never writes a `RootCauseAssignment`. It only ever
proposes; a human decides.
