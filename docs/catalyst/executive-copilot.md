# Project Catalyst — Executive Copilot

LumenAI OS v4.4 — Section 4

## Persona mapping

`catalyst_persona_service.persona_for_role(role)` maps Genesis's
canonical role catalog (`platform_identity_service.CANONICAL_ROLE_CATALOG`)
to the Executive persona for: `enterprise_admin`, `hospital_admin`,
`facility_director`, `market_director`, `regional_administrator`.

## Briefings

`GET /api/catalyst/persona/executive-briefing?cadence=daily|weekly|monthly|quarterly`
(gated to `admin`/`spd_manager` today, matching every other
leadership-scoped endpoint's `_LEADERSHIP_ROLES`) composes:

* **Quality** — `catalyst_skills_service.reporting_skill`. For
  `monthly`/`quarterly` cadences with a resolvable enterprise-hierarchy
  facility, this is a persisted `atlas_report_service.generate_executive_report`
  (Atlas's own cadence enum has no `daily`/`weekly` — confirmed in
  `REPORT_CADENCES` — so those two cadences, and any tenant with no
  enterprise-hierarchy facility, get the live
  `pulse_executive_service.executive_command_dashboard` instead. Never
  a report coerced into a cadence it can't actually produce.)
* **Risk** — `anatomy_risk_service.anatomy_risk_dashboard`.
* **Forecast** — `insight_operational_forecast_service.forecast_operational`.
* **Recommendations** — pulled from the Atlas report's summary when one
  was generated; an empty list otherwise (never invented).
* **Emerging trends** — `finding_trend_service.finding_trends`.

Every field in the response is real, computed data — Catalyst adds no
new score or projection of its own for the Executive Copilot; it only
composes what Sentinel/Atlas/Insight/Anatomy already compute.
