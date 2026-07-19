# LPR-DIR-016 — Observability Operations (Phase 5)

**Basis:** `observability/` (prometheus.yml, grafana), `/metrics`, `/health`,
`/ready`, logging at `bd94bc5`. Builds on Phase 4 `OBSERVABILITY_REVIEW.md`.

## Present

| Capability | Status | Evidence |
|---|---|---|
| Liveness | ✅ | `GET /health` → k8s `livenessProbe` |
| Readiness | ✅ | `GET /ready` (DB hard-gate, 503 on DB loss; storage/config soft) |
| Metrics endpoint | ⚠️ basic | `GET /metrics` token/localhost-gated; exposes `lumenai_requests_total` + uptime only |
| Prometheus scrape | ✅ config | `observability/prometheus.yml` |
| Grafana | ⚠️ | `observability/grafana/provisioning` + 1 dashboard JSON |
| Audit visibility | ✅ | hash-chained audit queryable; admin chain-verification (Phase 3) |
| Structured logs | ⚠️ | JSON logs present; `print()` vs logger inconsistency + ~70 silent excepts |
| **Alerting** | ❌ | **prometheus.yml has no `rule_files`/alert rules** |
| **Tracing** | ❌ | no OpenTelemetry / distributed tracing |

## Gap: can operators detect + diagnose in production?

**Detection is coarse; diagnosis is weak.**
- **OPS-OBS-01 (MAJOR):** metrics expose only a request counter + uptime — **no
  latency histograms, no per-endpoint p95/p99, no error-rate/DB-pool/queue-depth
  gauges.** Grafana can only chart what `/metrics` exposes, so dashboards are thin.
- **OPS-OBS-02 (MAJOR):** **no alerting rules** — the monitoring stack is scrape-only;
  incident *detection* depends on a human watching Grafana. No page fires on
  readiness flaps, error-rate spikes, or DB-pool saturation.
- **OPS-OBS-03 (MEDIUM):** no distributed tracing → cannot localize a slow cross-tier
  request (API→DB→storage).
- **OPS-OBS-04 (MEDIUM):** logging inconsistency + silent excepts (Phase 3
  SEC-INF-03) reduce failure visibility; no error-aggregation sink (Sentry-style).

## Operator visibility summary
Operators can see: process alive (`/health`), DB-backed readiness (`/ready`), request
count + uptime, audit chain, coarse Grafana. Operators **cannot** see: per-endpoint
latency, error budgets, pool/queue health, traces. This is adequate for a
**supervised pilot with humans watching**, not for unattended production.

## Recommendations (Phase 6)
Instrument with `prometheus_client` request-latency histograms + per-endpoint labels
+ DB pool/queue gauges; add Prometheus alert rules mapped to SLOs
(`MONITORING_AND_ALERTING.md`); add OpenTelemetry tracing; standardize the logger and
add an error-aggregation sink.

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| OPS-OBS-01 | MAJOR | Metrics too thin (counter+uptime); no latency/error/pool signals |
| OPS-OBS-02 | MAJOR | No alerting rules — detection is human-dependent |
| OPS-OBS-03 | MEDIUM | No distributed tracing |
| OPS-OBS-04 | MEDIUM | Logging inconsistency + no error-aggregation sink |

**Positive:** the primitives are correctly designed (liveness/readiness split, DB
hard-gate, gated metrics, immutable audit) and Prometheus+Grafana are provisioned —
a real base to build depth on.
