# Outcome Prediction — Instrument Health Projection & Outcome Learning

Codename: Project Sentinel · LumenAI Inspect v2.5

## Instrument Health Projection (Section 5)

`GET /api/scenario-analysis/instrument-health?instrument_barcode=...` (or
`instrument_udi=...`) forecasts one physical instrument's trajectory:

- `health_trend` — `improving` / `stable` / `declining` / `insufficient_data`, taken directly from `instrument_condition_service.instrument_condition_history`'s clean-rate trend
- `corrosion_progression` — `worsening` when corrosion has appeared 2+ times in history, `stable` for one occurrence, `none_detected` otherwise
- `damage_progression` — same logic applied to non-cleaning (structural) findings
- `inspection_frequency_days`, `repair_frequency_days` — modeled cadence, only populated when there's enough history to speak to a cadence at all
- `expected_remaining_service_life_days` — a modeled estimate, weighted down for instruments with a declining trend or repair history; `null` when history is insufficient to project at all, rather than fabricating a number

Returns 404 when the instrument identity has no inspection history —
LumenAI does not guess a projection for an instrument it has never seen.

## Outcome Learning (Section 8)

When the actual disposition of an inspection becomes known — after
supervisor review, repair, or removal from service — record it against the
original simulation:

```
POST /api/scenario-analysis/{simulation_run_id}/actual-outcome
{ "actual_disposition": "Remove From Service", "notes": "Confirmed by supervisor" }
```

This creates or updates a `ScenarioOutcome` row comparing the predicted
scenario to the actual one and sets `prediction_correct`. Restricted to
`admin` / `spd_manager` (the same leadership roles that can action a
`DispositionOverride`), and logged as `scenario_analysis.outcome_recorded`.

`prediction_correct` feeds directly into the enterprise `prediction_accuracy`
metric (`decision-comparison.md`) — this is how the simulation engine's
recommendations are continuously checked against reality rather than
trusted indefinitely on the strength of their initial heuristic.
