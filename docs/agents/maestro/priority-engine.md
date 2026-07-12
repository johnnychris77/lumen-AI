# Project Maestro — Priority Engine

Section 2 of the sprint brief.

## The 9 priority categories

`app/models/maestro_orchestration.py::PRIORITY_CATEGORIES` — each ranked
from one specialist's real, already-persisted output; a category with no
real data to report is skipped, never fabricated:

| Category | Resolved from |
|---|---|
| `highest_risk_instrument` | Sentinel-X `supervisor_workspace_summary` → `highest_risk_instruments[0]` |
| `highest_risk_workflow` | Sentinel-X `risk_dashboard_summary` → `workflow_risk.process_variation_flagged_count` |
| `highest_risk_facility` | Sentinel-X `risk_dashboard_summary` → `facility_risk[0]` (heatmap) |
| `highest_risk_technician_education_need` | Sage `list_gaps(status="open")`, highest `occurrence_count` |
| `highest_risk_equipment` | Vulcan `VulcanReliabilityAssessment`, lowest `reliability_score` of the last 200 rows |
| `highest_priority_capa` | `capa_suggestion_service.generate_capa_suggestions`, highest `occurrences` |
| `highest_priority_inspection` | Sentinel-X `supervisor_workspace_summary` → `highest_risk_inspections[0]` |
| `highest_priority_repair` | `RepairRequest` (or_connect), oldest pending |
| `highest_priority_executive_issue` | `ExecutiveRiskSignal`, highest unreviewed risk tier |

## Ranking

`maestro_priority_engine_service.compute_priorities(db, tenant_id)` runs
every category resolver, persists one `MaestroPriorityItem` row per
category that produced real data, and ranks the resulting set across
categories by `priority_score` (descending). `rank` is assigned 1..N over
that combined, cross-category ordering — this is Maestro's only original
computation; every input score itself comes straight from the owning
specialist.

`latest_priorities(db, tenant_id)` returns the most recent run's items
(matched by `created_at`), already in rank order, for read-only display
without re-computing.

## Auditability

Every `MaestroPriorityItem` carries `source_specialist`, `rationale`, and
`evidence_json` — a leader can always trace a ranked priority back to the
exact specialist output that produced it.
