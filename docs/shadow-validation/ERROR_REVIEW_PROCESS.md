# Error Review Process

**Status:** New this pass (Shadow). **Code:**
`backend/app/services/ml/shadow_error_review_queue.py`,
`backend/app/services/ml/shadow_comparison_engine.py`,
`backend/app/services/ml/shadow_failure_analysis.py`.

## The AI Comparison Engine (§4)

`shadow_comparison_engine.classify_comparison()` compares one shadow
prediction against the locked human ground truth and assigns exactly one
category:

| Category | Meaning |
|---|---|
| `agreement` | Predicted label matched the human final decision (confidence >= 0.55) |
| `low_confidence` | Matched, but confidence was below 0.55 — a calibration concern even though it agreed |
| `false_positive` | Human said no actionable finding; AI predicted one |
| `false_negative` | Human found a real issue; AI predicted no actionable finding — the safety-critical error |
| `disagreement` | Both sides named a real finding, just different ones |
| `unknown_pattern` | Prediction or ground truth was missing — nothing to compare |

This reuses `app.services.ml.error_analysis.NEGATIVE_LABEL` for the
positive/negative framing rather than a second definition.

## Every disagreement becomes a review item — not just safety-flagged ones

`shadow_error_review_queue.route_if_disagreement()` is called
automatically the moment a shadow prediction is revealed
(`shadow_mode.reveal_if_finalized()`). Any category other than
`agreement` creates a `ShadowErrorReviewItem` row — distinct from the
pre-existing `pilot_validation.safety_review_queue()`, which is a
computed, safety-only view with no persisted reviewer workflow.

## Review workflow

1. `GET /api/shadow-validation/error-review-queue` — list open items
   (image, human decision, AI prediction, confidence, comparison
   category).
2. A human reviewer examines the case and records comments plus a
   failure classification (`ERROR_ANALYSIS.md`'s vocabulary, extended —
   see below).
3. `POST /api/shadow-validation/error-review-queue/{id}/resolve` —
   records `reviewer_comments`, `failure_classification`, `resolved_by`,
   `resolved_at`, and sets `status: resolved`.

Every disagreement becomes a learning opportunity: resolved items feed
`shadow_failure_analysis.analyze_failures()` (`ERROR_REVIEW_PROCESS.md`'s
sibling doc, `MODEL_TRAINING_GUIDE.md`'s failure-analysis section) for
ranked failure causes and frequency trends.

## Failure classification vocabulary (§7)

`shadow_failure_analysis.py` reuses Genesis's `error_analysis.classify_
error()` for the five real-signal root causes it already computes (blur,
poor lighting, cropping, the anatomy-zone proxy, annotation disagreement),
relabeled into §7's vocabulary, and refines its `unknown_pattern`
catch-all with two new signals unique to the shadow-mode pilot context:

| §7 cause | Source |
|---|---|
| `poor_image_quality` | blur / poor lighting / cropping (Genesis, relabeled) |
| `ambiguous_anatomy` | anatomy-zone proxy (Genesis, relabeled) |
| `annotation_inconsistency` | annotation disagreement (Genesis, relabeled) |
| `model_limitation` | wrong despite adequate confidence, no other real signal — new |
| `workflow_issue` | an explicit, real workflow anomaly flag — new |
| `unknown_pattern` | the honest catch-all when nothing else applies |

No existing Genesis root cause is ever reclassified by this refinement —
only its `unknown_pattern` bucket is further split, using two new real
signals, never a guess.
