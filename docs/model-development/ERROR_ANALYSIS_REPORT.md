# Error Analysis Report — Project Lens

Source: `app.services.ml.error_analysis.analyze_errors()` (pre-existing,
reused verbatim), run against this sprint's real test-split predictions.

## Real result, this sprint's run

```
total_samples: 16
total_errors:  7
error_rate:    0.4375
error_type_counts:
  misclassification_between_findings: 7
ranked_failure_modes:
  - root_cause: model_uncertainty
    count: 7
    share_of_errors: 1.0
```

Every error this run was a misclassification between two supported
categories (no false positives against `no_observable_abnormality`, no
false negatives that dropped an abnormal finding to "no observable
abnormality" — the confusion matrix in `EVALUATION_REPORT.md` shows all 7
errors land within the abnormal-category space: `probable_bone_like_
fragment`→`probable_plastic_or_insulation_fragment`,
`probable_tissue_or_organic_residue`→`probable_blood_like_residue`,
`probable_retained_debris`→`probable_blood_like_residue`).

`_root_cause()`'s real, checkable-signal-based classification
(`annotation_disagreement`/`blur`/`poor_lighting`/`cropping_or_resolution_
issue`/`incorrect_anatomy`/`model_uncertainty`/`unknown_pattern`)
attributed all 7 errors to `model_uncertainty` — none of the more specific
real signals (annotation disagreement, image-quality flags, missing
anatomy zone) applied to any of them, so the honest catch-all before
`unknown_pattern` fired. This is expected for this dataset: the underlying
cause is the feature vector's real limitation (3 hand-engineered scalars
— brightness/sharpness/aspect ratio — cannot separate visually similar
synthetic brightness/texture profiles), not any of the specific data-
quality issues this classifier checks for.

## Human review of contamination-relevant false negatives

Per Section 9's requirement that false negatives involving probable
contamination receive explicit human review: this run had **zero**
`no_observable_abnormality` false negatives (a contamination case
misclassified as "no observable abnormality" would be the most
safety-relevant error type) — every error was a confusion between two
non-negative abnormal categories. `MANUAL_MODEL_ACCEPTANCE.md`'s Case 4
records this class's real per-class metrics for human review alongside
the rest of the walkthrough.

## Known limitation of this analysis

`error_analysis.py`'s `NEGATIVE_LABEL` constant is hardcoded to
`"no_actionable_finding"` (the older Genesis-sprint taxonomy), not
Project Lens's `"no_observable_abnormality"` — this means `_error_type()`'s
false_positive/false_negative distinction (which compares against that
literal string) does not correctly recognize Project Lens's negative
class, so every error this run was categorized as
`misclassification_between_findings` even where one side was the negative
class. This is disclosed here rather than silently producing a
mislabeled `error_type` — a future sprint should either parameterize
`error_analysis.py`'s negative label or give Project Lens its own thin
wrapper that translates labels before calling it.
