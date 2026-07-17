# Pilot Site Guide — Infrastructure and Equipment Readiness

For the site IT contact and the LumenAI engineering owner. Everything in
§Infrastructure is backed by executed evidence from Foundation Sprint 1
(`docs/foundation/`) — the procedures below are the same ones already
run end-to-end in a development environment; what the site adds is the
managed, durable substrate.

## Infrastructure (mission Section 2)

| Requirement | How | Evidence base |
|---|---|---|
| Managed PostgreSQL | Provision PostgreSQL ≥14 (16 verified); set `DATABASE_URL`; run `alembic upgrade head` from `backend/` | Full chain + suite executed on PG 16.13 (`POSTGRESQL_MIGRATION.md`) |
| Durable object storage | S3-compatible bucket via `LUMENAI_STORAGE_BACKEND=s3` + `LUMENAI_S3_*`, or durable volume for `LUMENAI_LOCAL_STORAGE_DIR`; all objects governed by the `governed_objects` registry | `OBJECT_STORAGE.md` |
| TLS | Terminate at the site's reverse proxy / load balancer in front of the API and frontend; no plaintext transport on hospital networks | deployment guide (`docs/commercial-readiness/DEPLOYMENT_GUIDE.md`) |
| Backups | Schedule `python scripts/gpae_backup_restore.py backup` + `verify` (cron/systemd timer); store off-host | Executed: backup 1.10 s, SHA-256 manifest (`BACKUP_RESTORE.md`) |
| Monitoring | `/health`, `/ready`, `/metrics`, RBAC-gated `/api/gpae/health/deep`; schedule `/api/gpae/monitoring/sweep` | `MONITORING.md` |
| Alert destination | Set `SMTP_HOST`/`ALERT_EMAIL_TO` (or route the ERROR-level alert log to the site's paging tool). Verify a **real delivered test alert** before launch — the platform records delivery truthfully and never fakes it | `MONITORING.md` |
| Role-based access | Create real accounts with the platform roles (admin, spd_manager, clinical_reviewer, operator/technician, viewer); no shared logins; dev-token auth must be disabled (`ENABLE_DEV_AUTH` unset; production config validation enforces this) | `app/config.py`, `enterprise_auth` |
| Disaster recovery validation | Before go-live, execute the restore test **on the site's own environment**: backup → restore to a scratch database → verify counts/hashes → record timings in the DR runbook | Procedure executed end-to-end incl. real DB drop + corruption recovery (`DISASTER_RECOVERY.md`) |

Go-live gate: all eight rows above executed **on site infrastructure**
and recorded (screenshots/logs attached to the site record). The
development-container evidence proves the procedures; it does not
substitute for the site run.

## Equipment (mission Section 3) — on-site validation checklist

- [ ] Borescope model + serial recorded; visual inspection passed
- [ ] Camera settings documented (fixed for the pilot; changes logged)
- [ ] Lighting standardized at the inspection station
- [ ] Resolution meets the minimum used by image-quality assessment
- [ ] Calibration per manufacturer schedule, certificate on file
- [ ] Inspection workstation: OS patched, browser supported, no PHI apps sharing the screen during capture
- [ ] Network: workstation reaches the API over TLS; upload of a test image succeeds end-to-end (LCID assigned, hash verified)
- [ ] Barcode scanner (if available) maps to instrument records; manual entry fallback tested
- [ ] Ten-image dry run: capture → upload → baseline retrieval → advisory display → decision capture, all audited

The dry run uses **non-clinical test targets**, not patient-used
instruments, and its images are marked as test data — they never enter
training eligibility.
