# Quality Event Intake Engine

Codename: Project Guardian · LumenAI Quality v2.9

## Mission

Transform perioperative quality events (OR occurrence reports, SafeCare/
RLDatix/MIDAS exports, CSV imports) into structured SPD intelligence
connected to the rest of LumenAI — without becoming a second, competing
integration hub. This complements, not replaces, the existing P16/P17
healthcare-quality-safety-ecosystem integration
(`docs/integrations/healthcare-quality-safety-ecosystem.md`,
`QualitySafetyEventRecord`) — that pipeline mirrors external system records
for correlation; `QualityEvent` here is LumenAI's own first-class, narrative-
bearing quality event, purpose-built for classification, RCA, and CAPA.

## The `QualityEvent` model

One row per event, capturing intake (Section 1) and classification
(Section 2) together — the narrative and its structured interpretation are
never split across tables, so "always preserve the original narrative
alongside the structured interpretation" is true by construction, not by
convention.

Intake fields: `event_ref` (e.g. `QE-2026-A1B2C3`), `source_system`
(`safecare` / `rldatix` / `midas` / `occurrence_reporting` / `csv_import` /
`manual` / `fhir_hl7` — the last two reserved for future real integrations),
`external_event_id`, `event_date`, `facility_name`, `procedure`,
`service_line`, `case_id` (optional — links to `SurgicalCase` from OR
Connect if known at intake time), `narrative`, `reporter_role`, `severity`,
`attachments_json` (metadata only — no file storage is implemented).

## Endpoints

- `POST /api/quality-guardian/events` — create + auto-classify
- `POST /api/quality-guardian/events/import-csv` — bulk CSV import, any
  `source_system`; SafeCare/RLDatix/MIDAS exports all reduce to the same
  normalized row shape (`event_date`, `narrative`, `facility_name`,
  `procedure`, `service_line`, `case_id`, `reporter_role`, `severity`)
- `GET /api/quality-guardian/events`, `GET /api/quality-guardian/events/{id}`

## What's honestly out of scope

Real SafeCare/RLDatix/MIDAS API/webhook connectors are not implemented —
the existing `quality_safety_connectors.py` mocks are seeded-random demo
data, and this sprint doesn't change that. CSV import is the one real,
working intake path today; wiring a live connector is future work,
consistent with `fhir_hl7` being reserved rather than implemented.
