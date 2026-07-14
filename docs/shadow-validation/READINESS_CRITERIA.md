# Readiness Criteria

**Status:** New this pass (Shadow). **Code:**
`backend/app/services/ml/candidate_promotion.py` (extended),
`backend/app/services/ml/shadow_validation_metrics.py`,
`backend/app/services/ml/shadow_clinical_review_board.py`.
**Tests:** `backend/tests/test_shadow_validation.py`.

## §14 — the second, stage-scoped checklist

Genesis's `candidate_promotion.py` (Sprint 5) already gates every advance
beyond `Experimental` with an 8-item checklist
(`MODEL_PROMOTION_POLICY.md`). This program adds **4 additional items**,
required only when the target stage is `Validated Candidate` or later —
the base 8 items are completely unchanged, so the `Experimental ->
Candidate` transition Genesis's own tests exercise is unaffected:

```python
VALIDATED_CANDIDATE_CHECKLIST_ITEMS = [
    "inspection_volume_achieved",
    "performance_targets_met",
    "model_drift_acceptable",
    "clinical_review_board_approved",
]
```

| Item | Evidence source | Threshold |
|---|---|---|
| `inspection_volume_achieved` | `shadow_validation_metrics.shadow_go_no_go()` over this model's reconciled shadow predictions | >= 30 reconciled predictions |
| `performance_targets_met` | Same | Agreement rate >= 0.80 |
| `model_drift_acceptable` | `sentinel_ai_health_service._detect_drift()` (`MODEL_DRIFT_MONITORING.md`) | No drift detected |
| `clinical_review_board_approved` | `shadow_clinical_review_board.board_approved()` — the latest session's `approved` field | Must be explicitly `true`, never defaulted |

`evaluate_candidate_promotion()` merges these into the base checklist only
when `target_stage in {"Validated Candidate", "Pilot", "Production"}`:

```python
checklist = evaluate_candidate_checklist(db, model)
if target_stage in _STAGES_REQUIRING_SHADOW_EVIDENCE:
    checklist.update(evaluate_validated_candidate_checklist(db, model))
unmet = [item for item, ok in checklist.items() if not ok]
```

`GET /api/model-pipeline/models/{id}/validated-candidate-checklist` is a
read-only preview of both checklists against a model's current state.

## Why these specific thresholds

`inspection_volume_achieved`/`performance_targets_met` reuse the exact
threshold philosophy `app.services.ml.pilot_validation.go_no_go()`
already established for the deployed placeholder engine (`_MIN_REVIEWS =
30`, `_MIN_AGREEMENT_RATE = 0.80`) — the same conservative defaults,
applied to this candidate model's own shadow-mode evidence instead of the
placeholder engine's `SupervisorReview` rows. Reusing an established,
already-reviewed threshold rather than inventing a new one for Shadow.

## Never auto-promoted

Exactly as Genesis established: `evaluate_candidate_promotion()` always
returns the unmet items and requires an explicit human approver. Reaching
every item's `true` state is necessary but not sufficient — the route
only writes the new stage when a human calls
`POST /api/model-pipeline/models/{id}/candidate-promotion` with an
approver on record.

## Definition of done for this program

Reaching `Validated Candidate` means: the model has cleared its
inspection-volume and performance thresholds in real shadow-mode use,
shows no unexplained drift, and has been reviewed and approved by the
Clinical Review Board — on top of everything Genesis's own Candidate gate
already required. **This is still not clinical deployment.** Advancing to
`Pilot`/`Production` requires the pre-existing `deployment_gates.py`
ladder's own separate approval (`can_provide_advisory`/`can_drive_
clinical_recommendation`), which this program does not touch.
