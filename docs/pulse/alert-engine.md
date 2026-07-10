# Project Pulse — Alert Engine

LumenAI OS v4.2 — Section 5

## A new table, because the shape genuinely differs

`PulseAlert` is a new table — distinct from Atlas's system-scoped
`EnterpriseAlert` narrative and Sentinel's entity-risk
`ClinicalWatchlistEntry` — because Section 5 asks for a specific shape
(`evidence`, `confidence`, `recommendation`, `suggested_owner`) neither
existing alert model carries as first-class fields. Detection logic
itself reuses existing engines wherever one already exists (AI
Confidence Drop reuses Sentinel's own drift detector directly), and
follows the same idempotent `_already_active` check-then-create pattern
every other alert/recommendation engine in this codebase already uses,
so repeated generation calls never create duplicate active alerts.

## The eight alert types

| Alert | Detection |
|---|---|
| Critical Blood Trend | Real `InspectionFinding` rate for `finding_type="blood"`, last 7 days vs. prior 23-day baseline, flagged at >1.5x |
| Corrosion Spike | Same trend detector, `finding_type="corrosion"` |
| AI Confidence Drop | `sentinel_ai_health_service._detect_drift` — reused directly, not re-derived |
| Repeated Supervisor Overrides | Real `SupervisorReview.override_action` non-empty rate over the last 7 days, flagged at ≥25% |
| Missing Baseline | Real `Inspection.baseline_status == "not_checked"` rate over the last 7 days, flagged at ≥20% |
| Repair Surge | Real `RepairRequest` volume, last 7 days vs. baseline weekly rate, flagged at >1.5x |
| Coverage Decline | Real `Inspection.coverage_pct` average, last 7 days vs. prior baseline, flagged at ≥15% relative decline |
| Knowledge Gap | Real high-severity `InspectionFinding` count with zero `KnowledgeArticle` rows created in the same 30-day window |

Every detector requires a minimum real sample size (`_MIN_SAMPLE = 5`)
before evaluating a trend — a tenant with too little data simply
produces no alert, never a fabricated one from a tiny sample.

## Endpoints

```
POST /api/pulse/alerts/generate         — run all eight detectors for the caller's tenant
GET  /api/pulse/alerts                  — list (filterable by status/alert_type)
POST /api/pulse/alerts/{id}/acknowledge
POST /api/pulse/alerts/{id}/resolve
```

Every alert carries `human_review_required` semantics implicitly via
this platform's disclaimer convention — recommendations use "possible
contributing factor" / "quality review recommended" language throughout,
never a causation claim.
