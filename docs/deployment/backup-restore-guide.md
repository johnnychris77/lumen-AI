# Backup & Restore Guide

## What must be backed up

| Asset | Contains | Backup approach |
|---|---|---|
| Primary PostgreSQL database | All clinical, tenant, audit, and governance data — inspections, supervisor reviews, pilot validation ground truth, the Clinical Decision Ledger, CIOS events | Automated daily full backup + continuous WAL archiving for point-in-time recovery |
| Retained training images | Opt-in, consented images stored via `app/models/retained_image.py` (de-identified, EXIF-stripped, no PHI per CLAUDE.md constraints) | Included in the same backup cadence as the database if stored as BLOBs; object-storage lifecycle policy if stored externally |
| Application configuration | Environment variables, secrets (see `docs/security/security-compliance-center.md` §Secrets Management) | Stored in the secrets manager, not backed up alongside application data — recovered by re-provisioning from the secrets manager, never from a database backup |

## What is intentionally never backed up as "recoverable secrets"

- Secret API keys are stored as SHA-256 hashes only (see CLAUDE.md
  security constraints) — they are one-way and issued once
  (`secrets.token_urlsafe(40)`). A backup restore recovers the hash, not
  the original key; a lost key must be reissued, not "restored."

## Backup cadence and retention

| Backup type | Frequency | Retention |
|---|---|---|
| Full database backup | Daily | 35 days rolling |
| WAL/continuous archiving | Continuous | Sufficient to support the 15-minute RPO target in `docs/deployment/disaster-recovery-guide.md` |
| Monthly archival snapshot | Monthly | 1 year (aligned with the audit log's minimum 1-year retention commitment across editions — see `docs/enterprise/commercial-packaging.md`) |
| Cross-region copy | Daily | Matches primary retention; stored in a separate region/provider account from production |

## Restore procedure

1. Identify the target restore point (latest backup, or a specific
   point-in-time via WAL replay for a more precise RPO).
2. Restore into an isolated environment first — never restore directly
   over a live production database without validating the restored data.
3. Run the schema/column-migration check
   (`app/db/column_migrator.py::ensure_columns`) against the restored
   database to confirm compatibility with the currently deployed
   application version.
4. Spot-check tenant isolation: confirm a query scoped to one
   `tenant_id` does not return another tenant's rows (this is the same
   check enforced by
   `docs/security/lumenai-enterprise-tenant-isolation-test-matrix-v1.md`'s
   automated tests).
5. Promote the restored environment to production per
   `docs/deployment/disaster-recovery-guide.md`'s relevant scenario.

## Restore testing

A full restore-to-scratch-environment test should be run on a schedule
(recommended: quarterly) independent of an actual incident, so the first
time a restore is attempted is never during a real outage. Record results
(restore duration, any schema drift found, data integrity spot-check
outcome) — this evidences the RTO/RPO targets in
`docs/deployment/disaster-recovery-guide.md` are actually achievable, not
just assumed.
