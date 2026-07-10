# Vendor Collaboration Portal

Codename: Project Symphony · LumenAI OR Connect v2.8

## Auth

`GET /api/or-connect/vendor-portal` and its action endpoints reuse
`require_manufacturer_auth` as-is (Bearer token + `X-Manufacturer-ID`
header) — vendor and manufacturer are the same external-party identity
concept elsewhere in this codebase, so this doesn't introduce a second auth
mechanism.

## A real scoping fix, not just a claim

The existing manufacturer-portal scorecard endpoints
(`vendor_intelligence_engine.compute_manufacturer_scorecard`) accept a
`manufacturer_id` but only use it to pick a display name from a mock pool —
there is no query anywhere that actually filters by it. **Every OR Connect
vendor-portal endpoint filters real rows by the vendor's own name** —
`or_connect_vendor_service.py` never returns a `VendorTray` or
`RepairRequest` whose `vendor_name` doesn't match the caller's identity,
and any action against another vendor's tray (e.g. confirming delivery)
is rejected with `403`, not silently scoped away or ignored.

## What a vendor can see and do

`GET /api/or-connect/vendor-portal`:
- `assigned_cases` — cases with at least one of the vendor's own trays
- `requested_trays` — the vendor's own `VendorTray` rows, any status
- `replacement_requests` — the vendor's trays flagged for replacement
- `delivery_confirmations` — the vendor's trays with a recorded delivery confirmation
- `repair_requests` — repair tickets attributed to this vendor

Actions:
- `POST /api/or-connect/vendor-portal/trays/{tray_id}/confirm-delivery` — records `delivery_confirmed_by`/`delivery_confirmed_at`
- `POST /api/or-connect/vendor-portal/trays/{tray_id}/request-replacement` — flags `replacement_requested` with notes

## Out of scope for this pass

External-researcher-style outside identity management (real vendor
accounts, self-service registration into this portal) is not built here —
`require_manufacturer_auth`'s header-claim model is reused as-is. Standing
up a genuine external identity system is a larger, separate project.
