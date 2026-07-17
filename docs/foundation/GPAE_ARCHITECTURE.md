# GPAE Architecture — Governed Persistent AI Environment

**Project Foundation, Sprint 1.**

## Purpose

Make every governed object in LumenAI persistent, versioned, auditable,
recoverable, reproducible, and traceable — and prove each property with
executed evidence where this environment allows, or say plainly where it
does not.

## Honest scope statement (read first)

This sprint was executed in a **development container**, not a managed
production deployment. What that means:

* Everything below marked **EXECUTED** really ran here: the Alembic chain
  and the full test suite against a real PostgreSQL 16 instance, a real
  backup → destroy → restore → verify disaster-recovery exercise with
  measured timings, and hash-verified governed object storage.
* The container itself is ephemeral. Running the platform *persistently*
  still requires a managed environment (a long-lived PostgreSQL service,
  durable object storage, a configured alert destination). This sprint
  makes the code ready for that environment and proves the procedures
  work; it does not conjure the environment into existence.
* No new AI capability, clinical scope, or dashboard was added.

## Architecture

```
                    ┌─────────────────────────────┐
                    │        FastAPI app          │
                    └──────┬─────────────┬────────┘
              SQLAlchemy   │             │  governed_object_service
                           ▼             ▼
        ┌──────────────────────┐   ┌───────────────────────────┐
        │ PostgreSQL (authori- │   │ Object storage            │
        │ tative; SQLite for   │   │ (local dir or S3), fronted│
        │ dev/test)            │   │ by governed_objects       │
        │  DATABASE_URL        │   │ registry rows             │
        └──────────┬───────────┘   └────────────┬──────────────┘
                   │      hash-chained          │ SHA-256 verified
                   │      append-only           │ on every read
                   ▼                            ▼
        ┌─────────────────────────────────────────────────────┐
        │ audit_logs (immutable — ORM guards + hash chain)    │
        └─────────────────────────────────────────────────────┘
```

Root identity chain (all pre-existing, verified this sprint):
LCID image → annotation versions → Ground Truth versions → baseline links
→ frozen dataset versions → model registry entries → inference records →
Digital Twin history → audit events.

## What was already true (built by earlier sprints, verified here)

| Property | Where enforced | Evidence |
|---|---|---|
| DATABASE_URL-driven engine, postgres:// normalization | `app/db/session.py`, `alembic/env.py` | code + PG run |
| Permanent LCID identity, never reused | `dataset_governance` (unique `lcid`, per-year counter) | `test_lcid_*` suites |
| Frozen dataset immutability | `DatasetVersionFrozenError` | dataset registry suite |
| Annotation append-only versioning | `AnnotationVersion` | annotation database suite |
| Ground Truth versioned records | annotation GT service | GT suite |
| Baseline lifecycle + `IMAGE_EVIDENCE_MISSING` for metadata-only | Atlas (`baseline_image_library`) | Atlas suite |
| Hash-chained audit events, single writer | `enterprise_audit_service` + chain verification | audit suites |
| Model artifact checksum verification at load | Lens registry columns + adapter | Lens suite |

## What this sprint added (the genuine deltas)

1. **PostgreSQL verified for real** — see `POSTGRESQL_MIGRATION.md`.
2. **Governed object storage registry** (`governed_objects` table +
   `governed_object_service`) — see `OBJECT_STORAGE.md`.
3. **Audit immutability enforced at the ORM layer** (instance + bulk
   UPDATE/DELETE guards) — see `AUDIT_ARCHITECTURE.md`.
4. **Single-active-Production-model invariant** in
   `candidate_promotion.promote_candidate` — see `MODEL_REGISTRY.md`.
5. **Backup/restore tooling, executed** (`scripts/gpae_backup_restore.py`)
   — see `BACKUP_RESTORE.md`.
6. **Disaster-recovery exercise, executed with measured RTO/RPO** — see
   `DISASTER_RECOVERY.md` and `evidence/DR_EXERCISE_EVIDENCE.json`.
7. **Deep persistence monitoring + truthful alert dispatch**
   (`gpae_monitoring_service`, `/api/gpae/health/deep`) — see
   `MONITORING.md`.

## Configuration surface (all environment-driven, no secrets in code)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | authoritative database (required; PostgreSQL in production) |
| `LUMENAI_STORAGE_BACKEND` | `local` (default) or `s3` |
| `LUMENAI_LOCAL_STORAGE_DIR` | local object-store root |
| `LUMENAI_S3_*` | S3 endpoint/bucket/credentials |
| `LUMENAI_MODEL_ARTIFACTS_DIR` | model artifact directory (backup tooling) |
| `SMTP_HOST` / `ALERT_EMAIL_TO` | alert delivery destination (unset ⇒ alerts recorded, truthfully marked undelivered) |
