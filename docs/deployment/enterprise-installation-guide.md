# Enterprise Installation Guide

Companion to `docs/deployment/production-deployment-guide.md` — this
guide covers the enterprise-specific installation path (multi-facility
health systems, IT-managed rollout) rather than the single-site quick
start covered elsewhere (`docs/deployment/HOSTED_BACKEND_QUICKSTART.md`,
`RENDER_DEPLOYMENT.md`, `RAILWAY_DEPLOYMENT.md`, `FLY_DEPLOYMENT.md`).

## Prerequisites

- A supported deployment target: managed cloud (Render/Railway/Fly — see
  the respective deployment docs) or a customer-managed Kubernetes/VM
  environment.
- PostgreSQL 14+ (production; SQLite is dev/test-only — see
  `backend/app/db/session.py`).
- An environment variable set matching
  `docs/deployment/ENVIRONMENT_VARIABLE_CHECKLIST.md` — at minimum
  `DATABASE_URL`, `JWT_SECRET`/OIDC configuration
  (`docs/security/production-oidc-deployment-guide.md`), and
  `APP_ENV=production` (which disables dev-auth tokens — see
  `backend/app/enterprise_auth.py`).
- TLS termination in front of the API (load balancer or reverse proxy) —
  LumenAI does not terminate TLS itself.

## Installation sequence

1. **Provision the database.** Run Alembic migrations
   (`backend/alembic/`) against a fresh PostgreSQL instance. `Base.metadata.create_all`
   plus `ensure_columns()` (`backend/app/db/column_migrator.py`) handle
   additive schema changes on startup, but the initial schema should come
   from migrations, not just `create_all`, in a real production install.
2. **Configure tenancy.** Every table that carries clinical or
   operational data is `tenant_id`-scoped (see
   `docs/security/lumenai-enterprise-tenant-isolation-test-matrix-v1.md`).
   Decide up front whether this install is single-tenant (one hospital)
   or multi-tenant (a health system or MSP hosting multiple facilities) —
   see `docs/deployment/multi-tenant-deployment-guide.md`.
3. **Configure authentication.** Production installs must use real
   JWT/OIDC authentication (`docs/security/production-oidc-deployment-guide.md`,
   `docs/security/lumenai-production-dev-auth-removal-plan-v1.md`) — dev
   tokens (`dev-token`, `manager-token`, etc.) are rejected outright when
   `APP_ENV=production` (`backend/app/enterprise_auth.py`).
4. **Deploy the backend** (FastAPI + Uvicorn/Gunicorn) behind your load
   balancer, and the frontend** (static Vite build,
   `npm --prefix frontend run build`) behind a CDN or static host.
5. **Verify with the go-live runbook** (`docs/deployment/go-live-runbook.md`)
   and the public demo readiness checklist as a baseline smoke test
   (`docs/deployment/PUBLIC_DEMO_READINESS_CHECKLIST.md`), even for a
   private enterprise install — the same health checks apply.
6. **Enroll the site.** Use the onboarding flow in
   `docs/customer/customer-onboarding-playbook.md` and
   `docs/enterprise/site-onboarding-guide.md` to configure the facility,
   users, and RBAC roles before go-live.

## Post-install verification checklist

- [ ] `GET /health` (or equivalent) returns healthy
- [ ] A test inspection can be created, scored, and reviewed end-to-end
- [ ] Audit log entries are being written (`AuditLog` table populated)
- [ ] RBAC roles are enforced (`docs/security/lumenai-rbac-matrix-v1.md`)
- [ ] Backups are configured and a restore has been test-run
  (`docs/deployment/backup-restore-guide.md`)
- [ ] The `/api/cios/dashboard` and `/api/agents/health` endpoints report
  `ok` system health (Phase 22/23)

## Related guides

- `docs/deployment/production-deployment-guide.md` — deployment mechanics
- `docs/deployment/high-availability-guide.md` — redundancy and failover
- `docs/deployment/scaling-guide.md` — capacity planning
- `docs/deployment/disaster-recovery-guide.md` — recovery procedures
