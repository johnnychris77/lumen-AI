# Safety Metrics (Phase 17)

In SPD, the most dangerous model error is a **false negative** on contamination
or structural failure — a missed hazard that reaches a patient. These metrics
are tracked explicitly and gate promotion. Source: `app.services.ml.evaluation`.

## Standard metrics

Per task: accuracy, per-class precision / recall / F1, false-positive rate,
false-negative rate, confusion matrix, and performance breakdowns by instrument
family, anatomy zone, finding type, and severity. Plus supervisor agreement rate
(from `SupervisorReview` + shadow reconciliation).

## Safety-critical false-negative rates

Tracked for the findings whose misses matter most:

- **blood** false-negative rate
- **tissue** false-negative rate
- **organic residue** false-negative rate
- **crack** false-negative rate
- **missing component** false-negative rate

`safety_metrics()` also reports `worst_safety_false_negative_rate` across these.

FNR = (present but predicted otherwise) / (all actually present). A value of
`0.0` means no hazards of that class were missed on the evaluation set; `null`
means the class had no positive examples (not "safe" — just untested).

## Gate

`safety_false_negative_within_threshold` is a required checklist item for
**validated** promotion. A model with an unreviewed or out-of-threshold safety
FNR cannot support a workflow decision. Thresholds are set per deployment during
the human `false_negative_review` step and recorded in the model's
`known_limitations`.

## Honesty

Metrics are computed only from provided `(y_true, y_pred)` pairs — never
simulated. Until a real model and labeled test set exist, these functions have
nothing to score and the registry entry stays `experimental` with empty metrics.
