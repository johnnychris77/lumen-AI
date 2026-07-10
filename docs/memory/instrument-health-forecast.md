# Instrument Health Forecast (Project Insight, Section 5)

`app/services/instrument_health_forecast_service.py`.

Extends the existing Predictive Instrument Intelligence
(`app/services/instrument_intelligence.instrument_timeline` — risk trend,
remaining-useful-life estimate, already used by Instrument Passport) rather
than re-deriving risk trend from scratch:

| Field | Source |
|---|---|
| `condition_trend` | `instrument_condition_service` (cleaning/damage-finding rate, first half vs second half) |
| `failure_risk_trend` | `instrument_intelligence.instrument_timeline`'s risk-score trend |
| `repair_trend` | `none` / `occurred_once` / `recurring`, from this instrument's own `repair_count` |
| `estimated_remaining_useful_life` | `instrument_intelligence.instrument_timeline`'s existing projection (only offered on a clear worsening trend) |
| `confidence_interval` | New — see below |
| `sample_size` | How many inspections this forecast is built on |

## Confidence interval — honest about small samples

`confidence_interval` widens as `sample_size` shrinks (±5 at 8+ inspections,
±12 at 4-7, ±20 at 2-3, `null` below 2 or when there's no scored risk value
yet) — a deliberately wider, less precise band with less history, rather than
a fixed-width interval that would claim the same precision regardless of how
little is actually known about this instrument.

## What this deliberately does not do

Does not re-run or duplicate `instrument_intelligence.instrument_timeline`'s
trend/RUL math — it's called directly and its `prediction` block is reused
verbatim, with the condition/repair trend and confidence interval added on
top.
