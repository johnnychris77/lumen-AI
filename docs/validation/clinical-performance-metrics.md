# Clinical Performance Metrics — Phase 18

All metrics below are computed live from supervisor-adjudicated
`pilot_validation_cases` rows (`app/services/pilot_validation_service.py`).
None are fabricated or simulated; with zero adjudicated cases a rate is
returned as `null`, never as a misleading `0.0`.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/pilot-validation/metrics` | Clinical performance metrics + critical safety metrics. |
| `GET /api/pilot-validation/zone-performance` | Per-zone performance breakdown. |
| `GET /api/pilot-validation/dashboard` | Full pilot dashboard payload (`/pilot-validation` page). |

## Core Confusion-Matrix Metrics

Computed over all *adjudicated* cases (label is `tp`, `tn`, `fp`, or `fn` —
`inconclusive` cases are excluded from rate denominators but reported
separately as `inconclusive_count`).

| Metric | Formula |
|---|---|
| Accuracy | `(TP + TN) / (TP + TN + FP + FN)` |
| Precision | `TP / (TP + FP)` |
| Recall (sensitivity) | `TP / (TP + FN)` |
| F1 | `2 · precision · recall / (precision + recall)` |
| False positive rate | `FP / (FP + TN)` |
| False negative rate | `FN / (FN + TP)` |
| Supervisor agreement rate | `(TP + TN) / adjudicated` — fraction of cases where the AI prediction matched the supervisor's confirmed finding. |
| Override rate | Fraction of dispositioned cases where the supervisor's `final_disposition` differs from `ai_recommended_disposition`. |

## Confidence Calibration

Cases are bucketed into 20-point confidence deciles (0–20%, 20–40%, …,
80–100%). For each non-empty bucket the report returns:

- `mean_confidence` — average `ai_confidence` in the bucket
- `observed_accuracy` — fraction of TP+TN in that bucket

A well-calibrated model has `observed_accuracy` tracking `mean_confidence`
closely across buckets. Large gaps (e.g. 90%-confidence cases that are only
60% accurate) indicate the model is overconfident and should inform the
go/no-go decision and next training priorities.

## Critical Safety Metrics

The single highest-priority set of numbers in this phase. Computed
per critical finding type — **blood, tissue, organic residue, crack,
missing component** — plus an overall critical false-negative rate:

```
false_negative_rate(type) = FN(type) / (FN(type) + TP(type))
```

Each type's result includes `meets_safety_threshold`, evaluated against
`CRITICAL_FN_RATE_THRESHOLD` (currently 5%, see
`docs/validation/pilot-go-no-go-criteria.md`).

## Zone Performance Metrics

Per zone (serrations, grooves, drill-bit flutes, threaded regions, o-ring
areas, rigid scope ports, lumens, box locks, hinges, ratchets, insulation
edges):

| Field | Meaning |
|---|---|
| `case_count` | Cases reviewed in this zone. |
| `missed_count` | False negatives in this zone. |
| `miss_rate` | `missed_count / adjudicated_count_for_zone`. |
| `accuracy` | `(TP + TN) / adjudicated_count_for_zone`. |
| `mean_confidence` | Average AI confidence for cases in this zone. |
| `override_count` / `override_rate` | How often the supervisor corrected the zone assignment. |

The dashboard surfaces four derived views from this table:

- **Most common missed zones** — highest `missed_count`.
- **Highest-risk zones** — all zones in the high-retention taxonomy
  (all 11 tracked zones are treated as high-risk per existing SPD
  zone-retention guidance in `app/services/instrument_zones.py`).
- **Lowest-confidence zones** — lowest `mean_confidence`.
- **Highest-override zones** — highest `override_count`.

## Instrument-Family Performance

Cases are also grouped by `instrument_family` with `case_count`,
`missed_count`, and `accuracy`, so the dashboard can show whether a specific
instrument family (e.g., rigid scopes) is systematically underperforming.

## Human Review

Every metrics payload includes `human_review_required: true` and, where
applicable, a disclaimer that findings are quality indicators, not clinical
diagnoses, and that association does not imply causation — consistent with
platform-wide policy.
