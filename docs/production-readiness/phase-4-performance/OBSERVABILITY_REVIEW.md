# LPR-DIR-015 — Observability Review (Phase 4)

**Basis:** `/metrics`, `/health`, `/ready`, logging inspection at `bd94bc5`.

## Present capabilities

| Signal | Status | Evidence |
|---|---|---|
| **Liveness** | ✅ | `GET /health` (process alive) → k8s `livenessProbe` |
| **Readiness** | ✅ | `GET /ready` — DB hard-gate (503 on DB loss) + storage/config soft sub-checks |
| **Metrics** | ⚠️ basic | `GET /metrics` — hand-rolled Prometheus plaintext (uptime, `lumenai_requests_total`), token- or localhost-gated |
| **Audit visibility** | ✅ | hash-chained audit is queryable; admin chain-verification endpoint (Phase 3) |
| **Structured logs** | ⚠️ | JSON logs present (observed in benchmark), but `print()` vs logger inconsistency + ~70 silent excepts (Phase 2/3) |
| **Tracing** | ❌ | no distributed tracing (OpenTelemetry) |
| **Dashboards** | ⚠️ | `observability/` assets exist; not validated against a running stack this phase |
| **Alerts** | ❌ | no alert rules found in repo |
| **Error reporting** | ⚠️ | errors surface as fail-closed status codes; no Sentry/error-aggregation integration found |

## Gap analysis — "can operators rapidly detect and diagnose failures?"

**Partially.** Operators can detect **coarse** failure (readiness 503, liveness fail,
request-count/uptime) but **cannot rapidly diagnose latency/regressions**:
- **OBS-01 (MAJOR):** metrics are minimal — **no latency histograms, no p95/p99 per
  endpoint, no error-rate/DB-pool/queue-depth gauges**. Under a production incident
  there is no per-endpoint latency signal to localize the problem.
- **OBS-02 (MAJOR):** **no distributed tracing** — a slow request across API → DB →
  storage cannot be traced end-to-end.
- **OBS-03 (MEDIUM):** **no alerting rules** — detection depends on humans watching
  dashboards; add SLO-based alerts (readiness flaps, error-rate, p99, pool
  saturation).
- **OBS-04 (MEDIUM):** logging inconsistency + ~70 silent `except: pass` (Phase 3
  SEC-INF-03) reduce failure visibility.

## Recommendations (Phase 5)
Adopt `prometheus_client` with request-latency histograms + per-endpoint labels + DB
pool/queue gauges; add OpenTelemetry tracing; wire SLO alert rules; standardize on
the structured logger and narrow/log the silent excepts; add an error-aggregation
sink.

## Assessment
The **observability primitives are correctly designed** (liveness/readiness split,
DB hard-gate, gated metrics, immutable audit) — a strong base. But production-grade
**diagnosis** depth (latency histograms, tracing, alerts) is **missing**, which is a
real operability gap for incident response.
