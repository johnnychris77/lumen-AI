# Project Orbit — Cross-Department Coordination

LumenAI OS v4.5 — Section 4

## Seven departments, one notification table

Project Symphony's `CaseNotification` table and its `STAKEHOLDER_ROLES`
vocabulary already covered SPD, OR (`or_charge_nurse`), Supply Chain,
Clinical Engineering, Surgeon, and Vendor Rep. Section 4 names three more
departments this sprint adds by **extending** (not duplicating)
`or_connect.py`'s `STAKEHOLDER_ROLES`:

* `infection_prevention`
* `quality`
* `biomedical_engineering`

All seven of Section 4's named departments (SPD, OR, Supply Chain,
Clinical Engineering, Infection Prevention, Quality, Biomedical
Engineering) now route through the one existing `CaseNotification`
table via `or_connect_service.generate_stakeholder_notifications`/
`list_case_notifications` — Orbit adds no second notification system.

## Shared operational timeline

"Each action is tracked through a shared operational timeline"
(`orbit_coordination_service.department_coordination_timeline`) merges
`CaseNotification` and `CaseRiskAlert` rows for a case into one
chronologically ordered list — composing two already-real tables, the
same idiom `pulse_replay_service.py` already established for merging
multiple event sources into one timeline (there, tenant-wide across
audit/event/review/execution/alert rows; here, case-scoped across
notification/risk-alert rows).

## Endpoints

```
GET  /api/orbit/cases/{case_id}/coordination       — shared timeline
POST /api/orbit/cases/{case_id}/coordinate         — detect risks + notify all departments
GET  /api/orbit/department-inbox?department=<role> — one department's inbox
```
