# Inspection State Machine

`app/cios/state_machine.py` formalizes the states every inspection passes
through.

## States

```
NEW
    ↓
IMAGE_CAPTURED
    ↓
INSTRUMENT_IDENTIFIED
    ↓
ANATOMY_IDENTIFIED
    ↓
BASELINE_LOADED
    ↓
COVERAGE_VALIDATED
    ↓
ANALYZED
    ↓
CLINICAL_REVIEW
    ↓
SUPERVISOR_PENDING
    ↓
APPROVED  or  REQUIRES_ACTION
    ↓
COMPLETE
```

`is_valid_transition(from_state, to_state)` encodes the only legal edges —
`SUPERVISOR_PENDING` is the sole branch point (to `APPROVED` or
`REQUIRES_ACTION`), and both of those lead only to `COMPLETE`.

## Honest derivation — not fabricated history

`derive_state(inspection, review=None)` computes the **current** state and
the ordered list of **states reached** from real, persisted fields
(`has_image`, `score_status`, `baseline_status`, `supervisor_review_required`,
`status`, and the linked `SupervisorReview` if one exists).

**Important limitation, stated plainly:** in the current implementation,
`INSTRUMENT_IDENTIFIED`, `ANATOMY_IDENTIFIED`, `BASELINE_LOADED`, and
`COVERAGE_VALIDATED` all happen inside one synchronous call to
`analyze_inspection()` (`baseline_comparison_scoring_service.py`) at
inspection-creation time. There is no separate persisted timestamp for
"anatomy was identified" distinct from "baseline was loaded" — they
happen in the same database transaction. `derive_state()` reports these
as *reached* (they are real facts — the anatomy resolver really did run,
the baseline really was checked) but does not fabricate individual
historical timestamps for each one. Where a real distinct timestamp does
exist — image/inspection creation (`created_at`), and a live CIOS pipeline
run's actual per-agent execution times — those are used directly (see
`docs/cios/lumenai-clinical-intelligence-operating-system.md` and the
Explainable Inspection Timeline in `app/cios/orchestrator.py::_timeline`).

## State mapping

| Inspection condition | State |
|---|---|
| No image, `score_status == "pending"` | `NEW` |
| Has image, `score_status == "pending"` | `IMAGE_CAPTURED` |
| `score_status` is `scored`/`supervisor_review_required`, no review yet, not flagged for review | `ANALYZED` |
| Same, but flagged `supervisor_review_required` | `SUPERVISOR_PENDING` |
| Same, but a `SupervisorReview` exists (no override, agreement not "disagree") | `APPROVED` (reached via `CLINICAL_REVIEW`/`SUPERVISOR_PENDING`) |
| Same, but the review has an override or `agreement == "disagree"` | `REQUIRES_ACTION` |
| `Inspection.status` is `reviewed`/`closed` and a review exists | `COMPLETE` |

## Auditability

Every CIOS pipeline run (`GET /api/cios/run/{id}` or
`GET /api/cios/state/{id}`) recomputes state live from the current
database — there is no separate "state" column that could drift from the
underlying facts. This is the same "derive, don't duplicate" pattern
already used for Phase 20's `classify_readiness()` and Phase 18's ground-
truth labels: a single source of truth (the real `Inspection`/
`SupervisorReview` rows), computed fresh on every read.
