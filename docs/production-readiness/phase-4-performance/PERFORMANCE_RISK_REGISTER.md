# LPR-DIR-015 — Performance Risk Register (Phase 4)

Severity: **Critical / High / Medium / Low / Observation**. Blocking = must resolve
(or measure) before a production performance PASS. Baseline `bd94bc5`. Documentation
only; all items are pre-existing platform behavior.

| ID | Description | Evidence | Impact | Likelihood | Severity | Owner | Mitigation | Blocking |
|---|---|---|---|---|---|---|---|---|
| PERF-07 | **Production load/stress/soak testing not executed** (no prod-representative env/tooling) | this phase | Scaling limits & p95/p99 unknown | High | **HIGH** | SRE | Run k6/locust on multi-worker + Postgres; define SLOs | **YES (measure)** |
| SCAL-01 | Single PostgreSQL + single-worker pods → vertical ceiling; HA unproven | `Dockerfile`, k8s, AR-06/AR-08 | Global saturation under load | Med-High | **HIGH** | Infra | HA Postgres (replicas), multi-worker/pods, PgBouncer | **YES** |
| RES-01 | In-process APScheduler duplicates across replicas (no leader election) | `main.py:149-157` | Duplicate scheduled work + side effects under HA | High (with ≥2 replicas) | **HIGH** | Backend | Leader election / single scheduler pod / distributed lock | **YES** |
| DB-01 | Default connection pool (15/proc), untuned | `db/session.py` | Pool exhaustion → queueing/timeouts | Med | MEDIUM | DB Eng | Tune pool_size/overflow/timeout; PgBouncer | No |
| DB-05 | N+1 query risk (zero eager-loading) | grep (0 joinedload) | DB-load amplification on list/report endpoints | Med | MEDIUM | Backend | Profile query counts; add selectinload on hot paths | No |
| PERF-01 | Single uvicorn worker/pod (no `--workers`); CPU builders block loop | `Dockerfile` | Low per-pod throughput on heavy endpoints | Med | MEDIUM | Infra | gunicorn+UvicornWorker or more pods; offload heavy gen | No |
| PERF-05 | Slow startup (~24 s) + ~198 MB baseline | benchmark | Slow deploy/rollback/autoscale | Med | MEDIUM | Backend | Lazy-import heavy routers; trim import graph | No |
| OBS-01 | Metrics lack latency histograms/percentiles + pool/queue gauges | `/metrics` | Cannot localize latency incidents | Med | MEDIUM | SRE | prometheus_client histograms + labels | No |
| OBS-02 | No distributed tracing | code | Cannot trace slow cross-tier requests | Med | MEDIUM | SRE | OpenTelemetry | No |
| HA-01 | k8s (replicas 2) vs Helm (replicas 1) + resource drift | manifests | Helm deploy is non-HA/under-resourced | Med | MEDIUM | Infra | Reconcile to one HA-correct manifest set | No |
| SCAL-03 | Heavy report/evidence gen on request path | code | Tail latency + worker blocking | Med | MEDIUM | Backend | Offload to RQ worker | No |
| STRESS-02 | No circuit-breaker/bulkhead/timeout policy | code | DB brownout cascades to all endpoints | Med | MEDIUM | Backend | Timeouts + bulkheads | No |
| DR-03 | No automated DB failover (SPOF) | infra | Recovery = restore, higher RTO | Med | MEDIUM | Infra | Managed HA Postgres / replica promotion | No |
| CAP-01 | Retention-first → monotonic DB+storage growth | data model | Unbounded long-term cost | Med | MEDIUM | Platform | Retention/archival policy; audit partitioning | No |
| DB-03 | 1,595 indexes → write amplification | models | Slower writes/storage bloat | Low-Med | LOW | DB Eng | Confirm each index is query-backed | No |
| OBS-03 | No alerting rules | repo | Slow incident detection | Med | LOW | SRE | SLO alerts | No |
| DR-02 | WAL/PITR not configured (RPO=cadence) | foundation | Data loss window = cadence | Low | LOW | Infra | Enable WAL archiving/PITR | No |

## Summary
- **HIGH (3, blocking):** PERF-07 (load test not run), SCAL-01 (SPOF/HA), RES-01
  (scheduler duplication). **No CRITICAL** performance defect was observed — but the
  absence of a production load test means a hard PASS cannot be asserted.
- **MEDIUM (11), LOW (3).**
- **Theme:** the *design* is horizontally scalable and recovery is proven, but
  **production-scale operation is unmeasured and HA is unprovisioned**. Closing the
  three HIGH items (run the load test; provision HA DB + multi-worker; fix scheduler
  leader-election) is the path to a production PASS.
