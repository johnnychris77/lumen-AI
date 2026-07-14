# Error Analysis

**Status:** New this pass (Genesis). **Code:**
`backend/app/services/ml/error_analysis.py`.
**Tests:** `backend/tests/test_candidate_model_training.py::TestErrorAnalysis`.

## Error types

Every misclassified prediction is assigned exactly one `error_type`, using
`no_actionable_finding` as the negative class (consistent with the
platform-wide safety framing that a missed real finding is the more
dangerous error):

| `error_type` | Meaning |
|---|---|
| `false_positive` | Truth was `no_actionable_finding`; model predicted a finding |
| `false_negative` | Truth was a real finding; model predicted `no_actionable_finding` — the safety-critical error |
| `misclassification_between_findings` | Truth and prediction were both real findings, just the wrong one |

## Root causes — every one from a real, already-available signal

| `root_cause` | Real signal used | Priority |
|---|---|---|
| `annotation_disagreement` | `DoubleBlindReview.agreement is False` for that image — the ground truth itself was disputed, not necessarily a model error | 1 (checked first) |
| `blur` | `ImageQualityAssessment.blur_flag` or `.focus_flag` (real, Pillow-computed edge-energy variance) | 2 |
| `poor_lighting` | `ImageQualityAssessment.lighting_flag` or `.exposure_flag` (real, computed mean brightness) | 3 |
| `cropping_or_resolution_issue` | `ImageQualityAssessment.cropping_flag` | 4 |
| `incorrect_anatomy` | The image's `anatomy_zone` was not identified (blank/unknown) — **a proxy**, not a true anatomy-classifier disagreement, since no per-sample anatomy ground truth exists to compare against. Documented here explicitly as a proxy, not overclaimed. | 5 |
| `model_uncertainty` | The model's own reported confidence was below 0.55 | 6 |
| `unknown_pattern` | No other real signal explains the error — the honest catch-all | 7 (last resort) |

Each error gets exactly one root cause: the first matching signal in
priority order above, so a blurry image with low confidence is attributed
to `blur` (the more actionable, correctable signal) rather than
`model_uncertainty`.

## Ranked failure modes

`app.services.ml.error_analysis.analyze_errors(samples)` returns:

```json
{
  "total_samples": 24,
  "total_errors": 3,
  "error_rate": 0.125,
  "error_type_counts": {"false_negative": 1, "false_positive": 1, "misclassification_between_findings": 1},
  "ranked_failure_modes": [
    {"root_cause": "blur", "count": 2, "share_of_errors": 0.667},
    {"root_cause": "model_uncertainty", "count": 1, "share_of_errors": 0.333}
  ],
  "errors": ["... per-error detail records ..."]
}
```

`ranked_failure_modes` is sorted by frequency — the highest-count root
cause is the most actionable finding for the next data-collection or
labeling cycle (e.g. "2 of 3 errors this run were attributable to blur —
review image-capture guidance/lighting at the affected facility").

## Review workflow

Every candidate model's error analysis report is persisted on
`ModelRegistryEntry.error_analysis_report` and surfaced in the Validation
Package (`GET /api/model-pipeline/models/{id}/validation-package`). A human
reviewer marks `error_analysis_reviewed: true` via `PATCH .../candidate-flags`
once they have examined the ranked failure modes — this flag is one of the
8 required items in the Candidate promotion gate (`MODEL_PROMOTION_POLICY.md`).
