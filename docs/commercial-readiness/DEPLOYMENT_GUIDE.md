# LumenAI — Deployment Guide

**Commercial Readiness Program · Phase 6: Launch · Commercial Readiness, Pilot Deployment & Operational Excellence**

Objective 1 review. Every claim below distinguishes what is real and operational today from what is documented intent or aspirational scaffolding — this distinction is the single most important thing this document contributes, since several existing deployment docs already contradict each other or the actual code.

## Deployment architecture — what's real

**Render is the only deployment path actually in use.** `render.yaml` (repo root) is a genuine, wired Blueprint defining 5 services: `lumen-ai-api` (Docker web service), `lumen-ai-worker` (Docker worker), `lumen-ai-redis` (managed Redis), `lumen-ai-1` (static frontend), `lumen-ai-web` (single-origin Docker frontend with an nginx reverse proxy for cookie-auth), plus a managed Postgres database. Health check, env-var wiring (`fromDatabase`/`fromService`), and CORS pinning are all real and connected. **Render's own `autoDeploy: true` git-push webhook is the actual deploy mechanism** — not GitHub Actions.

**Railway and Fly.io are documented intent only.** `docs/deployment/RAILWAY_DEPLOYMENT.md`/`FLY_DEPLOYMENT.md` are terse cheat-sheets with no matching working config files in this repo.

**Containerization is real and CI-verified.** `docker-compose.prod.yml` orchestrates 5 services (Postgres 15, Redis 7, API, worker, nginx edge) with real health-check-gated dependency ordering, and **`enterprise-quality-gate.yml`'s CI job actually boots this full stack and runs a smoke test against it** — this is genuine, exercised verification, not just a file that exists unused.

**Kubernetes and Helm are unused parallel scaffolding.** Real, well-formed manifests exist in `k8s/` and `helm/lumenai/` (RollingUpdate strategy, resource limits, liveness/readiness probes, non-root security context) — but **no CI workflow ever runs `kubectl` or `helm` against a real cluster**, and the two configs aren't even mutually consistent (they reference different container registries). Do not present Kubernetes as an active deployment target in any customer-facing material; it is design scaffolding for a future path.

## A known, real bug worth fixing before this program's Go/No-Go review

The root-level `Dockerfile`'s `CMD` invokes `uvicorn ... --port ${PORT}` with **no default value for `$PORT`** — this will fail if run standalone without an externally-set env var. Separately, `docker/Dockerfile.worker` (used by the `release-ghcr.yml` tag-triggered release pipeline) is a literal placeholder stub (`CMD ["python","-c","print('Worker image built. Add worker entrypoint/module and update CMD.')"]`) — **the GHCR release pipeline is currently publishing a non-functional worker image.** This should be fixed before any customer relies on a tagged GHCR release.

## CI/CD — test/lint/security is real; deploy automation is mostly stubbed

Of 10 GitHub Actions workflows: `ci.yml`, `backend-compliance-tests.yml`, `security-baseline.yml`, `security-hardening-validation.yml`, and `enterprise-quality-gate.yml` are all real, substantive, and running on every push/PR. **The only workflow that actually auto-deploys anything is `github-pages-demo.yml`**, which pushes the static demo landing page to GitHub Pages. `staging-deploy.yml` and `ml-eval-nightly.yml` are explicit placeholder jobs that only `echo` a message. `deploy.yml`'s staging/production deploy jobs are also `echo`-only stubs behind a manual `workflow_dispatch` + GitHub Environment approval gate — the gating is real, but there's nothing real gated behind it yet.

## Health monitoring — three endpoints, inconsistent usage

- `GET /api/health` and `GET /health` are both trivial liveness stubs — unconditional `{"status": "ok"}`, no dependency check. These are the endpoints every deployment doc and `render.yaml` actually point health checks at.
- `GET /ready` **genuinely checks database connectivity** (`SELECT 1` via `engine.connect()`, returns HTTP 503 on failure) — this is the one endpoint that actually verifies a real dependency, but **no deployment doc or `render.yaml` config references it**. Recommend wiring Render's health check (or a K8s readiness probe, if that path is ever activated) to `/ready` instead of `/api/health`, since the current setup would report "healthy" even with a dead database connection.

`GET /metrics` is a real, minimal hand-rolled Prometheus-format endpoint (request counter + uptime gauge only — no latency/error-rate/DB-pool metrics). `observability/prometheus.yml` and Grafana provisioning config exist but **are not wired into any compose/K8s/Helm config** — no Prometheus or Grafana service is actually running anywhere. No Sentry/Datadog/APM integration exists in the codebase, despite `docs/platform/production-readiness-checklist.md` describing this as if implemented.

## Backup, disaster recovery, and rollback — documented thoroughly, implemented minimally

- **Backup/DR**: `docs/deployment/backup-restore-guide.md` and `disaster-recovery-guide.md` document real, specific targets (RPO ≤15min/RTO ≤4h, explicitly caveated as design objectives, not a contractual SLA) — but **no backup or restore script exists anywhere in this repository**, and there is no evidence a restore drill has ever been executed.
- **Rollback**: the only rollback script that actually exists and runs (`scripts/public-demo-rollback-local.sh`) rolls back the **public demo landing page's links**, not a production application or database. The documented K8s rollout-undo and Alembic downgrade procedures (`docs/platform/reliability.md`) have never been exercised — the production readiness checklist's own "Rollback" section is an unchecked template, not a completed record.
- **Alembic migrations**: confirmed still exactly 4 migration files covering 417 real table definitions (one 703 KB "baseline" migration does most of the work). All 4 have `downgrade()` functions defined, but none has ever been run in anger, and the repo's own docs contradict each other on whether migration rollback is even a supported operation (`database-runbook.md` treats it as routine; `device-master-record.md` states "migrations are forward-only; rollback requires coordination with DBA").

## Recommendation — priority order before commercial pilot deployment

1. Fix the root `Dockerfile`'s missing `$PORT` default and the `docker/Dockerfile.worker` stub — these are the two concrete, fixable bugs found in this review.
2. Point health checks at `/ready`, not `/api/health`, so a dead database connection is actually detected.
3. Write and test one real backup/restore script and run one real restore drill before claiming a tested backup strategy in any customer-facing document.
4. Do not present Kubernetes/Helm as an active deployment option until at least one `kubectl apply`/`helm install` has been exercised against a real cluster.
5. Treat "rollback strategy" as documented design intent, not a tested capability, until at least one documented procedure (Alembic downgrade or K8s rollout-undo) has actually been run once.
