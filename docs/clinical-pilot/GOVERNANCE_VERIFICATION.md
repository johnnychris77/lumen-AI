# Governance Verification (Mission Section 9)

Each item verified against enforcing code and passing tests —
re-validated this development cycle on both SQLite (3683 passed) and
PostgreSQL 16 (full suite green after the Foundation fixes). This is
software-governance verification; the weekly on-site spot-check during
the pilot is Form E in `PILOT_OBSERVATION_FORMS.md`.

| Item | Enforcement | Verified by |
|---|---|---|
| LCID assignment | Unique `lcid` + per-year atomic counter; assigned once, never reused (`dataset_governance`, `lcid_service`) | LCID/dataset-registry suites; DB-level uniqueness now enforced on PostgreSQL |
| Audit trail completeness | Single hash-chained writer (`enterprise_audit_service`); every governed action audited; ORM immutability guards (update/delete/bulk) | audit suites incl. tamper-detection via out-of-band SQL; `test_gpae_foundation.py::TestAuditImmutability` |
| Ground Truth versioning | Append-only GT versions; supersession is a new row (`annotation_ground_truth_service`) | annotation-database suite |
| Annotation versioning | `AnnotationVersion` append-only; edits create versions | annotation suites |
| Baseline linkage | ACTIVE `BaselineImageLink` cites approved LCID images; SHA-256 re-verified on every access, fail-closed; legacy metadata-only marked `IMAGE_EVIDENCE_MISSING` | Atlas suite; live-path comparator tests |
| Digital Twin linkage | Inspection/observation/history rows accumulate per instrument; nothing deleted | twin + Canvas timeline suites |
| Model version tracking | `ModelRegistryEntry` with artifact checksum verified at load; single-active-Production invariant | Lens suites; `TestSingleActiveProductionModel` |
| Inference traceability | Result contract carries `inspection_id`, `image.lcid_image_id`, `image.sha256`, `model.version`/maturity; identity mismatch fails closed | Sprint-2 contract tests; false-PASS remediation tests A–J |

No gaps found. Any pilot-time deviation observed via Form E is a
safety-monitoring event (mission Section 7), not a paperwork item.
