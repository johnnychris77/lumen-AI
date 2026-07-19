# LPR-DIR-016 — Operations Runbooks (Phase 5)

**Basis:** inventory + review of existing runbooks at `bd94bc5`. Verifies coverage
of the required operational procedures and flags stale/unexercised ones.

## Existing runbooks (inventory)

| Runbook | Location | Coverage |
|---|---|---|
| Operations Runbook (v1.0) | `docs/general-availability/OPERATIONS_RUNBOOK.md` | deploy, health, monitoring, logging, alerting, backup/restore, DR, HA, rollback, on-call |
| Go-live | `docs/deployment/go-live-runbook.md` | production cutover |
| Database | `docs/platform/database-runbook.md` | DB ops |
| Staging smoke test | `docs/platform/staging-smoke-test-runbook.md` | post-deploy verification |
| Backup / restore | `docs/deployment/backup-restore-guide.md`, `docs/foundation/BACKUP_RESTORE.md` | backup + restore |
| Disaster recovery | `docs/foundation/DISASTER_RECOVERY.md` | DR with **measured RTO 10.4 s** |
| Evidence | `docs/portfolio-evidence/EVIDENCE_RUNBOOK.md` | evidence handling |
| Pilot launch | `docs/pilot/pilot-launch-runbook.md` | pilot ops |

## Required-procedure coverage

| Required | Covered? | Notes |
|---|---|---|
| Startup | ✅ | OPERATIONS_RUNBOOK "Deployment"/"Health checks"; startup DB-retry in code |
| Shutdown | ⚠️ | implied (k8s termination); no explicit graceful-shutdown/drain runbook (RB-03) |
| Deployment | ⚠️ | documented but **not automated** (OPS-DEP-01) |
| Rollback | ⚠️ | procedure documented but **only demo rollback executed** (OPS-DEP-02) |
| Database restore | ✅ | backup-restore-guide + DR (executed, RTO 10.4 s) |
| Tenant recovery | ⚠️ | no dedicated per-tenant recovery runbook (RB-01) |
| Audit recovery | ⚠️ | audit is append-only/hash-chained; **reconciliation of commit-without-audit (AR-16) not runbooked** (RB-02) |
| Evidence recovery | ✅ | EVIDENCE_RUNBOOK + checksum re-verify |
| Storage failure | ✅ | OPERATIONS_RUNBOOK + `/ready` soft-check + restore |
| Authentication outage | ⚠️ | partial — re-auth path clear; **`SECRET_KEY`/JWKS outage recovery not runbooked** (RB-04) |
| Report failures | ✅ | fail-closed (not produced from partial data); regenerate from governed records |
| Digital Twin failures | ✅ | fail-closed; re-register identity |

## Staleness / consistency (honest)
- **RB-05 (MEDIUM) — runbook drift:** the v1.0 `OPERATIONS_RUNBOOK.md` states *"no
  restore has ever been executed"*, but the later **foundation DR drill executed a
  restore with a measured RTO of 10.4 s**. Runbooks across program phases are **not
  reconciled** (also Phase 2 DOC-02). Update the GA runbook to reflect the executed
  DR drill and current state.

## Findings
| ID | Sev | Finding |
|---|---|---|
| RB-01 | MEDIUM | No dedicated tenant-recovery runbook |
| RB-02 | MEDIUM | No audit-reconciliation runbook (commit-without-audit, AR-16) |
| RB-03 | LOW | No explicit graceful-shutdown/drain runbook |
| RB-04 | MEDIUM | No `SECRET_KEY`/JWKS auth-outage recovery runbook |
| RB-05 | MEDIUM | Runbook drift — GA runbook contradicts the executed foundation DR drill |

**Positive:** runbook **coverage is broad** for a pre-production platform (deploy,
DB, DR, backup, evidence, staging smoke, pilot) and DR is proven. The gaps are
specific missing procedures + reconciling stale content + exercising deploy/rollback.
