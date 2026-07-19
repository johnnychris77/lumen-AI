# LPR-DIR-015 — High Availability Review (Phase 4)

**Basis:** k8s/Helm manifests + Dockerfile + health-probe inspection at `bd94bc5`.

## HA readiness matrix

| Capability | Status | Evidence |
|---|---|---|
| Stateless services | ✅ | DB is SoR; no in-process request state → replicas interchangeable |
| Health checks / liveness | ✅ | `/health` liveness; k8s `livenessProbe` → `/health` |
| Readiness probes | ✅ | `/ready` (DB hard-gate, 503 on DB loss); k8s `readinessProbe` → `/ready` |
| Redundant services | ⚠️ **inconsistent** | **k8s `replicas: 2`** (backend + frontend) but **Helm `replicas: 1`** (api + worker) — deployment-path drift (HA-01) |
| Rolling deployments | ✅ (k8s) | Deployment objects support rolling update; probes gate rollout |
| Restart policy | ✅ | k8s default `Always` |
| Persistent storage | ⚠️ | object storage external; **single PostgreSQL (SPOF, AR-06)** — no HA/replica config in repo |
| Backup strategy | ✅ | backup/restore + DR with measured RTO (foundation) |
| Worker/runtime concurrency | ⚠️ | **single uvicorn worker/pod** (no `--workers`) — HA via pods only (PERF-01) |
| Scheduler HA | ❌ | in-process APScheduler duplicates across replicas; no leader election (RES-01) |

## Resource sizing (k8s vs Helm drift)

| Path | Backend replicas | CPU req/limit | Mem req/limit |
|---|---|---|---|
| `k8s/backend-deployment.yaml` | 2 | 250m / 1000m | 512Mi / 1Gi |
| `helm/lumenai/values.yaml` | 1 | 100m / … | 256Mi / … |

**HA-01 (MAJOR):** the two deployment paths disagree on replica count and resources.
A Helm-based deploy would run **single-replica, under-resourced** — no HA and likely
memory-tight (~198 MB import baseline vs 256Mi request). Reconcile to one
authoritative, HA-correct manifest set.

## Single points of failure
1. **PostgreSQL** — one instance (AR-06). Needs managed HA / read replicas / failover.
2. **Scheduler** — no leader election (RES-01).
3. **Object storage** — external; HA is provider-dependent (document the SLO).

## Assessment
**HA foundations are present** (stateless, correct liveness/readiness split, rolling
deploys, backups) and the app is **designed to run multiple replicas**. HA is **not
yet proven or consistently configured**: single-worker pods, DB SPOF, scheduler
duplication, and k8s/Helm drift are the gaps (HA-01, PERF-01, RES-01, SCAL-01) —
all provisioning/config items for Phase 5, consistent with Phase 1 AR-06.

## Findings
| ID | Sev | Finding |
|---|---|---|
| HA-01 | MAJOR | k8s (replicas 2) vs Helm (replicas 1) + resource drift; Helm path is non-HA |
| (SCAL-01) | MAJOR | PostgreSQL SPOF — no HA/replica config (AR-06) |
| (RES-01) | MAJOR | Scheduler has no leader election (duplicates across replicas) |
| (PERF-01) | MAJOR | Single uvicorn worker/pod |
