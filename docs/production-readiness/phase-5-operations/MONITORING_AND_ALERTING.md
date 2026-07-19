# LPR-DIR-016 — Monitoring & Alerting (Phase 5)

**Basis:** `/health`, `/ready`, `/metrics`, `observability/` at `bd94bc5`.

## Health checks (present)
- **Liveness:** `GET /health` → k8s `livenessProbe` (restart on process death).
- **Readiness:** `GET /ready` → k8s `readinessProbe`; **DB is the hard gate** (503 on
  DB loss, traffic shed); object storage + config are soft informational sub-checks.
- **Startup:** DB-readiness retry loop with attempt logging before hard-fail.

## Metrics (present but thin)
`GET /metrics` (token/localhost-gated) exposes `lumenai_requests_total` + uptime.
Prometheus scrape configured (`observability/prometheus.yml`); 1 Grafana dashboard.
**No latency histograms, error-rate, saturation, or DB-pool/queue gauges**
(OPS-OBS-01).

## Proposed SLIs / SLOs (to adopt — none defined today)

| SLI | Proposed SLO | Source (to instrument) |
|---|---|---|
| Availability | 99.x% (set with business) | `/ready` uptime |
| API latency p95 | < X ms (per-endpoint class) | request-latency histogram (to add) |
| Error rate (5xx) | < 0.1% | status-code counter by class (to add) |
| DB pool saturation | < 80% | pool gauge (to add) |
| Queue/backlog depth | bounded | RQ/scheduler gauge (to add) |
| Readiness flaps | 0 sustained | `/ready` transitions |

## Error budgets
**MON-01 (MAJOR):** no SLOs/error budgets are defined and the metrics to measure them
don't exist yet — so there is **no quantitative production health target**. Define
SLOs, instrument the SLIs, and derive error budgets in Phase 6.

## Alerting
**MON-02 (MAJOR):** **no alert rules** (`prometheus.yml` has no `rule_files`). No page
fires on readiness loss, error spikes, latency regression, or pool saturation.
Detection is human-dependent. Add Prometheus/Alertmanager rules mapped to the SLOs
above, with routing to on-call (ties OPS-INC-01).

## Service / resource health
- **App:** `/health` + `/ready`. **CPU/Memory:** k8s requests/limits set (250m/1Gi
  backend) but **no HPA / autoscaling config** found (MON-03, MEDIUM) and no
  utilization alerts. **Database:** `/ready` gate + `pool_pre_ping`; **no DB metrics
  exported** (connections, slow queries). **Storage:** `/ready` soft-check. **API:**
  request counter only. **Queue:** APScheduler in-process (no queue-depth metric).

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| MON-01 | MAJOR | No SLOs / error budgets defined; SLIs not instrumented |
| MON-02 | MAJOR | No alert rules — detection human-dependent |
| MON-03 | MEDIUM | No HPA/autoscaling + no resource-utilization alerts |
| (OPS-OBS-01) | MAJOR | Metrics too thin to measure SLOs |

**Positive:** correct liveness/readiness design with a DB hard-gate and shedding;
Prometheus + Grafana provisioned — the scaffolding to add SLO-based alerting exists.
