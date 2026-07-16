# LumenAI — Capacity Planning

Objective 6 review. `docs/vanguard/strategic-planning.md` already documents this area's real scope accurately — this document cites it rather than duplicating it, and adds the specific gap analysis against this brief's 6 required forecast categories.

## `generate_capacity_planning()` — only 2 of 6 required forecast categories are real

`vanguard_strategy_service.py::generate_capacity_planning()` calls exactly two things: `digital_twin_engine.compute_twin_dashboard()` (for utilization %/bottleneck station) and `insight_operational_forecast_service.forecast_operational()` with a single forecast type, `FORECAST_INSPECTION_WORKLOAD` (7-day horizon). Against the brief's 6 sub-items:

| Required forecast | Status |
|---|---|
| Inspection demand | **Real** — the one forecast type actually invoked |
| Equipment utilization | **Real** — from Digital Twin's live station-queue snapshot, not mock data |
| Staffing needs | **Missing from this function** — a related forecast type (`FORECAST_SUPERVISOR_REVIEW_DEMAND`) exists in the underlying service but `generate_capacity_planning()` never calls it |
| Repair workload | **Missing from this function** — `FORECAST_REPAIR_BACKLOG` exists in the underlying service but is never invoked here |
| Training demand | **Does not exist anywhere** — there is no `FORECAST_TRAINING_*` type defined at all in `predictive_insight.py`'s `OPERATIONAL_FORECAST_TYPES` list |
| Growth trends | **Exists, but as an unrelated sibling feature** — `generate_service_line_expansion()` covers service-line volume growth, but it is a separate initiative generator, never called by `generate_capacity_planning()` |

**The module's own docstring is honest about this narrow scope** ("Digital Twin utilization plus `insight_operational_forecast_service.forecast_operational`'s real inspection-workload projection") — it never claims the other four categories. Any Version 1.3 feature presenting "capacity planning" as covering all 6 brief-named categories would be overstating current capability; today it covers 2 directly, with a third (growth trends) available as an unconnected sibling function.

## The forecasting model itself — real, simple, and honestly hedged

No `statsmodels`/`prophet` dependency exists anywhere in the backend. Forecasting is a genuine, hand-rolled ordinary-least-squares trend fit (`insight_forecast_math.py::linear_trend()`), which requires a minimum of 5 data points or explicitly returns `sufficient_data: False` rather than fabricating a trend from too little history — the same "don't guess from thin data" discipline confirmed elsewhere in this platform (Vulcan's progression model, Veritas's evidence gate). `project_forward()` extrapolates the fitted line; confidence is derived from sample size and r², not randomized.

**One field to avoid citing as real trend data**: `digital_twin_engine.compute_twin_dashboard()`'s `trend_data` field is explicitly commented in its own source as *"24h trend data (seeded mock)"* — a fabricated hourly series using a seeded RNG. This mock field is not consumed by `generate_capacity_planning()` (which only reads the live `utilization_pct`/`bottleneck_station` snapshot), but it lives in the same dashboard object returned to the frontend and could easily be mistaken for real trend data by a future feature built on top of this dashboard. Any Version 1.3 capacity-planning UI should explicitly avoid surfacing this field as if it were computed, not seeded.

## Recommendation

1. Extend `generate_capacity_planning()` to call the two forecast types it already has access to but doesn't use (`FORECAST_SUPERVISOR_REVIEW_DEMAND` for staffing, `FORECAST_REPAIR_BACKLOG` for repair workload) — this closes 2 of the 4 gaps with no new forecasting logic, only additional calls into an already-real service.
2. Add a genuine `FORECAST_TRAINING_DEMAND` type to `OPERATIONAL_FORECAST_TYPES` if training-demand forecasting is a real Version 1.3 priority — this is new work, not a wiring fix.
3. Either fold `generate_service_line_expansion()`'s growth-trend output into the capacity-planning response, or clearly document that "growth trends" lives in a separate Strategic Planning initiative type, not the Capacity Planning generator, to avoid confusing the two in customer-facing material.
4. Never surface Digital Twin's seeded-mock `trend_data` field as if it were a real computed trend in any capacity-planning UI.
