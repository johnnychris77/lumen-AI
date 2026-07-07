# Supervisor Operations Board

`GET /api/operations-board` (admin/spd_manager only) · frontend route
`/operations-board`

## What it is

A leadership-facing rollup of the same queue and workload data the Smart
Inspection Queue already computes, reorganized around what a supervisor
needs to run the shift: who's carrying what workload, what's waiting for
approval, and what needs escalated attention.

## Sections

| Section | Source |
|---|---|
| Technician Workload | `technician_workload_service.technician_workload()` |
| Supervisor Queue / Pending Approvals | Queue items in the `Supervisor Review` workflow state |
| High-Risk Findings | Queue items with `risk_tier` in `High Risk`/`Critical` |
| Repair Queue | Queue items in the `Repair` workflow state |
| OR Urgent Items | Queue items with an emergency/trauma/first-case procedure priority |
| Vendor Instruments | Queue items on a vendor tray |

## Technician Assignment & Workload (Deliverable 3)

Supervisors assign (or reassign) a technician to an inspection via
`POST /api/inspections/{id}/assign`. Every assignment is recorded — the
current assignment is the latest row, so reassignment history is never
lost. Assigning a technician only advances the workflow state from
`Waiting` to `Assigned`; it never regresses an inspection that has already
progressed further (e.g. one already past AI analysis or in Supervisor
Review) — it just updates who is responsible.

Per-technician workload tracks:

- **Open inspections** — assigned inspections that haven't reached
  `Completed`.
- **Completed inspections** and the **average real inspection time**
  (creation to the first audited `Completed` workflow-state event) — `null`
  for a technician with no completed inspections yet, never a fabricated
  average.

This is a capacity view; `competency_service.technician_quality_dashboard()`
(v1.4) remains the quality-of-work view (coverage, AI confidence,
supervisor agreement) for the same technicians — the two are deliberately
separate because they answer different questions.
