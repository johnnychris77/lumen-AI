# LPR-DIR-029 — Rollback Validation Report (Workstream 3)

## What was implemented + verified

1. **Rollback automation in the deploy workflow** — `deploy.yml` now performs
   `kubectl rollout undo` + status re-check on any failed rollout, exiting non-zero (real
   code; see DEPLOYMENT_IMPLEMENTATION_REPORT.md). *Implemented + statically valid.*
2. **Data-layer restore drill** — executed here (harness §5): 1000 rows written, backed up
   (~8 ms via SQLite online-backup API), source cleared, and **fully restored (1000/1000
   rows)**. This demonstrates the *restore mechanic*; it is a **SQLite analog**, not the
   managed Postgres.
3. **Schema rollback safety by construction** — the Version-1.1 delta (IRC-1) adds **no
   migration** (single head `e7b2f4a86c31`, verified in harness §6), so a code rollback is
   **schema-compatible** — rolling back the app does not strand the database on a
   forward-only migration.

## What was NOT executed (honest gap)

A **true rollback exercise** in the pilot sense — deploy version A → deploy version B →
`rollout undo` to A on a **real cluster**, with recovery timing (MTTR) and post-rollback
smoke tests — **was NOT performed**, because there is no cluster/kubectl in this environment.

| Required for closure (OPS-DEP-02) | Status |
|---|---|
| Rollback exercise on a managed environment | **NOT STARTED** (no cluster) |
| Recovery timing (MTTR) measured on that env | **NOT STARTED** |
| Post-rollback smoke + data-integrity verification | **NOT STARTED** (data-layer restore shown as analog only) |

## Determination
Rollback is **automated in code** and **schema-safe by construction**, and the restore
*mechanic* is demonstrated — but an **executed cluster rollback drill with timing is NOT
done**. OPS-DEP-02 remains **NOT COMPLETE** for pilot entry.
