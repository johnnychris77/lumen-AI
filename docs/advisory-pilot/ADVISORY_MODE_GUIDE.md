# Advisory Mode Guide

**Status:** New this pass (Advisor — Phase 7: Supervised Advisory Pilot &
Human-AI Collaboration). **Code:**
`backend/app/services/advisory_recommendation_service.py`,
`backend/app/models/advisory_pilot.py` (`AdvisoryRecommendationInteraction`).
**Tests:** `backend/tests/test_advisory_pilot.py`.

## Mission

Deploy the validated-candidate model into a controlled pilot where AI
recommendations are **visible** to users but all clinical and operational
decisions remain under human authority. No autonomous actions. No
automatic approvals. No automatic disposition decisions.

## The workflow (§1)

```
Technician
    |
Upload Image
    |
AI Analysis
    |
Visible Recommendation      <-- advisory_recommendation_service.present_recommendation()
    |
Technician Decision         <-- advisory_recommendation_service.record_interaction()
    |
Supervisor Review           <-- pre-existing SupervisorReview (unchanged)
    |
Final Human Decision
```

The AI may recommend. Humans decide. This program adds no new AI
inference and no new autonomous action anywhere in this chain — it adds
visibility (the recommendation is shown, where Shadow Mode kept it
hidden) and a new, technician-facing decision record.

## Why a new interaction table, not `SupervisorReview`

`SupervisorReview` is the pre-existing supervisor/manager-only
AI-agreement store — role-gated to `admin`/`spd_manager`, and already
consumed by `pilot_validation.py`, `ground_truth.py`, and competency
scoring. No existing table let the **technician** who receives the
recommendation act on it directly; their role previously ended at
capture/submission. `AdvisoryRecommendationInteraction` fills exactly
that gap, as a distinct actor and a distinct table — never conflated
with the supervisor's own, later review.

## Recommendation presentation (§3)

`present_recommendation()` wraps the pinned Genesis contract
(`app.services.ml.explainability.explain_prediction()`) directly rather
than building a second one — its exact field list (supported finding,
confidence, model version, image quality, known limitations, human
review requirement) already matches §3's requirements. It adds:

- `evidence_summary` — a caller-supplied summary of what the model based
  its recommendation on.
- `abstained` — `True` when confidence is below the same
  `error_analysis.LOW_CONFIDENCE_THRESHOLD` Genesis already uses, or the
  predicted class isn't supported — reusing an existing threshold, not
  introducing a new tunable.
- `recommendation_disclaimer` — a fixed string making explicit that this
  is a recommendation, never a definitive conclusion.

A recommendation is **never** presented without `human_review_required:
true` and the disclaimer text.

## Interaction logging (§4)

`record_interaction()` writes one `AdvisoryRecommendationInteraction` row
per technician decision: `decision` (`accepted`/`modified`/`rejected`),
`modified_to`, `reason_for_rejection`, `reviewer_comments`,
`user_confidence_rating` (1-5, nullable — never defaulted), and
`time_to_decision_seconds` — computed from the inspection's own
`AI_ANALYSIS` `WorkflowStateEvent` timestamp
(`app.services.workflow_state_service`) to now, reusing the existing
append-only workflow log rather than adding a new stopwatch field.

## API

- `POST /api/advisory-pilot/recommendations/present` — compute the
  presentation for a prediction.
- `POST /api/advisory-pilot/recommendations/respond` — record a
  technician's decision (roles: admin/spd_manager/operator).
- `GET /api/advisory-pilot/recommendations` — list interactions.
