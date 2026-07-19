# LPR-DIR-027 — Data Governance Certification (Workstream 5)

Verification of data-governance software controls present in IRC-1 (`5c22345`). These are
**capabilities present in code**; they are certified as present, with the honest caveat
that they are **unexercised on real pilot data** (no real facility images exist).

| Control | Evidence in IRC-1 | Certification |
|---|---|---|
| **Ground Truth workflow** | `annotation_ground_truth_service.py`; GT built from adjudicated annotations | ✅ **Present** (code) |
| **Annotation governance** | `annotation_review_service.py` (primary/secondary/adjudication, secondary-review-blind view); `AnnotationVersion` versioning | ✅ **Present** (code) — double-blind review supported |
| **Audit integrity** | Hash-chained, tamper-evident audit via `record_enterprise_audit_event` (`app.audit.log_audit_event` delegates to it); `audit_export_service.py`, `evidence_retention_service.py` | ✅ **Present** (code) — append-only hash chain |
| **Evidence storage** | Governed object storage + hash verification on access (`governed_objects` table, migration `d4e8a1c93f57`); baseline image hash verification | ✅ **Present** (code) |
| **Dataset governance** | `dataset_governance` validation, leakage-safe splitting, dataset-freeze concepts, LCID permanent IDs | ✅ **Present** (code) |
| **Privacy controls** | `sage_workforce_privacy_service.py`; CLAUDE.md constraints (no PHI in demo data/image metadata; cross-hospital identities anonymized) | ⚠️ **Present (code) + policy** — **not validated against real PHI** (no real data processed) |

## Determination

**Data-governance software controls are PRESENT and verifiable in IRC-1.** Ground-truth,
double-blind annotation review, hash-chained audit, governed evidence storage, and dataset
governance are implemented. **However, none has been exercised on real pilot data** — there
are zero real facility images, so privacy/PHI handling is unproven in practice. Per the
honesty requirement, this certifies **software-control presence only**; it does **not**
certify operational data governance for a live pilot, which requires processing real data
on a managed environment under a signed data agreement (absent).
