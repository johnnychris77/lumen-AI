# Model Validation Guide

**Status:** New this pass (Genesis). **Code:**
`backend/app/services/ml/dataset_integrity.py`,
`backend/app/services/ml/evaluation.py` (extended this pass),
`backend/app/services/ml/explainability.py`.
**Tests:** `backend/tests/test_candidate_model_training.py`.

## Dataset integrity (Section 4) — a reject-gate, not a filter

Distinct from `app.services.ml.dataset_builder.eligible_entries()` (which
*excludes* individual bad images and continues), `dataset_integrity`
*rejects the whole dataset* before training starts:

| Check | Function | Threshold |
|---|---|---|
| No duplicate images | `check_no_duplicate_images()` | zero repeated `image_sha256` |
| Facility diversity | `check_diversity()` | >= 2 distinct facilities |
| Manufacturer diversity | `check_diversity()` | >= 2 distinct manufacturers |
| Instrument diversity | `check_diversity()` | >= 2 distinct instrument families |
| No split leakage | `validate_split()` (reuses `dataset_split.has_no_group_leakage`) | zero groups spanning more than one split |
| Balanced train/validation/test | `check_class_balance()` per split | minority class >= 15% of that split |

A dataset failing any of these raises `DatasetInvalidError` (HTTP 422 at
the API layer) — training never proceeds against an invalid dataset.

## Evaluation metrics (Section 5)

`app.services.ml.evaluation.evaluate()` (pre-existing, reused) now reports,
per class: precision, recall, **sensitivity** (a clinical synonym for
recall, exposed under both names), **specificity**, F1, support, false-
positive rate, false-negative rate — plus the confusion matrix, macro
averages, and per-facility/per-manufacturer/per-instrument/per-anatomy
breakdowns (via the pre-existing generic `groups` parameter).

New this pass:

- `roc_curve()` / `roc_auc()` — already added in the Core Inspection
  Workflow Closure sprint; reused here.
- `pr_curve()` — precision-recall curve + average precision, for a binary
  0/1 ground truth against continuous scores. More informative than ROC
  when the positive class is rare (the common case for contamination/
  defect findings). Returns `average_precision: None` with a clear note
  when no positive example exists, rather than fabricating a curve.
- `calibration_report()` — see below.

## Confidence calibration (Section 7)

`app.services.ml.evaluation.calibration_report(y_correct, confidences)`
bins predictions into deciles and compares each bin's mean confidence to
its empirical accuracy:

- **Over-confident bin**: mean confidence exceeds empirical accuracy by
  more than 0.10.
- **Under-confident bin**: empirical accuracy exceeds mean confidence by
  more than 0.10.
- **Expected Calibration Error (ECE)**: the sample-weighted mean absolute
  gap across all non-empty bins.
- **Recommended threshold**: the lowest confidence value such that every
  bin at or above it meets a target accuracy (default 0.8) — `None`,
  honestly, when no confidence range achieves it. Never substitutes a
  default threshold in that case.

Empty bins (no predictions in that confidence range) are skipped entirely
— never assumed or interpolated.

## Explainability (Section 8)

`app.services.ml.explainability.explain_prediction()` returns exactly:
supported class, confidence, model version, image quality, known
limitations, the full supported-class list, and `human_review_required:
true`. It also returns `visual_explanation.available: False` with an
explicit note — **no saliency map or class-activation map is generated**,
because this pipeline has no real trained vision model with real gradients
to visualize. Fabricating a heatmap over a logistic-regression-on-pixel-
statistics model would misrepresent it as something it is not. If a future
model provides a real visual explanation, it must be labeled an
explanatory aid, never proof of causation (this section's explicit
instruction).

## Process

1. Train (see `MODEL_TRAINING_GUIDE.md`) — dataset integrity is checked
   automatically as the first two pipeline steps.
2. Evaluate on the held-out test split (or validation, if no test split
   exists in a small sample).
3. Review the error analysis (`ERROR_ANALYSIS.md`) and calibration report.
4. Record human sign-off via `PATCH /api/model-pipeline/models/{id}/
   candidate-flags` (`error_analysis_reviewed`,
   `reproducible_training_confirmed`, `governance_review_completed`).
5. Only then attempt promotion — see `MODEL_PROMOTION_POLICY.md`.
