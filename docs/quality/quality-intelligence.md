# Quality Intelligence (v1.5)

## What it does
Turns every inspection into measurable quality-improvement intelligence:
volume, pass/reclean/repair/remove-from-service rates, supervisor override
rate, baseline and coverage compliance, and AI confidence trend — plus
finding trends by type and time period, anatomy zone risk, instrument family
performance, and per-technician/per-supervisor quality rollups.

Distinct from the existing `quality_intelligence_service.py` (Phase 21),
which tracks network-wide emerging-risk signals across hospitals via mocked
data. v1.5 is per-tenant, real-data-only, and lives under `/api/quality/*`
and the `/quality-dashboard` route to avoid colliding with that unrelated
feature.

## New persisted fields (Inspection)
- `disposition` — the clinical_decision.overall_result computed at analysis
  time (PASS/MONITOR/SUPERVISOR REVIEW/REPROCESS/REMOVE FROM SERVICE),
  persisted so pass/reclean/remove-from-service rates don't require
  re-deriving analysis for every dashboard load.
- `coverage_pct` / `coverage_quality` — the Inspection Coverage Engine's
  result at submission time, persisted for coverage-compliance reporting.

## New table: InspectionFinding
Inspection only stores the rolled-up disposition — not which individual
finding types were detected. `InspectionFinding` logs one row per actionable
finding (severity_index >= 1) at analysis time: finding type, anatomy zone,
instrument type, severity. This is the real data source behind Finding Trend
Intelligence, the Anatomy Risk Dashboard, and Instrument Family Performance —
nothing in those dashboards is derived from a single rolled-up field or
fabricated.

## Dashboard endpoint
`GET /api/quality/dashboard?period=day|week|month|quarter|year|all_time`
returns the KPI set for the requested window. A metric with no underlying
data returns `null`, never a fabricated zero.
