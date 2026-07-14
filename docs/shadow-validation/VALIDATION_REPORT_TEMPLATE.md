# Validation Report Template

**Status:** New this pass (Shadow). **Code:**
`backend/app/services/ml/shadow_reports.py`.
**API:** `GET /api/shadow-validation/reports/{report_type}`.

## Reproducibility (§15)

Every report carries a common envelope:

```json
{
  "report_type": "...",
  "generated_at": "2026-...",
  "period": {"start": "...", "end": "..."}
}
```

Re-running the same report against the same stored rows and the same
`period_start`/`period_end` produces byte-for-byte identical content —
nothing in this module samples randomly or reads a clock-dependent source
other than `generated_at` itself and the explicit period bounds passed
in.

## The seven reports (§12)

| Report | `report_type` | Built from |
|---|---|---|
| Weekly Validation Report | `weekly` | `shadow_dashboard.performance_dashboard()`, scoped to `period_start`/`period_end` |
| Monthly Validation Report | `monthly` | Same, over a wider period |
| Performance Summary | `performance-summary` | `shadow_dashboard.performance_dashboard()` |
| Error Analysis Report | `error-analysis` | `shadow_failure_analysis.analyze_failures()` over the error review queue |
| Failure Trend Report | `failure-trend` | Ranked failure causes + frequency trend over time |
| Pilot Progress Report | `pilot-progress` | `pilot_service.get_pilot_status()` + `shadow_validation_metrics.validated_metrics()` |
| Clinical Review Summary | `clinical-review-summary` | Every `ClinicalReviewBoardSession` for the model |

`weekly`/`monthly` require explicit `period_start`/`period_end` — there is
no implicit "last 7 days" default, since silently assuming a window would
make the report non-reproducible against a fixed period.

## Composition, not duplication

Every report function in `shadow_reports.py` calls into an existing
Shadow service (`shadow_dashboard`, `shadow_failure_analysis`,
`shadow_validation_metrics`, `shadow_clinical_review_board`) — none of
them recompute a metric a sibling module already owns.
