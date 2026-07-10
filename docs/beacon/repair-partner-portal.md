# Project Beacon — Repair Partner Portal

LumenAI v3.5 — Section 3

## Extends the real-identity-filtered vendor pattern, not the mock one

`or_connect_vendor_service.py`'s docstring already states its own
purpose precisely: every function there filters real rows by
`vendor_name`, unlike `manufacturer_portal.py`'s mock scorecard.
`beacon_repair_partner_service.py` extends that same real-filtering
pattern rather than the mock one — with one deliberate difference:
`or_connect_vendor_service.vendor_portal_view` is scoped to a single
tenant (one hospital's own vendor portal), whereas a repair vendor
legitimately services many hospitals. Every function here filters
`RepairRequest` by `vendor_name` alone, across every tenant. This is not
a cross-tenant de-identification boundary the way the Manufacturer
Intelligence Portal's aggregate views are — a repair vendor already
knows which hospital physically shipped them an instrument for repair.

## What's covered

| Sprint requirement | Function |
|---|---|
| Repair referrals | `repair_referrals` |
| Repair history | `repair_history` |
| Failure categories | `failure_category_breakdown` — groups `RepairRequest.failure_category` (new nullable column, see below) |
| Repair turnaround | `repair_turnaround` |
| Repeat repair analysis | `repeat_repair_analysis` — instruments repaired more than once by this vendor |
| Digital Twin history | `digital_twin_history` — reuses `digital_twin_engine.list_recent_flows`'s underlying table |

## `RepairRequest.failure_category` (new column)

`RepairRequest.repair_type` was always free text. This sprint added a
nullable `failure_category` column (`app/models/or_connect.py`) with a
closed vocabulary (`FAILURE_CATEGORIES`: corrosion, mechanical_wear,
electrical_fault, insulation_defect, misuse_damage,
manufacturing_defect, other) so Section 3 and Section 7 (Repair
Intelligence) can group and benchmark repair causes. This is an additive
nullable column, automatically applied by `app/db/column_migrator.py` —
no manual migration required, the same mechanism that added
`Inspection.case_id` in an earlier sprint.

## "Repair outcomes update Digital Twins"

`record_repair_outcome` is the literal implementation of this
requirement. It never constructs an `InstrumentFlowRecord` directly —
it calls `digital_twin_engine.log_instrument_flow` (to open a flow record
tagged `station_type="repair_return"`) and then `digital_twin_engine.
complete_flow` (to close it with a real outcome — `"failed"` if the
repair's `failure_category` is corrosion/mechanical_wear/
manufacturing_defect, `"passed"` otherwise) — the same two-call pattern
every other Digital Twin flow completion in this codebase uses.

## Endpoints

```
GET  /api/beacon/repair-partner-portal
GET  /api/beacon/repair-partner-portal/referrals
GET  /api/beacon/repair-partner-portal/turnaround
GET  /api/beacon/repair-partner-portal/repeat-analysis
GET  /api/beacon/repair-partner-portal/digital-twin-history/{instrument_identity}
POST /api/beacon/repair-partner-portal/repairs/{repair_id}/record-outcome
```

Auth: `require_manufacturer_auth` (Bearer token + `X-Manufacturer-ID`
header used as the vendor's identity) — reused as-is.
