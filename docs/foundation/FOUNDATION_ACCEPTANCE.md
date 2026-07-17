# Foundation Sprint 1 — Acceptance Record

Executed 2026-07-16/17 in a development container. Every item below is
labeled EXECUTED (it ran here, with the evidence cited) or
VERIFIED-BY-EXISTING-SUITE (long-standing enforcement whose tests ran in
the regression suites) or DEFERRED (requires a managed environment;
explicitly not faked).

## Section 16 verification checklist

| Item | Status | Evidence |
|---|---|---|
| PostgreSQL migration | EXECUTED | Full 13-revision Alembic chain → 431 tables on PostgreSQL 16.13; downgrade/re-upgrade exercised (`POSTGRESQL_MIGRATION.md`) |
| Object storage persistence | EXECUTED | `governed_objects` registry + verified reads; DR round-trip restored objects byte-identical (`OBJECT_STORAGE.md`) |
| LCID permanence | VERIFIED-BY-EXISTING-SUITE | unique `lcid` + per-year counter; constraint now also enforced on PostgreSQL (`LCID_PERSISTENCE.md`) |
| Dataset immutability | VERIFIED-BY-EXISTING-SUITE | `DatasetVersionFrozenError` (`DATASET_REGISTRY.md`) |
| Model registry | EXECUTED (new invariant) | single-active-Production guard + checksum-at-load; `TestSingleActiveProductionModel` (`MODEL_REGISTRY.md`) |
| Baseline persistence | VERIFIED-BY-EXISTING-SUITE | Atlas lifecycle + `IMAGE_EVIDENCE_MISSING` (`BASELINE_PERSISTENCE.md`) |
| Ground Truth versioning | VERIFIED-BY-EXISTING-SUITE | append-only GT versions (`GROUND_TRUTH_VERSIONING.md`) |
| Annotation versioning | VERIFIED-BY-EXISTING-SUITE | `AnnotationVersion` append-only rows |
| Digital Twin persistence | VERIFIED-BY-EXISTING-SUITE | history rows, nothing deleted (`DIGITAL_TWIN_PERSISTENCE.md`) |
| Backup | EXECUTED | 1.10 s backup with SHA-256 manifest, verified (`BACKUP_RESTORE.md`) |
| Restore | EXECUTED | 10.4 s full restore after real DB drop + storage deletion; row counts and object hashes verified (`DISASTER_RECOVERY.md`) |
| Monitoring | EXECUTED | deep health check across 7 persistence components + truthful alert dispatch; `TestGpaeMonitoring` (`MONITORING.md`) |
| Disaster recovery | EXECUTED | database loss, storage loss, artifact corruption — all recovered; `evidence/DR_EXERCISE_EVIDENCE.json` |
| Audit integrity | EXECUTED (new guards) | ORM immutability guards (instance + bulk) + pre-existing hash chain; `TestAuditImmutability` (`AUDIT_ARCHITECTURE.md`) |

## Secrets audit (Objective 13)

Scanned `backend/app` for hardcoded secrets: none found. All credentials
(database URL, SMTP, S3, auth tokens) are environment-driven via
`app/config.py`, which additionally **fails validation in production**
if `DEV_AUTH_TOKEN` remains the dev default; `enterprise_auth` rejects
non-JWT dev tokens in production. Alembic reads `DATABASE_URL` from the
environment and embeds no credentials. No auth behavior was changed this
sprint.

## Validation runs

| Check | Result |
|---|---|
| `ruff check app tests` | All checks passed |
| Frontend build (`npm run build`) | ✓ built in 4.20 s |
| New Foundation tests (`tests/test_gpae_foundation.py`) | 17 passed |
| Full backend suite on SQLite | see below |
| Full backend suite on PostgreSQL 16 | see below |

Full-suite results (executed in this container):

* **SQLite (default test engine):** `3683 passed, 2 skipped, 0 failed`
  (12:11).
* **PostgreSQL 16.13:** first-ever run failed 110 tests — every failure a
  real SQLite-masked defect or test PostgreSQL-ism (see
  `POSTGRESQL_MIGRATION.md`). After the fixes, the full re-run was
  `3682 passed, 2 skipped, 1 failed` (10:41); the one remaining failure
  (the recall-signal FK-ordering bug) was then fixed and its test files
  re-verified green against PostgreSQL (`86 passed`, including the
  previously failing test). SQLite's clean full run above includes all
  of these fixes.

## Definition-of-Done honesty assessment

The DoD items that are *code properties* (identity, versioning,
immutability, traceability, registry, audit, monitoring, verified
backup/restore/DR procedures) are met with the evidence above. Two DoD
items are *environmental* and remain DEFERRED, stated plainly:

1. **"PostgreSQL is authoritative" / "no governed evidence depends on
   temporary storage"** — the platform now runs verified on PostgreSQL
   and governed object storage, but this repository still ships no
   long-lived deployment; every current environment (including the one
   this sprint executed in) is ephemeral. Standing up the managed
   database/storage/alert-destination is the same prerequisite recorded
   in `docs/controlled-production/FINAL_RELEASE_DECISION.md`.
2. **Scheduled automated backups + monitoring sweeps** — tooling and
   endpoints exist and are exercised; no scheduler runs in an ephemeral
   container.

Within those stated bounds, the completion statement below is accurate
at the level of platform capability, with persistence of any specific
deployment contingent on provisioning the managed environment:

> LumenAI now operates on a governed persistent AI platform. Every
> governed object has a permanent identity, complete provenance,
> auditability, recoverability, and reproducibility suitable for
> regulated healthcare AI development.

This record makes no claim of FDA clearance or regulatory approval, and
changes no standing release decision.
