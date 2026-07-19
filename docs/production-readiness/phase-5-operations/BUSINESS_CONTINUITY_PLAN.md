# LPR-DIR-016 — Business Continuity Plan (Phase 5)

**Basis:** foundation DR evidence + infra inspection at `bd94bc5`. Cross-references
Phase 4 `DISASTER_RECOVERY_REVIEW.md`.

## Backup
- **Schedule:** backup cadence is deployment-configured (managed Postgres / cron);
  `backup-restore-guide.md` targets **RPO ≤ 15 min** in the GA runbook.
- **Scope:** DB dump + governed object storage; append-only audit + immutable
  governed objects survive working-copy loss.
- **Validation:** restore was **exercised** (foundation) and integrity-verified.

## Restore testing
- **Executed** with **measured RTO 10.4 s** (foundation exercise dataset, same host).
  Integrity verified against governed records (image `image_sha256`, evidence
  checksums, hash-chained audit re-verify).

## Recovery objectives (honestly stated)
| Objective | Value | Note |
|---|---|---|
| **RTO** | 10.4 s (exercise) | **production-scale RTO not committed** (DR-01) — depends on DB size + managed failover |
| **RPO** | = backup cadence (≤ 15 min target) | **WAL/PITR not configured** (DR-02) → RPO can't beat cadence yet |

## Failover
- **BC-01 (MAJOR):** **no automated failover** — single PostgreSQL (SPOF, AR-06);
  continuity = restore-from-backup, not hot standby. Managed HA Postgres / replica
  promotion required for low-RTO continuity.

## Business continuity
- **Stateless app tier** → surviving pods continue serving during a single-pod loss;
  k8s reschedules. Continuity is therefore **DB-bound** (the SPOF).
- **Data durability** is strong: immutable + hash-verifiable governed records mean a
  restore is trustworthy (integrity-after-recovery is provable).

## Disaster communication
- **BC-02 (MAJOR):** **no disaster-communication plan** (tenant notification, status
  page, RACI) — ties to the missing incident process (OPS-INC-01). For a
  multi-tenant clinical-adjacent platform this is required before production.

## Recovery drills
- One DR restore drill executed (foundation). **BC-03 (MEDIUM):** no **recurring**
  drill cadence, and **no full failover/rollback game-day**. Establish a scheduled
  DR + incident game-day.

## Continuity workflow (summary)
Detect (alert/`/ready` 503) → declare (Sev + comms) → restore DB (+ WAL replay if
enabled) → restore/verify storage → re-verify audit chain + evidence checksums →
bring pods ready → reconcile commit-without-audit records → postmortem.

## Findings
| ID | Sev | Finding |
|---|---|---|
| BC-01 | MAJOR | No automated DB failover (single Postgres SPOF) |
| BC-02 | MAJOR | No disaster-communication plan (tenant/status/RACI) |
| BC-03 | MEDIUM | No recurring DR-drill cadence / failover game-day |
| (DR-01/DR-02) | MEDIUM | Production RTO uncommitted; WAL/PITR off (RPO=cadence) |

**Positive (strong):** DR **executed** with **measured RTO**, honest RPO, and
**provable integrity-after-recovery** — the durability foundation is genuinely
production-grade; the gaps are failover automation + comms + drill cadence.
