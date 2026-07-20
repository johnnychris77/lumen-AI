# BACKUP & DISASTER-RECOVERY EXECUTION REPORT — LPR-DIR-031 / WP-4

**Commit:** `4299c40` · **Operator:** automated · **Attempt timestamp:** 2026-07-20T02:33Z.
**Precondition:** a managed authoritative PostgreSQL (WP-1/WP-6) — **not provisionable here**.

## 1. Objective
Execute backup → restore → integrity validation on the managed DB; record RTO and RPO.

## 2. Result — NOT EXECUTED on a managed database
No managed Postgres exists; the server binaries (`initdb`, `postgres`) are absent, and nothing
listens on 5432 (`evidence/PROVISIONING_PROBE.log`). Therefore:
| Required capture | Value |
|---|---|
| Managed-DB backup snapshot | **none** |
| Restore-to-clean-instance transcript | **none** |
| RTO (time to restored service) | **none — unmeasured on managed DB** |
| RPO (data-loss window) | **none — unmeasured on managed DB** |

**No RTO/RPO figure is fabricated.**

## 3. Genuinely-executed, related evidence (ANALOG only — does NOT close the managed gate)
- **Backup/restore mechanic works:** capability harness `§5` (captured
  `evidence/HARNESS_RUN.log`) seeds 1000 rows, backs up, restores, and confirms 1000 rows —
  on **SQLite**. Explicitly **rejected** as managed-DB DR evidence (DIR-030
  `BACKUP_AND_RECOVERY_VERIFICATION.md`).
- **Postgres client tooling present:** `pg_dump` / `pg_restore` available — the *tools* a real
  DR drill needs, but with no server to run against.

## 4. Exact procedure that WOULD produce the evidence (managed Postgres)
```
# RPO: note last-committed txn time before snapshot
pg_dump "$DATABASE_URL" -Fc -f backup_$(date -u +%Y%m%dT%H%M%SZ).dump      # backup
# provision a CLEAN target DB, then:
t0=$(date +%s); pg_restore -d "$RESTORE_URL" --clean --if-exists backup_*.dump; t1=$(date +%s)
echo "RTO=$((t1-t0))s"                                                       # ← RTO
psql "$RESTORE_URL" -c "select count(*) from <critical_tables>;"             # integrity parity
alembic -c backend/alembic.ini current                                       # schema head parity
```

## 5. Classification
| Item | Status |
|---|---|
| Managed-DB backup + DR drill (RTO/RPO) | **NOT EXECUTED / OPEN** |
| Backup/restore mechanic (SQLite analog) | **VERIFIED (analog only)** |
