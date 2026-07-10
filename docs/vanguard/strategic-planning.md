# Project Vanguard — Strategic Planning Workspace & Executive AI Advisor

LumenAI OS v4.6 — Sections 5 & 6

## Strategic Planning Workspace (Section 5)

Frontend route `/strategy`. Five initiative types, each generator
composing an already-real signal into a draft `StrategicInitiative` —
none of them projects a number this codebase can't actually support:

| Initiative type | Real signal used |
|---|---|
| Capital planning | `vanguard_financial_service`'s capital-replacement priority list (from `prediction_engine`) |
| Quality initiative | `finding_trend_service.finding_trends`'s real recurring-finding-type totals |
| Service-line expansion | Real `SurgicalCase.service_line` volume, last 30 days vs. the prior 30 days |
| Capacity planning | Digital Twin utilization + `insight_operational_forecast_service.forecast_operational`'s real inspection-workload projection |
| Scenario planning | A captured snapshot of the current Executive Intelligence Center state alongside a free-text scenario description |

Scenario planning is deliberately **not** a fabricated enterprise-wide
what-if simulator. Orbit's `orbit_simulation_service` already owns
case-scoped what-if simulation (case time-shift, instrument
unavailability, vendor tray delay); building a second, enterprise-scoped
simulator with no real basis for projecting downstream impact would
mean inventing numbers this codebase can't support. Instead, Vanguard's
scenario planning captures the real current state for a human-led
planning discussion, honestly labeled as such.

```
GET   /api/vanguard/strategy/initiatives
GET   /api/vanguard/strategy/initiatives/{id}
PATCH /api/vanguard/strategy/initiatives/{id}/status
POST  /api/vanguard/strategy/generate/{initiative_type}
```

## Executive AI Advisor (Section 6)

This codebase has zero real LLM/completion-API integration anywhere
(confirmed repeatedly across every prior sprint's research). Consistent
with that, the Executive AI Advisor is **four new intents added directly
to `catalyst_query_engine.py`'s existing deterministic keyword
classifier** — not a second natural-language engine:

| Example question (from the brief) | New intent | Dispatches to |
|---|---|---|
| "What are our top enterprise risks?" | `enterprise_risk_summary` | `vanguard_ai_advisor_service.top_enterprise_risks` → `pulse_command_center_service.pulse_command_center` |
| "Which investment will reduce repair costs?" | `investment_recommendation` | `vanguard_ai_advisor_service.investment_recommendation` → `prediction_engine.compute_predictive_dashboard` |
| "Which facilities require attention?" | `facility_attention_ranking` | `vanguard_ai_advisor_service.facilities_requiring_attention` → `vanguard_benchmarking_service` (inspection programs) |
| "What quality trends should I discuss at tomorrow's executive meeting?" | `quality_trends_for_meeting` | `vanguard_ai_advisor_service.quality_trends_for_meeting` → `finding_trend_service.finding_trends` |

Every response still carries Catalyst's existing explainability envelope
(`build_evidence_envelope`) — evidence used, reasoning path, confidence,
references — unchanged from how Catalyst's original eight intents work.
The frontend's AI Advisor tab (`/executive`) calls the same
`POST /api/catalyst/chat` endpoint Catalyst already exposes; Vanguard
adds no second chat endpoint.
