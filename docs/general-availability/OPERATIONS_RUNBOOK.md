# Operations Runbook — LumenAI Version 1.0

**Status:** consolidates and indexes the real operational documentation
already built across prior phases (`docs/deployment/`,
`docs/commercial-readiness/`, `docs/release-management/`). This is not a
new operational capability — it is the single entry point Section 5/8
require, pointing to the real underlying docs and being explicit about
what has and has not actually been exercised.

## Deployment

- **Primary path**: Render (`render.yaml`) — 5 services (API, worker,
  Redis, static frontend, nginx frontend), auto-deploys on push to the
  release branch. This is the only path with real evidence of use.
- **Secondary/CI-exercised path**: `docker-compose.prod.yml`, booted and
  smoke-tested by `.github/workflows/enterprise-quality-gate.yml`.
- **Not yet real**: Kubernetes/Helm (`k8s/*.yaml`, `helm/lumenai/`) are
  well-formed but have never been applied to a live cluster;
  `docker/Dockerfile.worker` is a placeholder stub and must be fixed
  before the GHCR release pipeline publishes a working worker image.
- Full guide: `docs/commercial-readiness/DEPLOYMENT_GUIDE.md`,
  `docs/deployment/production-deployment-guide.md`.

## Health checks

- `GET /health` — trivial liveness stub, no dependency check.
- `GET /ready` — real readiness check (`SELECT 1` against Postgres).
- **Known gap**: `render.yaml`'s health check currently points at
  `/health`, not `/ready` — a dead database would still report healthy.
  Fix this before relying on Render's health-based restart behavior.

## Monitoring

- Real, DB-computed dashboards: `pulse_ai_ops_service.ai_operations_monitor()`,
  `sentinel_ai_health_service.compute_ai_health()` — model version
  distribution, inference latency, confidence distribution, drift
  detection, `model_availability_pct`.
- `GET /metrics` exposes only a request counter and an uptime gauge.
- **Known gap**: the Prometheus/Grafana configuration under `observability/`
  is not wired into any running service. No APM exists.

## Logging

- Structured JSON logs to stdout, configurable level via `LOG_LEVEL`.
- **Known gap**: no shipping to an external log aggregator.

## Alerting

- `app/notifications/notifier.py` has real Slack/Teams/email dispatch
  code, gated by env flags that default to `false` and are not configured
  anywhere in this repository.
- `pulse_alert_service.py`'s trend-based alerts write to the database only
  — they do not reach the notifier.
- **Before any pilot**: configure the relevant channel for the pilot
  tenant and wire at least critical-severity Pulse alerts to
  `notifier.dispatch_alert`, per `GO_LIVE_CHECKLIST.md` item #8.

## Backup and restore

- Procedure: `docs/deployment/backup-restore-guide.md` (RPO ≤15 min,
  RTO ≤4h targets).
- **Known gap**: no backup script exists anywhere in the repository and
  no restore has ever been executed. This is `GO_LIVE_CHECKLIST.md`
  item #4 and must close before any real pilot data is processed.

## Disaster recovery

- Runbook: `docs/deployment/disaster-recovery-guide.md` — 3 named
  scenarios, dependency-linked to the backup and HA guides.
- **Known gap**: never drilled. Recommended cadence in the doc itself is
  annual; record results in `docs/evidence/lessons-learned.md` once a
  drill actually occurs.

## High availability

- Design target: `docs/deployment/high-availability-guide.md` (multiple
  stateless replicas, hot-standby Postgres, PgBouncer).
- **Actual state**: the exercised deployment path runs single instances
  of every service. Acceptable for one narrow pilot; must close before
  any multi-site commitment (`GO_LIVE_CHECKLIST.md` item #10).

## Rollback

- The only rollback script that exists and runs
  (`scripts/public-demo-rollback-local.sh`) covers the public demo landing
  page only, not the application or database.
- Alembic migrations all define `downgrade()`, but none has ever been
  executed. Run one real rollback drill before a second pilot
  (`GO_LIVE_CHECKLIST.md` item #11).

## On-call

- No rotation, tool, or process exists today. Define at minimum an
  informal on-call owner for the duration of the first pilot
  (`GO_LIVE_CHECKLIST.md` item #8).
