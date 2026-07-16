# Pilot Dashboard Guide

**Status:** New this pass (Advisor). **Code:**
`backend/app/services/advisory_pilot_dashboard_service.py`.
**API:** `GET /api/advisory-pilot/dashboard`.

## Composition, not duplication

`pilot_dashboard()` composes the other Advisor services exactly as
Shadow's `shadow_reports.py` established as this codebase's pattern —
nothing here recomputes a metric a sibling service already owns:

| §9 field | Source |
|---|---|
| `pilot_status` | `pilot_service.get_pilot_status()` (only when a `facility_id` is supplied) |
| `inspection_volume` | `advisory_workflow_impact_service.adoption_rate()`'s `total_eligible_inspections` |
| `adoption` | `advisory_workflow_impact_service.adoption_rate()` |
| `acceptance_rate` / `override_rate` | `advisory_workflow_impact_service.acceptance_and_override_rates()` |
| `performance_trends` | `quality_dashboard_service.dashboard_summary()` |
| `safety_events` | `advisory_safety_service.safety_summary()` |
| `operational_impact` | `sla_monitoring_service.sla_monitoring()` |

## Parameters

- `model_id` (optional) — scope interaction-derived metrics (adoption,
  acceptance/override rate) to one candidate model.
- `facility_id` (optional) — include that facility's `pilot_status`; the
  other fields are tenant-scoped regardless, since inspection volume/
  turnaround/safety events aren't yet split per-facility anywhere in this
  codebase.

## Reading the dashboard

`acceptance_rate`/`override_rate` are complementary, not independent —
`acceptance_rate + override_rate = 1` over the same interaction set
(`modified` and `rejected` both count as an override). A low acceptance
rate alongside a high `workflow_interruptions` count (in the workflow
impact detail) signals the recommendation quality itself needs attention
before considering broader deployment (`PILOT_FINAL_REPORT.md`'s
promotion gate).
