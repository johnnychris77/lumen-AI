# Project GuardianX — AI Assurance Center

LumenAI Network v5.2, Section 1.

## An umbrella over what already exists, not a new engine

`/ai-assurance` (`/api/guardianx/assurance-center/*`) composes:

* AI Models, Status, Validation, Certification — Olympus's
  `AIModelRegistryEntry` (v5.1), unchanged.
* Approvals — GuardianX's own Governance Workflow
  (`docs/guardianx/model-governance.md`, Section 6).
* Evidence — the Evidence Ledger (`docs/guardianx/evidence-ledger.md`).
* Risk Rating — the AI Risk Registry (Section 5).
* Version History — Olympus's `version_chain` (`supersedes_id` walk),
  reused directly.

```
GET /api/guardianx/assurance-center/summary
GET /api/guardianx/assurance-center/models/{model_id}
```

No new "model" concept exists here — everything is composed from
`AIModelRegistryEntry` plus the five genuinely new tables this sprint
adds (risk entries, compliance mappings, evidence ledger entries, trust
snapshots, explainability records). See the other `docs/guardianx/*.md`
files for each.

## Compliance Mapping (Section 7)

Apollo's `regulatory_standards_catalogue.py` (v4.7) already catalogues
AAMI/AORN/Joint Commission/DNV standard references and maps *clinical
findings* to them. `ComplianceCapabilityMapping` maps a *platform
capability* to an organizational requirement instead — genuinely
different scope. When `requirement_type` is `aami` or `aorn`, the
mapping is checked against the existing catalogue's real standard codes
and flagged `verified_against_catalogue`; `internal_sop`/
`manufacturer_ifu`/`organizational_policy` references are free text,
since no catalogue of those exists. **The platform stores references
and supports traceability — it never claims regulatory certification.**

```
POST /api/guardianx/compliance-mappings
GET  /api/guardianx/compliance-mappings/{id}
GET  /api/guardianx/compliance-mappings?capability_name=...&requirement_type=...
GET  /api/guardianx/compliance-mappings/traceability-matrix
```

## AI Assurance Reports (Section 10)

Five named reports, each a read-only composition over the services
above and Olympus/Phoenix before them — no new table, no fabricated PDF
pipeline:

```
GET /api/guardianx/reports/executive
GET /api/guardianx/reports/model-validation/{model_id}
GET /api/guardianx/reports/governance
GET /api/guardianx/reports/audit-evidence-package?source_type=...&source_id=...
GET /api/guardianx/reports/knowledge-provenance
```
