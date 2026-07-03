# Disaster Recovery Guide

## Scope

Recovery procedures for a full or partial loss of the LumenAI production
environment — database loss, region outage, or application-tier failure.
This complements `docs/deployment/backup-restore-guide.md` (the mechanics
of taking and restoring backups) and
`docs/deployment/high-availability-guide.md` (avoiding the outage in the
first place).

## Recovery objectives

| Metric | Target | Basis |
|---|---|---|
| RPO (Recovery Point Objective) | ≤ 15 minutes | Driven by database backup/WAL-archiving frequency — see backup-restore-guide.md |
| RTO (Recovery Time Objective) | ≤ 4 hours for full environment rebuild | Infrastructure-as-code redeploy + database restore + verification |

These are target design objectives for this document's procedures, not a
contractual SLA — a specific customer's actual RPO/RTO commitment is set
in their support/SLA agreement (see
`docs/customer-success/renewal-readiness-guide.md` and the edition-level
support commitments in `docs/enterprise/commercial-packaging.md`).

## Disaster scenarios and response

### 1. Database loss or corruption
1. Stop write traffic to the affected database (take the API out of the
   load balancer pool or flip to maintenance mode).
2. Restore from the most recent backup per
   `docs/deployment/backup-restore-guide.md`.
3. Replay any available WAL/point-in-time-recovery logs to minimize data
   loss beyond the last full backup.
4. Run `ensure_columns()` / migrations to confirm the restored schema
   matches the current application version before reconnecting traffic.
5. Verify with the post-install checklist in
   `docs/deployment/enterprise-installation-guide.md`.

### 2. Application-tier failure (backend/frontend unavailable)
1. If running with multiple replicas (see
   `docs/deployment/high-availability-guide.md`), traffic should already
   have failed over automatically — confirm via `/api/agents/health` and
   `/api/cios/dashboard`'s `system_health` field.
2. If single-instance, redeploy from the last known-good build/image.
   Infrastructure-as-code (the deployment configs in
   `docs/deployment/RENDER_DEPLOYMENT.md` /
   `RAILWAY_DEPLOYMENT.md` / `FLY_DEPLOYMENT.md`) should make this a
   scripted redeploy, not a manual rebuild.

### 3. Full region/provider outage
1. Stand up the environment in a secondary region/provider using the same
   infrastructure-as-code configuration.
2. Restore the database from the most recent off-region backup copy (see
   backup-restore-guide.md's cross-region retention requirement).
3. Repoint DNS/load balancer to the new environment.
4. Communicate the outage and recovery status per the incident response
   plan (`docs/security/security-compliance-center.md` §Incident Response).

## What is NOT lost in a disaster (by design)

- **Audit trail integrity**: `AuditLog` rows are hash-chained
  (`previous_event_hash`/`event_hash`) — a restored database's audit trail
  can be verified for tamper-evidence after recovery, not just restored.
- **Governance versions**: Every `ClinicalDecisionLedgerEntry` (Phase 23)
  snapshots the governance versions active when it was written, so a
  restored ledger remains historically accurate regardless of what the
  *current* code version is at recovery time.

## Testing this plan

A disaster recovery drill (restoring a backup to a scratch environment
and running the post-install verification checklist) should be performed
at least annually and after any major schema change. Record drill results
in `docs/evidence/lessons-learned.md`.
