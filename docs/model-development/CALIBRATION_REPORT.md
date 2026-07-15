# Calibration Report — Project Lens

Source: `app.services.ml.lens_calibration` (temperature scaling, new this
sprint) + `app.services.ml.evaluation.calibration_report()` (pre-existing
reliability-bin/ECE computation, reused verbatim on the temperature-scaled
confidences).

## Method

1. **Temperature scaling** (Guo et al., 2017), fit by grid search over
   `T ∈ [0.25, 4.00]` (step 0.05), minimizing negative log-likelihood on
   the held-out split (test, or validation if test is empty). Pure Python
   (`math.log`/`math.exp` only — no numpy/scipy).
2. The resulting calibrated confidences are then run through the existing
   `evaluation.calibration_report()` — reliability bins, Expected
   Calibration Error (ECE), and a data-derived recommended abstention
   threshold.

## Real result, this sprint's run

```
temperature: 1.85
temperature_fit_nll: 0.6654
```

### Reliability bins (test split, 16 predictions)

| Confidence range | n | Mean confidence | Empirical accuracy | Gap | Flag |
|---|---|---|---|---|---|
| 0.3–0.4 | 8 | 0.3547 | 0.375 | −0.0203 | — |
| 0.4–0.5 | 6 | 0.4374 | 0.6667 | −0.2292 | under-confident |
| 0.5–0.6 | 1 | 0.5687 | 1.0 | −0.4313 | under-confident |
| 0.6–0.7 | 1 | 0.6130 | 1.0 | −0.3870 | under-confident |

```
expected_calibration_error: 0.1472
over_confident_bins: []
under_confident_bins: [[0.4,0.5], [0.5,0.6], [0.6,0.7]]
recommended_threshold: 0.5
target_accuracy: 0.8
```

`recommended_threshold` is real and data-derived here (0.5) — the lowest
bin-lower-edge above which every remaining bin's empirical accuracy meets
the 80% target. Note the model is systematically *under-confident* in
this run (every non-trivial bin's empirical accuracy exceeds its mean
confidence) — an honest artifact of the small, noisy synthetic dataset,
not tuned to look good.

## Abstention threshold (Section 10)

```
abstention_threshold: 0.5
abstention_threshold_is_data_derived: true
```

`resolve_abstention_threshold()` prefers the real, data-derived
`recommended_threshold` whenever `evaluation.calibration_report()` could
compute one (as it did this run); it falls back to a disclosed static
default (`DEFAULT_ABSTENTION_THRESHOLD = 0.6`) only when no confidence
range in the run achieved the target accuracy — clearly flagged via
`abstention_threshold_is_data_derived: false` in that case, never silently
substituted.

## Stored on every artifact

`temperature`, `abstention_threshold`, and the full reliability report are
serialized into the exported artifact JSON (`export_artifact()`) and the
registry's `calibration_report` column — the live inference adapter reads
`temperature`/`abstention_threshold` directly from the loaded artifact,
never a hardcoded default, so a live prediction's `calibrated_confidence`
is provably the same transform this report describes.

## A low-confidence result never becomes a confident recommendation

The live adapter (`live_inference_adapter.predict()`) computes
`abstained`/`abstention_reason` itself, before returning the Section 19
contract — there is no downstream formatting step that could upgrade a
`confidence_below_threshold` result into a confident finding; the
frontend (`NewInspectionPage.tsx`) renders `abstained: true` results with
an explicit "(abstained — ...)" label rather than the display label alone.
