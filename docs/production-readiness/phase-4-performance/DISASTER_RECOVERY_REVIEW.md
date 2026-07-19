# LPR-DIR-015 — Disaster Recovery Review (Phase 4)

**Basis:** foundation DR evidence (`docs/foundation/DISASTER_RECOVERY.md`,
`BACKUP_RESTORE.md`) + config inspection at `bd94bc5`. This is the strongest
operational-resilience area — DR was **executed with measured objectives**.

## Backups
- Backup/restore tooling exists and was **exercised** (foundation). Governed object
  storage + DB dump. Append-only audit + immutable governed objects mean historical
  records survive working-copy loss.

## Restore testing (executed)
- **Measured RTO:** full restore of the exercise dataset in **10.4 s** (same host) —
  a real, executed number, honestly scoped to that dataset/host.
- Restore integrity verified against the governed records.

## Recovery objectives (honestly stated)
- **RTO:** 10.4 s for the exercise dataset; **production-scale RTO is not yet
  committed** (depends on DB size, storage, managed-service failover) — DR-01.
- **RPO:** equals the age of the last verified backup = **backup cadence**. For
  tighter RPO than cadence, enable **PostgreSQL WAL archiving / PITR** (documented in
  foundation) — DR-02, not yet configured in repo.

## Failover
- **DR-03 (MAJOR):** no automated DB failover — single PostgreSQL (SPOF, AR-06);
  recovery is restore-from-backup, not hot failover. Managed HA Postgres / replica
  promotion needed for low-RTO production.

## Rollback
- Application rollback = redeploy prior image (stateless pods); **model rollback** is
  checksum-verified (Directive 009). Migrations are forward-tracked (13); confirm
  **down-migration/rollback** procedures are exercised (DR-04, MEDIUM).

## Data integrity after recovery
- Post-restore integrity is supported by: image `image_sha256` hash verification,
  evidence checksums, and the **hash-chained audit** (tamper-evident — a restored
  chain can be re-verified). This is a strong integrity-after-recovery property.
- Caveat: the **audit-not-atomic-with-write** gap (RES-02/AR-16) means a crash
  mid-write could leave business data without a chain entry; recovery should include a
  reconciliation check.

## Recovery workflow (summary)
1. Detect (readiness 503 / DB unreachable). 2. Restore DB from latest verified backup
(+ WAL replay if enabled). 3. Restore/verify object storage. 4. Re-verify audit chain
+ evidence checksums. 5. Bring pods ready (`/ready` greens). 6. Reconcile any
commit-without-audit records.

## Findings
| ID | Sev | Finding |
|---|---|---|
| DR-03 | MAJOR | No automated DB failover (single Postgres SPOF); restore-based recovery only |
| DR-01 | MEDIUM | Production-scale RTO not yet committed (exercise-only 10.4 s) |
| DR-02 | MEDIUM | WAL/PITR not configured → RPO = backup cadence |
| DR-04 | MEDIUM | Down-migration/rollback procedures not evidenced as exercised |

**Positive (strong):** DR **executed** with a **measured RTO (10.4 s)** and honestly
stated RPO; integrity-after-recovery is hash-verifiable (audit chain + checksums +
image hashes). This is production-readiness done right at the process level; the gaps
are HA-failover and RPO-tightening.
