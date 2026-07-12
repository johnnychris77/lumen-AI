# Project Maestro — Leadership Recommendation Engine, Daily Brief & Executive Coordination

Sections 3, 4, 5 of the sprint brief.

## Leadership Recommendation Engine (Sections 3 & 5)

`maestro_recommendation_engine_service.generate_recommendations(db,
tenant_id)` runs the Priority Engine, then converts each real priority
item (plus any pending Veritas baseline conflict) into one specific,
evidence-linked `MaestroRecommendation`:

| Trigger | Recommendation | Example |
|---|---|---|
| `highest_risk_facility` / `highest_risk_instrument` | `move_supervisor` | "Move supervisor to review \<facility/instrument\>." |
| `highest_risk_workflow` | `inspection_priorities` | "Review process-variation workflow controls." |
| `highest_risk_technician_education_need` | `schedule_competency` | "Schedule \<domain\> competency." |
| `highest_risk_equipment` (corrosion-related) | `review_corrosion_trend` | "Review \<instrument\> corrosion trend." |
| `highest_risk_equipment` (other) | `equipment_utilization` | "Review utilization for \<instrument\>." |
| `highest_priority_capa` | `generate_capa_draft` | "Generate CAPA draft." |
| `highest_priority_inspection` | `inspection_priorities` | "Prioritize \<inspection\>." |
| `highest_priority_repair` | `escalate_repair_backlog` | "Escalate repair backlog." |
| `highest_priority_executive_issue` | `quality_initiatives` | "Address executive risk: \<issue\>." |
| Unresolved Veritas baseline conflict | `publish_baseline` | "Publish updated baseline." |

`generate_strategic_recommendations(db, tenant_id)` produces the six
broader, periodic Section 5 categories (`resource_allocation`,
`staffing_changes`, `inspection_priorities`, `equipment_utilization`,
`education_priorities`, `quality_initiatives`) from the Operational Health
Index and the current priority list, rather than any single item — these
are the weekly/quarterly leadership-planning recommendations.

Every recommendation is advisory only: `status` starts `pending` and only
a Decision Journal entry (Section 8) advances it. Actually materializing a
CAPA from a `generate_capa_draft` recommendation is a separate,
human-triggered call to `maestro_capa_integration_service.
create_capa_from_recommendation` — nothing runs automatically.

## Daily Operational Brief (Section 4)

`maestro_daily_brief_service.generate_brief(db, tenant_id, brief_type)`
composes the same real signals (top priorities, pending recommendations,
operational health, open Sentinel-X patient safety alerts) into one of
five brief types (`BRIEF_TYPES`): `morning_brief`, `afternoon_update`,
`end_of_day_summary`, `weekend_readiness`, `shift_handoff` — each with a
narrative framed for that moment in the day.

## Executive Coordination (Section 5) & Strategy Timeline (Section 6)

`maestro_timeline_service.strategy_timeline(db, tenant_id)` is a pure
query over `MaestroRecommendation`, grouped by `timeline_horizon`
(`today`, `this_week`, `this_month`, `quarter`, `year`) and, within each
horizon, by `status` (`pending`, `completed`, `blocked`, `escalated`,
`dismissed`) — there is no separate timeline table.
