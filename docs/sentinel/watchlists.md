# Clinical Watchlists

LumenAI v3.0 · Project Sentinel

## Eight entity types, real data behind every entry

`sentinel_watchlist_service.refresh_watchlists` computes eight dynamic
watchlists — no generic "flag anything as high-risk" model existed before
this module, so each is grounded in whatever real, already-tracked data
that entity type actually has:

| Entity type | Signal |
|---|---|
| `anatomy` | `anatomy_risk_service.anatomy_risk_dashboard`'s highest-risk zones (reused, not re-derived) |
| `instrument` | Condition findings (rust/corrosion/pitting/crack/insulation damage/missing component) grouped by `instrument_type` |
| `instrument_family` | Same condition findings, grouped by `resolve_family` |
| `manufacturer` | Deprecated `BaselineLibraryEntry` rows — an honest, real signal (any deprecation is worth watching) |
| `vendor` | Repair referrals (`RepairRequest`) by `vendor_name` |
| `tray` | Repeated replacement requests (`VendorTray.replacement_requested`) by tray name |
| `service_line` / `facility` | Open `CaseRiskAlert` count across a service line's/facility's cases (OR Connect) |

## Risk score

Each entry's `risk_score` (0-1) is the trigger count normalized against a
per-entity-type ceiling (e.g. 15 findings = 1.0 for instruments/families,
5 for manufacturers/trays where the volume is naturally lower) — never a
fabricated probability, just a bounded normalization of a real count.

## Lifecycle

Entries are idempotently upserted (`active`, keyed by tenant + entity_type
+ entity_value) — refreshing updates the risk score and reason on the
existing entry rather than duplicating it. A supervisor can explicitly
`resolve` an entry once the underlying risk has been addressed.

## Endpoints

- `POST /api/sentinel/watchlist/refresh` — recompute all eight watchlists
- `GET /api/sentinel/watchlist?entity_type=...` — list active entries, optionally filtered
- `POST /api/sentinel/watchlist/{id}/resolve`
