# Project Insight — Predictive Intelligence Engine

LumenAI v3.3

## Mission

Project Insight enables LumenAI to forecast quality trends, operational
risk, and instrument health using historical inspections, Digital Twins,
Knowledge Graph relationships, enterprise analytics, and validated
clinical data — assisting leaders in proactive decision-making while
preserving human authority over operational and clinical actions.

## Section 1: a single orchestrator, not a new prediction stack

`app/services/insight_engine_service.py::generate_predictive_intelligence`
is the one genuinely new piece of plumbing this sprint adds: it ties
together every predictive signal already computed elsewhere in this
codebase into one coherent response, rather than re-deriving any of them.

```
backend/app/models/predictive_insight.py            — 6 tables + constants
backend/app/services/insight_forecast_math.py        — shared OLS trend math
backend/app/services/insight_quality_trend_service.py    — Section 3
backend/app/services/insight_operational_forecast_service.py — Section 5
backend/app/services/insight_instrument_forecast_service.py  — Sections 2 & 6
backend/app/services/insight_education_forecast_service.py   — Section 4
backend/app/services/insight_engine_service.py        — Section 1 & 7
backend/app/services/insight_recommendation_service.py — Section 8
backend/app/services/insight_report_service.py        — Section 9
backend/app/routes/predictive_insight.py              — /api/insight/*
frontend/src/components/InsightDashboard.tsx
frontend/src/pages/ForecastPage.tsx                   — route: /forecast
```

## What Insight composes, not duplicates

| Existing engine | What it already forecasts | What Insight adds |
|---|---|---|
| `prediction_engine.py` (P7) | Named-instrument failure probability (30/90/180d), contamination recurrence, repair cost, recall/tray risk | Corrosion-progression and recurring-damage *trend* scoring, aggregated across an instrument *type* rather than one named instrument |
| `digital_quality_twin_service.py` (P22) | Tenant-wide quality score forecast at 30/60/90-day horizons | A 7-day and rolling-annual point on the same trajectory, plus repair/retirement likelihood and a lifecycle risk tier |
| `finding_trend_service.py` (v1.5) | Historical finding counts bucketed daily/weekly/monthly/quarterly/yearly | The actual forward projection (OLS trend) `finding_trend_service` doesn't do |
| `competency_intelligence_service.py` (Guardian v2.9) | Coaching/team/department education opportunities from supervisor corrections and image-quality issues | Two new signal types: missed-anatomy-zone trend and coverage-decline trend |
| `atlas_report_service.py` (Atlas v3.1) | CSV/XLSX/PDF export pattern | Reused verbatim for Executive Forecast Reports (Section 9) |

`generate_predictive_intelligence` calls `prediction_engine.compute_predictive_dashboard`
and `digital_quality_twin_service.get_forecasts` directly and includes
their output verbatim (`existing_instrument_failure_dashboard`,
`existing_quality_forecasts`) alongside Insight's own quality-trend,
operational, instrument-lifecycle, and education forecasts — nothing from
those two engines is recomputed.

## Never fabricated

Every forecast in this module is computed from real historical rows
(`InspectionFinding`, `Inspection`, `SupervisorReview`, `RepairRequest`)
via the deterministic OLS trend implementation in
`insight_forecast_math.py` — never a seeded-random mock, unlike some of
the engines it composes (`digital_quality_twin_service.py` falls back to
a seeded decay when no forecast rows exist yet; Insight's own forecasts
never do). When a metric has fewer than 5 usable data points, the
forecast explicitly reports `"insufficient_data"`-style limitations
(Section 10) and a correspondingly low confidence, rather than inventing
a number.

## Advisory only

Every Insight response carries `human_review_required: true` and the
disclaimer defined in `app/models/predictive_insight.py::DISCLAIMER`.
Forecasts assist proactive decision-making; they do not replace human
operational or clinical judgment, and no Insight output claims causation
— only potential association.
