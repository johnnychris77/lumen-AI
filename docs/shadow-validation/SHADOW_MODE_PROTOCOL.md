# Shadow Mode Protocol

**Status:** New this pass (Shadow — Phase 6: Prospective Shadow-Mode
Clinical Validation). **Code:** `backend/app/services/ml/shadow_mode.py`,
`backend/app/models/shadow_prediction.py`,
`backend/app/services/workflow_state_service.py`.
**Tests:** `backend/tests/test_shadow_validation.py`.

## Mission

Validate the Genesis production-candidate model in real sterile
processing workflows **without influencing operational or clinical
decisions**. LumenAI observes. Humans decide. Every AI prediction is
compared against expert review only after that review is already locked.

## The workflow this program observes, unchanged

```
Technician performs normal inspection
        |
Supervisor completes review
        |
Final human decision is locked   <-- workflow reaches a TERMINAL STATE
        |
AI prediction is revealed internally
        |
Comparison is recorded
```

This is not a new workflow — it is the pre-existing inspection workflow
state machine (`app.services.workflow_state_service`, `Waiting ->
Assigned -> Image Capture -> AI Analysis -> Supervisor Review ->
{Reclean|Repair} -> Completed`, plus `Cancelled`). Shadow Mode adds no new
states and no new transitions to it. It only reads the existing state.

## The reveal gate — the single enforced invariant

A shadow prediction (`ShadowPrediction`, extended this pass with
`image_quality`/`anatomy_zone`/`instrument_family`/`facility_id`/
`comparison_category`/`revealed`/`revealed_at`) is recorded silently at
prediction time via `shadow_mode.record_shadow_prediction()` — exactly as
it was in the pre-existing Phase 17 §9 implementation.

The new function this pass adds, `shadow_mode.reveal_if_finalized()`, is
the only way a shadow prediction is ever reconciled or marked `revealed`:

```python
def reveal_if_finalized(db, row, *, insp, final_label):
    if insp is None or workflow_state_service.current_state(db, insp) not in workflow_state_service.TERMINAL_STATES:
        return row  # unchanged, still hidden
    row = reconcile_with_human(db, row, final_label)
    row.revealed = True
    row.revealed_at = datetime.now(timezone.utc)
    ...
    shadow_error_review_queue.route_if_disagreement(db, row)
    return row
```

Calling this before the inspection reaches `Completed`/`Cancelled` is a
**no-op** — the row comes back unchanged, still hidden. There is no code
path that reveals a shadow prediction, computes `agreed_with_human`, or
routes it to the error review queue before the human's own decision is
already recorded. `public_view()` (the API-facing shape) never returns the
predicted label — only that a shadow model ran (`clinical_recommendation_
shown: false`) and whether it has been revealed.

## No autonomous decision making

- No route in this program can write to `Inspection`, `SupervisorReview`,
  or `DispositionOverride`. It only *reads* the inspection's state and
  the shadow prediction it already stored.
- `POST /api/model-pipeline/shadow-predictions/{id}/reveal` takes a
  `final_label` the caller supplies (the already-recorded human decision)
  — it does not derive or infer one.
- Every dashboard/report/metric in this program carries
  `human_review_required: true`.

## API

- `POST /api/model-pipeline/shadow-predictions` (pre-existing, Phase 17) —
  record a silent prediction.
- `POST /api/model-pipeline/shadow-predictions/{id}/reveal` (new) —
  attempt the reveal; no-op until the inspection is finalized.
- `GET /api/model-pipeline/shadow-predictions/performance` (pre-existing)
  — aggregate agreement across all reconciled predictions.
- `GET /api/shadow-validation/dashboard` (new) — the full per-model
  Performance Dashboard (`MODEL_VALIDATION_GUIDE.md`'s sibling for
  Shadow, see `docs/shadow-validation/`).
