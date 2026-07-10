# Project Orbit — Surgical Readiness Engine

LumenAI OS v4.5 — Section 1

## Naming disambiguation (read this first)

Two existing systems already used the phrase "surgical readiness" before
this sprint, and both were checked in full before writing any Orbit code:

1. **P25's `SurgicalReadinessScore`** (`app/models/p25_infrastructure.py`,
   table `p25_readiness_scores`, mounted at `/api/infrastructure`) — an
   *instrument-quality* index scoped to facility/tray/enterprise
   (instrument availability, contamination status, inspection
   compliance, CAPA backlog health, sterilization cycle compliance).
2. **`frontend/src/pages/SurgicalReadinessDashboard.tsx`** at the
   frontend route `/surgical-readiness` — before this sprint, a thin,
   mostly client-side demo page: heuristic scoring over
   `/api/analytics/kpi-summary`, `/api/baseline-library`, and
   `/api/infrastructure/instruments`, a hard-coded demo tray table, and
   fabricated fallback numbers on fetch failure.

Orbit's Surgical Readiness Score is a **different axis** — per scheduled
*case*, spanning Patient Procedure → Case Cart → Instrument Trays →
Individual Instruments → Implants → Equipment → Staff → Environmental →
Clinical — not instrument-quality scoped. The resolution:

* Orbit's backend is mounted at **`/api/orbit`**, never
  `/api/infrastructure` — P25's prefix and scoring stay untouched.
* The **`/surgical-readiness` frontend route is kept** and its page
  rewritten in place to be Orbit's real dashboard. This was a conscious
  choice, not an accidental overwrite: the prior page was decorative and
  fabricated fallback data on failure, which this sprint's "never
  fabricate" convention would not allow to remain in place once a real
  system existed to replace it.
* P25's score is left completely untouched; nothing in Orbit recomputes
  it a second way.

## The nine dimensions, and what each is computed from

| Dimension | Weight | Computed from |
|---|---|---|
| Patient Procedure | 10 | `SurgicalCase.procedure`/`service_line`/`surgeon` completeness |
| Case Cart | 10 | This sprint's new `CaseCart.status` |
| Instrument Trays | 15 | `or_connect_service.compute_case_readiness_score`'s `vendor_tray_arrival`/`specialty_equipment_available` factors |
| Individual Instruments | 20 | The same function's `instrument_readiness`/`inspection_completion`/`coverage_completion`/`baseline_verification`/`repair_completion` factors |
| Implants | 10 | This sprint's new `ImplantRecord` rows |
| Equipment | 10 | This sprint's new `LoanerEquipment` rows |
| Staff | 10 | This sprint's new `StaffReadinessRecord` rows |
| Environmental | 10 | This sprint's new `EnvironmentalReadinessRecord` checklist |
| Clinical | 5 | The same function's `supervisor_approvals` factor |

Three of the nine dimensions are read directly from
`or_connect_service.compute_case_readiness_score`'s own factor
breakdown — Orbit never re-derives instrument/tray/inspection/supervisor
logic a second way. `orbit_readiness_engine.compute_surgical_readiness`
persists every computation as a `SurgicalReadinessSnapshot` (trend
history, never re-derived from scratch on read).

## Endpoints

```
GET /api/orbit/case-readiness/{case_id}            — compute + persist
GET /api/orbit/case-readiness/{case_id}/history
GET /api/orbit/surgical-readiness/{case_id}         — alias, same computation
```
