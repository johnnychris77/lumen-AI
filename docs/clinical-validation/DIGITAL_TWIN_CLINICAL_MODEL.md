# LumenAI — Digital Twin Clinical Model

Objective 7 review. Three digital twin systems exist with deliberately distinct scope (see `ADR-0002` in the Phase 1 architecture review): `digital_twin.py` (SPD workflow/operations telemetry — purely observational, no predictive fields), `digital_quality_twin.py` (quality-state forecasting), and Apollo's governance-health twin (`apollo_quality_twin_service.py`). This review's finding: **the two forecasting-capable twins hedge uncertainty very differently, and only one of them should be held up as the model to replicate.**

## `digital_quality_twin.py` — consistently hedged, the model to replicate

Every forward-looking class in this file pairs its projection with an explicit confidence and disclaimer:

- **`QualityForecast`**: `projected_quality_score`/`projected_risk_level`/`risk_drivers`, paired with `confidence_score`, `association_reason`, `human_review_required` (default `True`), and disclaimer: *"Forecast is a modeled projection for planning purposes. Does not establish causation or guarantee outcomes. All forecasts require human review before operational decisions."*
- **`ScenarioSimulation`**: `projected_quality_delta`/`projected_risk_reduction`/`projected_timeframe_days`, same `confidence_score`/`human_review_required` pairing, disclaimer: *"Simulation output for planning purposes only. Does not establish causation or predict specific outcomes."*
- **`InterventionModel`**: `projected_quality_score`/`projected_improvement`, disclaimer: *"Intervention model is advisory only... Does not establish causation. Human review and approval required before implementation."*
- **`ExecutiveDecisionBrief`**: `headline_risk`/`quality_trend`, disclaimer: *"All findings represent potential associations for human review. Does not establish causation or constitute clinical guidance."*
- **`QualityTwinState`**: `trend_direction` paired with `trend_confidence` (numeric).
- **`ForecastOutcome`**: an explicit prediction-vs-actual calibration table — `predicted_quality_score`/`predicted_risk_level` vs. `actual_quality_score`/`actual_risk_level`, with `prediction_error` and `calibration_status` (pending/calibrated/expired). This is a genuine strength: the platform checks its own forecasts against what actually happened, rather than only ever making claims with no feedback loop.

No field in this file is named in a way that overstates certainty (no bare `predicted_failure_date`-style field with no accompanying confidence) — every predictive field found is paired with at least a confidence score, a human-review flag, or an explicit non-causation disclaimer.

## Apollo's governance-health twin — real, but under-hedged relative to the above

`apollo_quality_twin_service.py::compute_quality_twin` returns: `id`, `department`, `created_at`, `scores` (8 named sub-scores), `overall_score`, `factors` (hand-written strings disclosing *data-scope* limitations, e.g. "tenant-wide, not department-scoped" or "department-scoped across N technicians"), `human_review_required: True`, and `disclaimer`. **There is no numeric or categorical confidence field anywhere in this return value.** `factors` discloses which sub-scores are proxies rather than true department-level measurements, but it does not quantify confidence in the overall score the way `digital_quality_twin.py`'s `confidence_score` does.

`twin_history` (the trend view consumed by Oracle's Digital Twin Research) is hedged **even less** than the live-compute endpoint: it returns only `id`, `created_at`, `department`, `overall_score`, `scores` — no `factors`, no `disclaimer`, and no `human_review_required` at all in the history rows.

**Recommendation**: add a `confidence_score` field to Apollo's twin snapshot (mirroring `digital_quality_twin.py`'s pattern) and carry `human_review_required`/a disclaimer through into `twin_history`'s output, not just the live-compute path. This is the clearest, lowest-risk clinical-safety improvement this review surfaced in the digital-twin area.

## Vulcan's instrument-progression model — condition trend, not a "twin" per se, but the same family of concern

`vulcan_progression_service.py::compute_progression` uses exactly three confidence levels: `"low"`, `"moderate"`, `"high"`. `PROGRESSION_INSUFFICIENT_HISTORY` triggers whenever `recurrence_count < 2` (fewer than 2 matching findings) — explicitly the "not enough data, don't guess" case, returned with `confidence: "low"`.

| Progression state | Exact condition (severities are 0-3; `net_change` = last − first) | Confidence |
|---|---|---|
| `insufficient_history` | `recurrence_count < 2` | low |
| `rapidly_worsening` | non-decreasing sequence, `net_change ≥ 2` | high |
| `slowly_worsening` | non-decreasing sequence, `net_change == 1` | moderate |
| `improving` | non-increasing sequence, `net_change < 0` | moderate |
| `unresolved` | non-decreasing, `net_change == 0`, `max(severity) ≥ 2` | moderate |
| `stable` | non-decreasing, `net_change == 0`, `max(severity) < 2` | moderate |
| `intermittent` | severity goes up and down (neither monotonic direction) | low |

This is a well-designed, honestly-hedged model: any single decrease anywhere in the sequence disqualifies both "worsening" states, and fewer than 2 data points never produces a confident trend claim.

## Conclusion — Objective 7's requirement

Digital Twins in this codebase describe observations and trends without overstating certainty **in the `digital_quality_twin.py` and Vulcan progression systems specifically**. Apollo's governance-health twin partially meets this bar (scope-limitation disclosure, `human_review_required`) but lacks a quantified confidence signal and loses even its qualitative hedging in the historical-trend view — this is the one clear improvement opportunity this review identifies in the digital-twin area, carried into [AI_LIMITATIONS.md](./AI_LIMITATIONS.md) and the [PRODUCTION_READINESS_SCORECARD.md](../production-readiness/PRODUCTION_READINESS_SCORECARD.md)'s companion, the Clinical Readiness Scorecard.
