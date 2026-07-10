# Project Orbit — Perioperative Intelligence Overview

LumenAI OS v4.5 — Platform overview

## What Orbit is, and isn't

Orbit expands LumenAI from SPD (Sterile Processing) into the broader
perioperative ecosystem — a Surgical Readiness Platform that
continuously evaluates instruments, trays, equipment, workflows, and
supporting departments before a patient enters the OR. It does **not**
replace OR scheduling, sterilization management, or EHR systems — every
service module's `DISCLAIMER` says so explicitly, and every readiness
score/alert/simulation carries `human_review_required: true`.

## Foundation: Project Symphony (OR Connect, v2.8)

Orbit is built directly on top of `app/models/or_connect.py` and
`app/services/or_connect_service.py` (Project Symphony) rather than
inventing a second case-scheduling/coordination system:

* `SurgicalCase` is the one scheduled-case table — every new Orbit table
  (`CaseCart`, `ImplantRecord`, `LoanerEquipment`, `StaffReadinessRecord`,
  `EnvironmentalReadinessRecord`, `SurgicalReadinessSnapshot`,
  `ReadinessSimulationRun`) FKs to `SurgicalCase.id`.
* `CaseRiskAlert`/`CaseNotification`/`CaseReadinessScoreRecord` are
  extended (new risk types, new stakeholder roles, an additive
  `recommended_action` column) rather than duplicated.
* `or_connect_service.get_case_or_404` (promoted from a private
  `_get_case` this sprint, matching the same promotion Forge did for its
  own `_get_or_404` → `get_workflow_row_or_404`) is the one case lookup
  every Orbit service and route uses.

## No fabricated "Project Helix"

The brief names a "Project Helix" as the basis for Readiness Simulation
(Section 9). A case-insensitive, repository-wide search before writing
any Orbit code found zero references to "Helix" anywhere in this
codebase. `orbit_simulation_service.py` implements the capability as
genuinely new code — see `readiness-engine.md` for the full note. No
document or code comment in this sprint claims "Project Helix" as a
prior system; it is used only as this sprint's internal label for a
brand-new capability.

## Module map

| Module | File | Reuses |
|---|---|---|
| Surgical Readiness Engine | `orbit_readiness_engine.py` | `or_connect_service.compute_case_readiness_score` |
| Case Intelligence | `orbit_case_intelligence_service.py` | `or_connect_service.case_detail`, `digital_twin_engine`, `knowledge_repository_service` |
| Cross-Department Coordination | `orbit_coordination_service.py` | `or_connect_service.generate_stakeholder_notifications`/`list_case_notifications` |
| Readiness Alert Engine | `orbit_alert_service.py` | `or_connect_service.detect_operational_risks`, `digital_twin_engine`, `knowledge_repository_service` |
| Surgical Timeline | `orbit_timeline_service.py` | `or_connect_service.build_case_timeline`, P25's facility readiness (visibility only) |
| Executive Surgical Operations | `orbit_executive_service.py` | `or_connect_service.executive_dashboard`, `digital_twin_engine`, `atlas_dashboard_service` |
| Procedure Knowledge | `orbit_procedure_knowledge_service.py` | `knowledge_repository_service.list_articles`, `knowledge_graph_service` |
| Readiness Simulation | `orbit_simulation_service.py` | genuinely new — see above |

Frontend: `frontend/src/pages/SurgicalReadinessDashboard.tsx` at
`/surgical-readiness`, tabbed across OR Readiness / Case Intelligence /
Timeline / Alerts / Coordination / Executive / Simulation.
