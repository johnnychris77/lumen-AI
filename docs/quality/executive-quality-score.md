# Executive Quality Score (v1.5)

## What it does
A single 0–100 score for leadership, computed from real data over the
trailing quarter for the requesting tenant.

## Weighted factors
| Factor | Weight | Source |
|---|---|---|
| Pass rate | 0.25 | `Inspection.disposition == "PASS"` |
| Coverage compliance | 0.15 | `Inspection.coverage_pct` |
| Supervisor agreement | 0.15 | `SupervisorReview.agreement == "agree"` |
| Low high-risk findings (inverted) | 0.15 | `100 - remove_from_service_rate` |
| Low repeat findings (inverted) | 0.10 | `100 - (repeated_error / supervisor_correction)` (CompetencyEvent) |
| Competency (education completion) | 0.10 | `education_completed / finding_reviewed` (CompetencyEvent) |
| Baseline compliance | 0.10 | `Inspection.baseline_status == "approved_baseline_found"` |

## Missing data is excluded, not defaulted
If a tenant has no data for a factor (e.g. no supervisor reviews yet), that
factor is dropped from the weighted average and the remaining weights are
renormalized — never defaulted to 0, 50, or 100. `factors_used` in the
response lists exactly which factors contributed, so the score is
auditable. If *no* factor has data, `score` is `null` with an explanatory
`note`, not a fabricated number.

## API
`GET /api/quality/executive-score` (leadership only).
