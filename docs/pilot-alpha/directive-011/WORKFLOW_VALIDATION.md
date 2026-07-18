# LPA-DIR-011 — Workflow Validation

**Purpose:** verify each workflow capability operates correctly in integration.
Evidence: the 130/130 integration subset (see `SYSTEM_INTEGRATION_VALIDATION.md`).

| Capability | Expected outcome | Observed | Status |
|---|---|---|---|
| **Inspection creation** | An inspection is created with identity + state | Created; workflow state machine enforces valid transitions | ✅ Pass |
| **Session management** | Session lifecycle tracked; no orphaned captures | Session lifecycle valid; closure test passes | ✅ Pass |
| **Image ingestion** | Governed image ingested, hashed, PHI-verified | Ingest path validated on **seeded** fixtures | ⚠️ Pass (seeded; physical blocked) |
| **Metadata linkage** | Required metadata linked + validated | Metadata enforced; missing-required rejected | ✅ Pass |
| **Digital Twin linkage** | Instrument resolves to its twin; records link | Twin identity resolves; image/annotation/GT linked | ✅ Pass |
| **Baseline retrieval** | Only ACTIVE/approved baseline returned | Approved baseline retrieved; non-active excluded | ✅ Pass |
| **Evidence generation** | Complete evidence bundle with checksums | Bundle assembled + verified | ✅ Pass |
| **Audit recording** | Every transition → hash-chained audit event | Append-only, tamper-evident chain verified | ✅ Pass |
| **Report generation** | Report/evidence artifacts produced | Generated from governed records | ✅ Pass |

## Notes

* **Fail-closed behavior** is preserved: missing identity, evidence, or a required
  review step blocks promotion rather than silently passing — consistent with the
  platform's contamination-safety / false-PASS-remediation invariants.
* **Image ingestion** is validated as a **code path on seeded fixtures**; a
  lab-acquired governed image path is gated on the physical lab (Directive 010
  LRR-1 / condition C-1).

## Determination

**WORKFLOW VALIDATED (engineering level).** All nine capabilities operate
correctly in integration on governed/seeded assets; the only qualification is that
image ingestion evidence is seeded pending physical lab stand-up.
