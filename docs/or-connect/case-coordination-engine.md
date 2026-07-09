# Case Coordination Engine

Codename: Project Symphony · LumenAI OR Connect v2.8

## Purpose

Coordinate the perioperative instrument workflow — from surgical scheduling
through instrument readiness — by correlating a surgical case with the
vendor trays, inspections, repairs, and supervisor approvals that already
exist elsewhere in LumenAI. **LumenAI OR Connect does not replace Epic,
ReadySet, supply chain, or clinical engineering systems. It coordinates
quality intelligence across them.**

## The `SurgicalCase` model

`backend/app/models/or_connect.py::SurgicalCase` is new — there was no
prior case-scheduling entity in LumenAI, only inspection-level metadata
(`Inspection.procedure_priority`, `tray_id`). A case carries:

- Case ID (`case_ref`, e.g. `CASE-2026-A1B2C3`)
- Procedure, Service Line, Surgeon, Facility, Operating Room, Scheduled Start
- Vendor (the primary vendor for the case, if any)
- Explicit `supervisor_approved` / `supervisor_approved_by` / `supervisor_approved_at`

**Deliberately not duplicated on `SurgicalCase`**: instrument condition,
inspection outcomes, disposition, and coverage. These already live on
`Inspection` (via `readiness_engine`/`disposition_engine`) and are linked to
a case through a new, nullable `Inspection.case_id` column — an additive
change, mirroring how `tray_id`/`facility_name` were bolted onto
`Inspection` in earlier phases. A case's "Digital Twins", "Inspection
Status", "Clinical Readiness", and "Repair Status" are always *derived*
from its linked `Inspection`/`VendorTray`/`RepairRequest` rows at read time
(`or_connect_service.case_detail`), never stored as a second copy that could
drift from the real state.

## Vendor trays and repair requests

Two more new, additive tables:

- `VendorTray` — one row per tray (vendor-supplied or hospital-owned)
  needed for a case, with a real `requested → shipped → received →
  returned` lifecycle and a delivery-confirmation timestamp/actor.
- `RepairRequest` — one row per repair/replacement ticket, optionally
  linked to the case it's blocking, with `expected_return_date` and
  `replacement_available`.

Neither existed before Project Symphony — the closest prior art
(`TrayTrackingRecord`, `RepairHistoryRecord` in `app/models/integrations.py`)
are inbound *import mirrors* of external systems, not natively-managed
workflow state. OR Connect's tables are the system of record for the case
coordination workflow itself.

## API

`backend/app/routes/or_connect.py`, prefix `/api/or-connect`:

- `POST/GET /api/or-connect/cases`, `GET /api/or-connect/cases/{id}`
- `POST /api/or-connect/cases/{id}/link-inspection`
- `POST /api/or-connect/cases/{id}/approve`
- `POST /api/or-connect/cases/{id}/trays`, `PATCH /api/or-connect/trays/{id}`

See `case-readiness-score.md`, `operational-risk-engine.md`, and
`vendor-collaboration.md` for the remaining endpoints.
