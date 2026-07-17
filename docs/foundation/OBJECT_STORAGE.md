# Governed Object Storage

## Design

Two layers, deliberately separated:

1. **Byte transport** — `app/services/object_storage.py` (pre-existing):
   writes/reads raw bytes to a local directory
   (`LUMENAI_LOCAL_STORAGE_DIR`) or S3-compatible bucket (`LUMENAI_S3_*`).
2. **Governance registry** — NEW this sprint:
   `app/models/governed_object.py` (`governed_objects` table) +
   `app/services/governed_object_service.py`. No object enters governed
   storage without a registry row.

## The Foundation Section 2 contract, field by field

| Requirement | Column / mechanism |
|---|---|
| Object ID | `object_id` (`GOBJ-<uuid4hex>`), unique, assigned once, never reused |
| SHA-256 | `sha256`, computed at registration, re-verified on every read |
| Upload timestamp | `uploaded_at` (UTC) |
| Uploader | `uploader` |
| Organization | `tenant_id` (every query filters on it — tenant isolation) |
| Retention policy | `retention_policy` (governance label; nothing is auto-deleted) |
| Storage URI | `storage_uri` + `storage_backend` |
| Version | `version` + `supersedes_object_id` chain; prior row marked `SUPERSEDED`, never edited |
| Audit linkage | every register / dedup hit / verified read / integrity failure writes a hash-chained audit event via `record_enterprise_audit_event` |
| No duplicate creation | `UniqueConstraint(tenant_id, sha256)` + service-level dedup: re-registering identical bytes returns the existing record with `deduplicated=true` and audits the hit |

Accepted categories: `borescope_image`, `baseline_image`, `report`,
`dataset_export`, `pdf`, `thumbnail`, `model_artifact`,
`supporting_evidence`.

## Integrity model (fail closed)

`load_and_verify_object` re-hashes the stored bytes on **every** access:

* hash matches → bytes returned, `last_verified_at` updated, access
  audited;
* mismatch or unreadable storage → `GovernedObjectIntegrityError`,
  `integrity_intact=false`, failure audited — corrupted bytes are never
  returned. (Mirrors the Atlas baseline-image access rule.)

## Relationship to existing image stores (no breaking rewires)

`RetainedImage` (DB-stored training bytes) and the Atlas baseline library
keep their existing storage; both already carry their own SHA-256 and
verification. The governed store is the platform-wide registry for
file-based objects (exports, reports, artifacts, evidence) and the
target for new bulk image storage. Migrating existing stores onto it is
deliberately out of scope for this sprint (no silent data moves).

## Deletion policy

Code never deletes governed objects. A delete *request* is an audited
governance action reviewed by a human; the row would be marked (not
removed) and the audit trail preserved. Rows are also never edited in
place — changed bytes mean a new version row.

## Evidence

* `tests/test_gpae_foundation.py::TestGovernedObjectStore` — register,
  audit event, dedup, verified round-trip, corruption fail-closed +
  audit, tenant isolation, supersession, input validation.
* Alembic migration `d4e8a1c93f57` (applied and downgraded/re-applied on
  real PostgreSQL 16).
* The DR exercise stored, destroyed, restored, and hash-re-verified real
  governed objects (`evidence/DR_EXERCISE_EVIDENCE.json`).
