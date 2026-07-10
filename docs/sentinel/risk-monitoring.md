# Continuous Risk Monitor

LumenAI v3.0 · Project Sentinel

## Nine signal types, one recurrence idiom

`sentinel_risk_monitor_service.detect_risk_signals` reuses
`capa_suggestion_service`'s existing recurrence idiom — a count reaching
`_REPEAT_THRESHOLD` (3) within `_LOOKBACK_DAYS` (90) — applied to the
sprint's nine named signal types, rather than inventing a fourth "is this
recurring?" algorithm:

| Signal | Grouped by | Source |
|---|---|---|
| `repeated_blood` / `repeated_rust` / `repeated_bone` / `repeated_corrosion` | anatomy zone | `InspectionFinding` |
| `repeated_damage` (pitting/crack/wear/insulation damage/missing component) | instrument family | `InspectionFinding` + `resolve_family` |
| `repeated_low_confidence` (confidence < 0.7) | technician | `Inspection.confidence` |
| `repeated_missing_coverage` (coverage < 75%) | technician | `Inspection.coverage_pct` |
| `repeated_supervisor_overrides` | instrument type | `DispositionOverride` |
| `repeated_repair_referrals` | instrument type | `RepairRequest` (OR Connect) |

## Idempotent, persisted, and generating alerts

Each detected signal is upserted into `SentinelRiskSignal` — a second call
to `detect_risk_signals` updates the existing open signal's `occurrences`/
`severity` rather than creating a duplicate. Severity scales with
occurrence count (`medium` at threshold, `high` at 2x, `critical` at 3x).
Every open signal is what `sentinel_alert_service.generate_enterprise_alerts`
turns into an explainable Enterprise Alert (see `clinical-alerting.md`).

## Endpoints

- `POST /api/sentinel/risk-signals/detect` — run detection
- `GET /api/sentinel/risk-signals` — list open signals
- `POST /api/sentinel/risk-signals/{id}/resolve` — mark resolved
