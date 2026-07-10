# Project Insight — Forecast Explainability

LumenAI v3.3 — Section 10

## A structural guarantee, not an afterthought

`app/services/insight_forecast_math.py::build_explainability_envelope`
is called by every Insight forecast service — quality trend, operational,
and (via its own evidence list) instrument lifecycle — so the six fields
Section 10 requires are a structural property of every forecast response,
not something bolted on per-endpoint:

```python
def build_explainability_envelope(
    *, data_sources, time_horizon, confidence_level,
    contributing_factors, historical_comparison, known_limitations,
) -> dict:
    return {
        "data_sources": data_sources,
        "time_horizon": time_horizon,
        "confidence_level": confidence_level,
        "contributing_factors": contributing_factors,
        "historical_comparison": historical_comparison,
        "known_limitations": known_limitations,
    }
```

## What each field means concretely

- **Data sources** — the actual ORM models the forecast was computed
  from (e.g. `["InspectionFinding", "Inspection", "SupervisorReview"]`),
  not a generic "internal data" placeholder.
- **Time horizon** — one of `7_day`/`30_day`/`90_day`/`rolling_annual`
  (`HORIZON_DAYS` in `app/models/predictive_insight.py`), always present
  on the forecast row itself.
- **Confidence level** — computed from real sample size and OLS fit
  quality (`insight_forecast_math.confidence_from_trend`), or a real
  binomial Wald interval for rate-based instrument-lifecycle estimates
  (`insight_instrument_forecast_service._wald_interval`) — never a
  seeded-random placeholder.
- **Contributing factors** — a list of `{factor, value, signal}` dicts
  naming the specific inputs (e.g. sample size, fit quality, recent-vs-
  prior corrosion counts) that produced the forecast — the same
  `EvidenceFactor` shape `prediction_engine.py` already established.
- **Historical comparison** — a recent-14-day vs. prior-14-day average
  (quality trends) so a leader can see whether "increasing" means a small
  wobble or a real shift, computed from the same historical series the
  forecast itself was fit on.
- **Known limitations** — explicit, human-readable strings, not a boolean
  flag: "Fewer than 5 data points available — trend is not statistically
  meaningful yet," "No recorded activity for this metric in the lookback
  window," "Only N inspections of this instrument type in the last 90
  days — estimates are low-confidence." A forecast with real limitations
  says so; it does not silently present a fragile estimate as if it were
  well-supported.

## Confidence intervals, not just point estimates

Section 2 explicitly asks for confidence intervals, not only a single
number. Every `QualityTrendForecast` carries `confidence_low`/
`confidence_high` (an ~80% interval widened by the trend's real residual
spread) alongside the point `forecast_value`; every
`InstrumentLifecycleForecast`'s `retirement_likelihood` carries its own
Wald interval. A caller that only reads the point value is still shown
the interval fields — they are never omitted from the response even when
a caller doesn't ask for them.

## No causation claims

Every disclaimer in this module (`DISCLAIMER` in
`app/models/predictive_insight.py`, echoed in every forecast/report row)
states explicitly that a forecast is "a potential association for
leadership awareness, not a causal or clinical determination" — the same
non-causation language established across every prior sprint in this
codebase (Atlas, Sentinel, Nexus). `human_review_required: true` is set
on every table without exception.
