# Project Insight — Predictive Education & Recommendation Engine

LumenAI v3.3 — Sections 4 & 8

## Section 4 — Predictive Education Engine

`insight_education_forecast_service.py` reuses
`competency_intelligence_service.py` (Quality Guardian v2.9) directly for
supervisor-correction and image-quality-issue patterns — those are not
re-derived. It adds two signal types this codebase didn't compute before,
both per technician, both grounded in real `Inspection` rows:

- **Missed anatomy zone trend** (`missed_anatomy_zone_trend`) — compares
  the average number of missed anatomy zones per inspection (via
  `inspection_coverage.compute_coverage`) in the last 30 days against the
  prior 30 days. Flagged only when the recent average is at least 0.5
  zones higher than the prior average, with at least 3 assessed
  inspections in *each* window — a technician with too little activity in
  either window is silently skipped, never assigned a fabricated trend.
- **Coverage decline trend** (`coverage_decline_trend`) — same comparison
  on `Inspection.coverage_pct`, flagged when the recent average is at
  least 5 percentage points lower than the prior average.

`generate_predictive_education_signals` returns both the new signals and
the existing competency opportunities in one merged response:

```jsonc
{
  "new_signals": [ /* PredictiveEducationSignal rows */ ],
  "existing_competency_opportunities": [ /* CompetencyOpportunity rows, unchanged */ ],
  "human_review_required": true,
  "disclaimer": "..."
}
```

Every signal explicitly states it "provides recommendations without
replacing manager judgment" — the recommendation text names the
technician and the specific pattern observed, never a generic prompt.

## Section 8 — Predictive Recommendation Engine

`insight_recommendation_service.py` never invents a recommendation — each
one is derived from an already-generated forecast row:

| Source | Trigger | Example |
|---|---|---|
| `QualityTrendForecast` | Adverse trend direction (increasing for blood/bone/debris/rust/corrosion/damage/supervisor workload; decreasing for coverage compliance) at confidence ≥ 0.3 | "Corrosion is trending increasing over the 30 day horizon" |
| `InstrumentLifecycleForecast` | `lifecycle_risk_tier` is high or critical | "{instrument_type} instruments show high lifecycle risk" |
| `OperationalForecast` | A non-null forecast value at confidence ≥ 0.3 | "Repair Backlog projected at 12.4 over the 30 day horizon" |
| `PredictiveEducationSignal` | Any new signal generated | Uses the signal's own recommendation text |

Every recommendation carries the four fields the sprint requires:

- **Evidence** — the source forecast's contributing factors/evidence list.
- **Confidence** — copied from the source forecast's own confidence,
  never re-fabricated.
- **Reasoning** — names the specific trigger (the metric, the instrument
  type, the projected value) — never a generic statement.
- **Suggested action** — a concrete next step ("Review corrosion practices
  and consider refresher education or maintenance review," "Schedule a
  lifecycle review for {instrument_type} instruments").

Matches this sprint's own example shape verbatim in spirit: *"Corrosion
findings for orthopedic drill bits are trending upward across two
facilities. Review maintenance practices."*

## Idempotent generation

Recommendations are deduplicated by `(tenant_id, title, status="open")` —
the same pattern established in Atlas's `atlas_alert_service.py` and
Sentinel's alert service — so re-running generation after nothing has
changed never spams duplicate open recommendations for the same finding.
