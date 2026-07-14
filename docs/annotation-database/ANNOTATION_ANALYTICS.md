# Annotation Analytics

Source: `backend/app/services/annotation_analytics_service.py`,
`GET /api/annotations/analytics/summary`.

Every metric is computed live from real `Annotation`/`AnnotationReview`
rows for the requesting tenant — never a fabricated or hardcoded figure.
Where there isn't enough data to compute a metric meaningfully (e.g. zero
reviewed annotations), the function returns `None`/an empty collection
rather than a misleading zero.

| Metric | Function | What it measures |
|---|---|---|
| Reviewer Agreement | `reviewer_agreement()` | Overall and per-reviewer-pair agreement rate across all completed reviews |
| Reviewer Accuracy | `reviewer_accuracy()` | Each reviewer's submitted-label match rate against the final ACTIVE Ground Truth label |
| Common Findings | `common_findings()` | Most frequent `primary_observation` values |
| Finding Distribution | `finding_distribution()` | Full count-per-label breakdown |
| Unknown Frequency | `unknown_frequency()` | Rate of `unknown_flag = True` annotations |
| Class Balance | `class_balance()` | Label counts + minority-class ratio |
| Dataset Growth | `dataset_growth()` | Annotation count per calendar day, from real `created_at` timestamps |
| Annotation Velocity | `annotation_velocity()` | Average annotations per reviewer per day they were active |

No metric here projects, forecasts, or interpolates — every number is a
direct aggregation of existing rows.
