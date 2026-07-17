# Backup and Restore — Tooling and Executed Test

## Tooling (NEW): `backend/scripts/gpae_backup_restore.py`

One CLI covering the three persistence surfaces:

| Component | Backup mechanism | Restore mechanism |
|---|---|---|
| Database (PostgreSQL) | `pg_dump --format=custom` | `pg_restore --clean --if-exists --no-owner` |
| Database (SQLite dev) | sqlite3 online backup API | file copy |
| Object storage (local backend) | tar.gz of `LUMENAI_LOCAL_STORAGE_DIR` | untar (replaces dir) |
| Model artifacts | tar.gz of `LUMENAI_MODEL_ARTIFACTS_DIR` | untar (replaces dir) |

Every backup writes `MANIFEST.json` with the SHA-256 of each archive.
`verify` re-hashes all archives against the manifest; `restore` refuses
to run unless verification passes, and refuses cross-engine restores.
All phases print measured timings.

```bash
python scripts/gpae_backup_restore.py backup  --out  <dir>
python scripts/gpae_backup_restore.py verify  --backup <dir>/gpae-backup-<ts>
python scripts/gpae_backup_restore.py restore --backup <dir>/gpae-backup-<ts>
```

For an S3 object-storage backend, use provider replication/versioning;
the local tar path covers the `local` backend this repository runs.

## Executed evidence (2026-07-16, development container)

Against the real PostgreSQL 16 database carrying the full 431-table
migrated schema plus seeded governed objects and audit events
(`evidence/DR_EXERCISE_EVIDENCE.json`):

| Measurement | Value |
|---|---|
| Backup (db + object storage + artifacts) | **1.10 s** |
| Manifest verification | all three components `sha256_verified` |
| Full restore after real DB drop + storage deletion | **10.4 s** |
| Post-restore checks | row counts identical, alembic revision intact, every object re-passed SHA-256 verified read |

Scheduling note (honesty): "automated backups" here means the tooling is
scriptable and cron-ready; **no scheduler is running** in this ephemeral
container because there is nothing persistent to schedule against. A
managed deployment schedules `backup` + `verify` (e.g. cron/systemd
timer) and alerts on failure via the monitoring service.

The numbers above are small-data, same-host measurements from a
development container — procedure-correctness evidence, not a
production-scale RTO commitment. See `DISASTER_RECOVERY.md` for the full
exercise including the corruption scenario.
