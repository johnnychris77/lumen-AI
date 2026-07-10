# Project Beacon — Manufacturer Intelligence Portal

LumenAI v3.5 — Section 2

## The existing `manufacturer_portal.py` is mock-only — this module is real

Before this sprint, `app/routes/manufacturer_portal.py`'s `/my-scorecard`,
`/my-defect-trends`, and `/network-benchmark` endpoints labeled a
seeded/mock scorecard (`vendor_intelligence_engine.compute_manufacturer_
scorecard`) with the caller's `X-Manufacturer-ID` header but never
actually filtered any real inspection row by manufacturer identity —
confirmed by reading that module and its engine directly before writing
any of this one.

`beacon_manufacturer_portal_service.py` is the real-data-filtered
counterpart. It resolves a manufacturer's real instrument population via
P15's national instrument registry
(`app/models/instrument_registry.py::RegistryInstrument.manufacturer_name
-> udi`), then joins that UDI set into real `Inspection` /
`InspectionFinding` rows across every tenant that has ever inspected one
of that manufacturer's instruments.

## What's covered

| Sprint requirement | Function |
|---|---|
| Approved baseline performance | `approved_baseline_performance` — `BaselineLibraryEntry` filtered by `manufacturer_name` + `approval_status == "approved"` |
| Anonymized quality trends | `anonymized_quality_trends` — real `InspectionFinding.finding_type` distribution |
| Instrument family performance | `instrument_family_performance` — grouped by `Inspection.instrument_type` |
| Common anatomy findings | `common_anatomy_findings` — grouped by `InspectionFinding.zone` |
| Corrosion trends | `corrosion_trend` — 90-day corrosion finding rate |
| Damage patterns | `damage_patterns` — every non-corrosion finding type, ranked |
| Repair recommendations | `repair_recommendations` — advisory text derived from the real finding distribution, never a fabricated confidence score |

## Customer identities are never disclosed

No function in this module ever returns a `tenant_id`. Every aggregate
is a network-wide count or rate. Any breakdown computed from fewer than
`MIN_FACILITIES` (imported directly from `network_benchmark_service.py`
— the same floor P15 and every Horizon benchmark already use) contributing
hospitals is suppressed (`suppressed: true`).

## Auth

Reuses `app.enterprise_auth.require_manufacturer_auth` as-is (Bearer
token + `X-Manufacturer-ID` header) — the same dependency
`or_connect_vendor_portal.py` already uses, since manufacturer and vendor
are the same external-party identity concept elsewhere in this codebase.

## Endpoint

```
GET /api/beacon/manufacturer-portal                              — full dashboard
GET /api/beacon/manufacturer-portal/approved-baselines
GET /api/beacon/manufacturer-portal/quality-trends
GET /api/beacon/manufacturer-portal/instrument-family-performance
GET /api/beacon/manufacturer-portal/anatomy-findings
GET /api/beacon/manufacturer-portal/corrosion-trend
GET /api/beacon/manufacturer-portal/damage-patterns
GET /api/beacon/manufacturer-portal/repair-recommendations
```
