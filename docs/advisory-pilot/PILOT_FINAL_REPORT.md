# Pilot Final Report

**Status:** New this pass (Advisor). **Code:**
`backend/app/services/ml/candidate_promotion.py` (extended),
`backend/app/routes/advisory_pilot.py::final_report`.
**API:** `GET /api/advisory-pilot/final-report?model_db_id={id}`.

## §13 — the Pilot -> Production promotion gate

Genesis's `candidate_promotion.py` (Sprint 5) already gates every advance
beyond `Experimental` with an 8-item base checklist, and Shadow (Phase 6)
added a 4-item checklist for advancing to Validated Candidate or beyond.
This program adds a **third, stage-scoped** checklist, required only when
the target stage is `Production` — the base 8 and Shadow's 4 are
unchanged, so earlier transitions are unaffected:

```python
PRODUCTION_CHECKLIST_ITEMS = [
    "safety_objectives_achieved",
    "performance_thresholds_met",
    "user_adoption_targets_met",
    "customer_approval",
]
```

`governance_approval` and `clinical_review_board_approved` are **not**
duplicated here — they're already required by the cumulative base and
Shadow checklists (`governance_review_completed`,
`clinical_review_board_approved`) that every Production promotion
inherits.

| Item | Evidence source | Threshold |
|---|---|---|
| `safety_objectives_achieved` | `advisory_safety_service.safety_objectives_achieved()` | Zero unreviewed `AdvisorySafetyEvent` rows of any severity |
| `performance_thresholds_met` | `pilot_validation.go_no_go()` over real `SupervisorReview` rows | `decision == "GO"` (>= 30 reviews, >= 0.80 agreement, safety FNR <= 0.05) |
| `user_adoption_targets_met` | `advisory_workflow_impact_service.adoption_rate()` | >= 0.60 adoption rate |
| `customer_approval` | `ModelRegistryEntry.customer_approved` | Explicit boolean, never defaulted true |

`performance_thresholds_met` reuses `pilot_validation.go_no_go()` — the
same readiness-gate philosophy as Shadow's `shadow_go_no_go()`, but over
**real, visible** `SupervisorReview` rows rather than Shadow's silent
predictions, since by the Pilot stage the model's recommendations are
actually shown and generating real supervisor reviews.

## The final report

`GET /api/advisory-pilot/final-report` assembles the complete evidence
package a Clinical Review Board (or customer/governance approver) needs,
read-only:

- The pilot dashboard (`PILOT_DASHBOARD_GUIDE.md`).
- Success metrics (`SUCCESS_METRICS.md`).
- The safety summary (`AdvisorySafetyEvent` rows).
- The user feedback summary (`USER_FEEDBACK_PLAN.md`).
- The Production promotion checklist preview.

## Clinical Review Board decision (§11)

The board's session (`ClinicalReviewBoardSession`, reused from Shadow)
records a `pilot_decision`: `continue | expand | pause | terminate` —
distinct from the `approved` field Shadow already uses for its own
Validated Candidate gate. A single review session can carry both
decisions independently.

## Never auto-promoted

Exactly as Genesis and Shadow established: `evaluate_candidate_promotion()`
always returns the unmet items and requires an explicit human approver.
Reaching every item's `true` state is necessary but not sufficient — a
human must still call `POST /api/model-pipeline/models/{id}/
candidate-promotion` with an approver on record.

## Definition of done

LumenAI has successfully completed a supervised advisory pilot. AI
recommendations were visible and explainable throughout. Human reviewers
retained full decision-making authority. Pilot outcomes demonstrate
measurable operational and clinical value — evidenced by this report —
providing the basis for a human decision about broader production
deployment. This report is evidence for that decision, not the decision
itself.
