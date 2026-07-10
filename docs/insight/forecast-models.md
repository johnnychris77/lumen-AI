# Project Insight — Forecast Models

LumenAI v3.3 — Sections 2, 3, 5 & 6

## Shared math: one trend implementation for every forecast

`app/services/insight_forecast_math.py` is the single deterministic
trend-projection implementation every Insight forecast service uses —
"forecast" means the same statistical operation everywhere in this
module:

1. **`linear_trend(series)`** — ordinary least squares over `(index,
   value)` pairs. Returns slope, intercept, `r_squared`, residual standard
   deviation, the series mean, and `sufficient_data` (False when fewer
   than 5 points — the forecast then reports a limitation rather than a
   number).
2. **`project_forward(trend, steps_ahead)`** — extrapolates the fitted
   line `steps_ahead` beyond the observed window.
3. **`confidence_from_trend(trend)`** — grows with sample size and fit
   quality (`r_squared`), capped at 0.95. Never a random draw.
4. **`confidence_interval(forecast_value, trend)`** — a ~80% interval
   around the point forecast, widened by the trend's real residual
   spread (not an arbitrary fixed band).
5. **`trend_direction(trend)`** — increasing/decreasing/stable, based on
   the *total* fitted change across the observed window relative to the
   series' own mean (not the per-step slope normalized against the OLS
   intercept, which is a poor reference point for a sparse or non-
   stationary series — the intercept is only the fitted value at x=0).

## Section 3 — Quality Trend Forecasting

`insight_quality_trend_service.py` builds a continuous 90-day daily
series (zero-filled for days with no activity — the same "report 0,
don't omit" philosophy `finding_trend_service.py` established) for nine
metrics: blood, bone, debris, rust, corrosion, damage (an aggregate of
crack/wear/pitting/missing_component/insulation_damage, matching the
`_CONDITION_FINDING_TYPES` convention used elsewhere), coverage
compliance, supervisor workload, and inspection throughput. Each is
projected at 7-day/30-day/90-day/rolling-annual horizons
(`HORIZON_DAYS` in `app/models/predictive_insight.py`).

Coverage compliance carries the last known daily average forward for
days with no inspections, rather than fabricating a 0% compliance day
that never happened.

## Section 5 — Operational Forecasting

`insight_operational_forecast_service.py` forecasts six operational
concerns from the same daily-series + OLS approach:

- **Inspection workload** / **supervisor review demand** — daily counts.
- **Repair backlog** — a running net (opened − closed) `RepairRequest`
  count, seeded from the current true open-repair count so the backlog
  series starts from reality, not zero.
- **Instrument availability** — the daily percentage of inspected
  instruments *not* in `REPROCESS`/`REMOVE FROM SERVICE` disposition.
- **High-risk procedure prep** — daily count of inspections with
  `risk_score >= 60`.
- **Peak inspection periods** — a distributional pattern (average volume
  per day-of-week), not a forward point-value forecast, so it skips the
  OLS trend and instead reports the day-of-week with the highest average
  historical volume.

## Sections 2 & 6 — Instrument Failure Forecasting & Predictive Digital Twin Analytics

`insight_instrument_forecast_service.py` operates at the `instrument_type`
level (not a single named instrument, unlike P7):

- **Corrosion progression / recurring damage scores** — a 0–100 score
  (50 = stable) comparing the last 30 days' finding counts against the
  prior 30 days for that instrument type.
- **Repair likelihood** — repairs / inspections for that type (a real
  base rate). **Repair recurrence likelihood** — the repair rate within
  the recent 30-day window alone.
- **Removal-from-service likelihood** — the real rate of `"REMOVE FROM
  SERVICE"` dispositions for that instrument type.
- **Retirement likelihood** — a weighted composite (0.5 × removal-from-
  service rate + 0.3 × corrosion score + 0.2 × damage score), with a
  **Wald confidence interval** (`confidence_low`/`confidence_high`) — a
  real binomial proportion interval, not an arbitrary band.
- **Lifecycle risk tier** — low/moderate/high/critical thresholds on
  retirement likelihood.
- **Health score trajectory** — extends P22's `QualityForecast` (30/60/90-
  day) with a 7-day and rolling-annual point via linear extrapolation of
  the same trajectory, satisfying Section 6's wider horizon set without
  re-deriving P22's own quality score.

Every instrument-type forecast lists its known limitations explicitly
(e.g. "Only N inspections of this instrument type in the last 90 days —
estimates are low-confidence") rather than presenting a low-sample
estimate as equally confident as a well-supported one.
