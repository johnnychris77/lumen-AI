# Project Vulcan — Instrument Forensics Workspace

LumenAI AI Specialist, Section 9.

## Route

`/instrument-forensics` (frontend), backed by `/api/vulcan/forensics/*`.

## Displayed per instrument

- instrument identity (barcode/UDI, honest `untracked:` fallback)
- Digital Twin / anatomy profile references (version strings + live anatomy
  profile lookup)
- inspection history and finding timeline
- severity trend
- repair history (with classified outcome)
- recurring zones
- reliability score + breakdown
- probable contributors + alternative explanations
- recommended disposition
- supervisor review (via Section 13 feedback)

## Filters

Manufacturer, instrument family, anatomy zone, failure category, repair
vendor, facility, and date range — implemented in
`vulcan_forensics_service.search_forensics`. "Model" is not filterable at
the per-physical-instrument level: no module in this codebase tracks model
per physical instrument (only `InstrumentKnowledge` reference data does, at
the manufacturer+family level) — documented rather than fabricated.

## API

```
GET /api/vulcan/forensics/{instrument_identity}?instrument_type=...
GET /api/vulcan/forensics/search?manufacturer=...&instrument_family=...&anatomy_zone=...&failure_category=...&repair_vendor=...&facility=...&date_from=...&date_to=...
```

`forensics/search` is registered before the `forensics/{instrument_identity}`
path match in the router so the literal `search` path is never shadowed by
the identity parameter route.
