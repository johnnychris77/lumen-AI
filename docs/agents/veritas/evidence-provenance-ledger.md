# Project Veritas — Evidence Provenance Ledger

LumenAI AI Specialist, Section 7.

## A different concept from GuardianX's EvidenceLedgerEntry

`guardianx_assurance.EvidenceLedgerEntry` (Project GuardianX, v5.2) records
what evidence backed an *AI-assurance* conclusion (knowledge/model/workflow
versions + digital signature) — it has no file_hash/storage_location/
modification_history/usage_scope fields and is not per-inspection-image
provenance. `VeritasEvidenceProvenanceRecord` is the per-evidence-object
ledger the brief actually asks for, covering all ten evidence types
(inspection image, manufacturer/vendor/organization baseline, supervisor
annotation, repair record, IFU reference, knowledge article, model
prediction, final disposition).

## Reference by ID, never a duplicate

Every provenance record points at real evidence (a `RetainedImage`, an
`Inspection`, a baseline row) by ID (`instrument_id`, `inspection_id`,
`baseline_id`) — the same reference-by-ID discipline Sage's
`SageEducationImageEntry` established for education images.

## Modification history

`append_modification` appends an `{actor, change, at}` entry to
`modification_history_json` — an append-only trail of who changed what,
never an overwrite of prior history.

## API

```
POST /api/veritas/provenance
GET  /api/veritas/provenance?inspection_id=...&evidence_type=...
```
