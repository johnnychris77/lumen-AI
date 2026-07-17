# Disaster Recovery — Executed Exercise

## What was actually done (2026-07-16, development container)

A real, scripted DR exercise ran against the migrated PostgreSQL 16
database and local object storage. The raw evidence log is committed at
`evidence/DR_EXERCISE_EVIDENCE.json`. Steps, in order:

1. **Seed**: three governed objects registered through
   `governed_object_service` (bytes on disk + registry rows + hash-chained
   audit events).
2. **Backup**: `gpae_backup_restore.py backup` — 1.10 s; manifest
   SHA-256s recorded.
3. **Verify**: all three archives `sha256_verified`.
4. **Disaster 1 — total loss**: `DROP DATABASE lumenai WITH (FORCE)` and
   deletion of the entire object-storage directory. Both losses real,
   not simulated.
5. **Restore**: database recreated + `pg_restore`, storage and artifacts
   untarred — **10.4 s total (measured RTO for this dataset)**.
6. **Verification**: governed-object row count and audit row count
   identical to pre-disaster; `alembic_version` intact
   (`d4e8a1c93f57`); every seeded object re-read through the verified
   loader and re-passed SHA-256.
7. **Disaster 2 — artifact corruption**: one stored object's bytes
   overwritten on disk. The governed reader **detected the corruption and
   failed closed** (`GovernedObjectIntegrityError`, audited, row marked
   `integrity_intact=false`). Re-restore from the same backup recovered
   the object in **16.0 s**, after which the verified read passed again.

Result: **ALL_STEPS_PASSED**.

## RTO / RPO, stated honestly

* **Measured RTO** (this dataset, same host): 10.4 s full restore;
  16.0 s for the corruption re-restore. These scale with data volume —
  they demonstrate the procedure, not a production SLA.
* **RPO** equals the age of the last verified backup (in the exercise,
  the loss window was ~11 s because the disaster immediately followed
  the backup). In a managed deployment RPO is set by backup cadence; for
  tighter RPO than the cadence, enable PostgreSQL WAL archiving /
  point-in-time recovery — designed but **not exercised here** (no
  long-lived server to archive from).

## Scenarios covered vs. not covered

| Scenario | Status |
|---|---|
| Database loss (real DROP) | EXECUTED, recovered |
| Object-storage loss (real deletion) | EXECUTED, recovered |
| Model/object corruption (real byte tampering) | EXECUTED, detected fail-closed, recovered |
| Configuration recovery | Config is env-driven + version-controlled; re-export of env restores it (exercised implicitly by the restore run) |
| Regional/provider failure, WAL PITR, failover | NOT exercised — requires managed infrastructure; documented as future work |

## Runbook (condensed)

1. Provision replacement database/storage.
2. `gpae_backup_restore.py verify --backup <latest>` — never restore an
   unverified backup.
3. `restore --backup <latest>`.
4. `alembic current` must show the expected head; run the GPAE deep
   health check (`/api/gpae/health/deep`) — all components `ok`.
5. Spot-verify governed objects via verified reads (hash mismatches are
   loud by design).
6. Record the incident and recovery timings in the audit trail
   (`platform_alert_raised` / incident event).
