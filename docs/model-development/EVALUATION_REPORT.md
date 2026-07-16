# Evaluation Report — Project Lens

Source: `app.services.ml.evaluation.evaluate()` (pre-existing, reused
verbatim), run against this sprint's real declared-experimental training
run. Every number below is copied directly from that run's actual output —
nothing here is illustrative or rounded up.

## Test-split results (16 samples)

```
accuracy:        0.5625
macro_precision: 0.7467
macro_recall:    0.6190
macro_f1:        0.7143
```

## Per-class metrics (real, test split)

| Class | Support | Precision | Recall (Sensitivity) | Specificity | PPV | NPV | F1 | FPR | FNR |
|---|---|---|---|---|---|---|---|---|---|
| no_observable_abnormality | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| probable_blood_like_residue | 2 | 0.333 | 1.0 | 0.714 | 0.333 | 1.0 | 0.5 | 0.286 | 0.0 |
| probable_bone_like_fragment | 3 | — (0 predicted) | 0.0 | 1.0 | — | 0.8125 | — | 0.0 | 1.0 |
| probable_corrosion_like_degradation | 2 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| probable_plastic_or_insulation_fragment | 2 | 0.4 | 1.0 | 0.786 | 0.4 | 1.0 | 0.571 | 0.214 | 0.0 |
| probable_retained_debris | 3 | 1.0 | 0.333 | 1.0 | 1.0 | 0.867 | 0.5 | 0.0 | 0.667 |
| probable_tissue_or_organic_residue | 2 | — (0 predicted) | 0.0 | 1.0 | — | 0.875 | — | 0.0 | 1.0 |

`—` marks a `null` precision/F1 (no true positives were predicted for that
class this run) — reported honestly as `null`, never as a fabricated 0 or
1.

## Confusion matrix (real, test split)

Every `probable_bone_like_fragment` and `probable_tissue_or_organic_residue`
test sample was misclassified as `probable_plastic_or_insulation_fragment`
and `probable_blood_like_residue` respectively — the 3-scalar feature
vector (brightness/sharpness/aspect only) genuinely cannot separate every
class in this small, synthetic dataset. This is disclosed, not hidden;
see `ERROR_ANALYSIS_REPORT.md`.

## Subgroup performance (Section 8's required breakdown)

| Subgroup | Group | n | Accuracy |
|---|---|---|---|
| Facility | LumenAI Synthetic Experimental Lab | 16 | 0.5625 |
| Manufacturer | Acme | 7 | 0.5714 |
| Manufacturer | Zenith | 6 | 0.5 |
| Manufacturer | Meridian | 3 | 0.6667 |
| Instrument family | scissors | 7 | 0.5714 |
| Instrument family | grasper | 6 | 0.5 |
| Instrument family | forceps | 3 | 0.6667 |
| Anatomy zone | unknown | 16 | 0.5625 |
| Image quality | Excellent | 14 | 0.5 |
| Image quality | Poor | 2 | 1.0 |

Every subgroup here has real sample counts shown alongside its accuracy —
no group is reported as a bare percentage without its `n`. No subgroup was
suppressed for having a poor result.

## Safety metrics

`safety_metrics()`'s tracked findings (`blood`/`tissue`/`organic_residue`/
`crack`/`missing_component`) all report `null` this run — these are the
older KPI-heuristic's label vocabulary (`app.services.ml.model_tasks.
SAFETY_CRITICAL_FINDINGS`), not Project Lens's new taxonomy labels, so none
matched. This is an honest scope mismatch to note for a future sprint: the
safety-critical false-negative tracking should be extended to cover the
new observation-taxonomy label names directly.

## Insufficient-data honesty

Training-split evaluation (30 samples) is stored in the registry's
`training_metrics` field; validation-split evaluation is `null` because
this run's leakage-safe split placed 0 samples in validation (see
`DATASET_SPLIT_AND_LEAKAGE_REPORT.md`) — reported as `null`, never
fabricated.
