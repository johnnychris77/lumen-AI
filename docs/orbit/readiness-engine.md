# Project Orbit — Readiness Alert Engine & Readiness Simulation

LumenAI OS v4.5 — Sections 5 & 9

## Readiness Alert Engine (Section 5)

`or_connect_service.detect_operational_risks` already detects six risk
types onto the shared `CaseRiskAlert` table. Section 5 names nine risk
types; four already existed under equivalent names (vendor delay =
`vendor_tray_not_received`, repair backlog = `repair_incomplete`,
incomplete inspection = `inspection_overdue`) and are detected by
Symphony's existing logic, unchanged. Five are genuinely new, extending
`or_connect.py`'s `RISK_TYPES` (never a second alert table):

| New risk type | Detected from |
|---|---|
| `missing_instrument` | All of a case's trays are received but zero inspections are linked yet |
| `missing_implant` | Any `ImplantRecord.status == "missing"` for the case |
| `high_risk_digital_twin` | `digital_twin_engine.compute_twin_dashboard`'s `open_alerts` with severity high/critical |
| `equipment_unavailable` | Any `LoanerEquipment` still requested/shipped within 24h of case start |
| `knowledge_advisory` | Any approved `KnowledgeArticle` for the case's procedure with a non-empty `common_mistake`/`prevention_tip` |

### "Every alert includes recommended next actions"

`CaseRiskAlert` gained an additive `recommended_action` column this
sprint. New alerts persist it directly; alerts Symphony's own detector
already creates (which predate this column having a value) are enriched
at read time via the same lookup table
(`orbit_alert_service._RECOMMENDED_ACTIONS`) rather than requiring a
backfill migration.

## Readiness Simulation (Section 9) — the "Project Helix" question

The brief asks for this capability "using Project Helix." **Before
writing a single line of `orbit_simulation_service.py`, a case-
insensitive, repository-wide search for "helix" was run across
`backend/app`, `frontend/src`, and `docs/` — it returned zero matches.**
No system by that name exists anywhere in this codebase.

Rather than pretend to integrate with something that doesn't exist, this
sprint builds the capability as new code, extending the same case-scoped
pattern Sentinel's single-inspection `simulation_engine_service.py`
already established (`generate_scenarios`, `project_workflow_impact`) up
to case/OR scope:

* `simulate_case_time_shift(hours_shift)` — projects whether currently-
  pending vendor trays/loaner equipment would arrive before a
  hypothetical new scheduled start, using each item's real current
  status only.
* `simulate_instrument_unavailable(inspection_id)` — reports the real
  ready/not-ready counts behind the instrument-readiness factor and how
  they'd shift if one inspection were excluded; it does not fabricate a
  precise new overall score without actually excluding the instrument
  and recomputing.
* `simulate_vendor_tray_delayed(tray_id, delay_hours)` — projects a
  tray's arrival time from its real `shipped_at` timestamp; if the tray
  hasn't shipped yet, the projection is refused rather than fabricating
  a ship date.

Every run persists a `ReadinessSimulationRun` row
(`human_review_required: true`, the standard disclaimer) — a simulation
result is never presented as a committed decision.

## Endpoints

```
GET  /api/orbit/readiness-alerts/{case_id}
POST /api/orbit/cases/{case_id}/simulate/time-shift             {hours_shift}
POST /api/orbit/cases/{case_id}/simulate/instrument-unavailable {inspection_id}
POST /api/orbit/cases/{case_id}/simulate/vendor-tray-delay       {tray_id, delay_hours}
GET  /api/orbit/cases/{case_id}/simulations
```
