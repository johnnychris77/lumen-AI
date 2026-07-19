# LPR-DIR-015 — Application Performance Report (Phase 4)

**Basis:** real in-process micro-benchmarks + code/config inspection at baseline
`bd94bc5`. **Honesty statement:** these are **in-process FastAPI `TestClient`
measurements on SQLite in an ephemeral single container** — they characterize
per-request code-path cost, **not** production throughput. No
production-representative environment, ASGI multi-worker server, or PostgreSQL was
available; production-scale load/stress testing is **deferred** (see
`LOAD_TEST_REPORT.md` limitations).

## Measured (in-process, SQLite, 300 iters after warmup)

| Endpoint | code | avg | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|
| `GET /health` (liveness) | 200 | 6.94 ms | 6.87 | 7.85 | 8.93 | 10.18 |
| `GET /ready` (DB SELECT 1 + storage check) | 200 | 8.37 ms | 8.06 | 9.28 | **15.82** | 41.97 |
| `GET /metrics` (auth-gated) | 403 | 8.22 ms | 7.90 | 9.07 | 10.21 | 65.55 |

The `/ready` p99/max tail (16–42 ms) is the DB round-trip + storage sub-check.
Trivial paths are single-digit ms in-process.

## Startup / resource baseline (measured)

| Metric | Value | Implication |
|---|---|---|
| **App import/startup time** | **≈ 23.7 s** | Slow cold start → longer rolling-deploy/rollback windows, slower autoscale reaction (**PERF-05**) |
| Import-time memory (tracemalloc) | **≈ 198 MB** | Per-worker baseline footprint; drives pod memory sizing |
| Routes registered | 1,916 | Large router graph contributes to import time |

## Concurrency probe (honest caveat)

A 10-thread × 50-request probe on `/health` yielded **~101 req/s wall throughput**.
**This is a harness artifact, not a capacity number:** `TestClient` is synchronous
and Python's GIL serializes the threads against one in-process app. It does **not**
represent a real ASGI server with multiple uvicorn workers × pod replicas.
**Production throughput is uncharacterized** (PERF-07).

## Profiling — CPU / memory / I/O / async

- **CPU:** the complexity tail (Phase 2 CH-01: `enterprise_intake.py` packet/PDF
  builders up to cyclomatic **F/66**) is CPU-heavy. On a **single uvicorn worker
  per pod** (Dockerfile `uvicorn app.main:app` with **no `--workers`**), a CPU-bound
  request can block the event loop and inflate tail latency for concurrent requests
  (**PERF-01/PERF-06**).
- **Memory:** ~198 MB import baseline + per-request allocations; k8s backend request
  512Mi / limit 1Gi is plausible but should be validated under load.
- **I/O:** DB and object-storage I/O dominate real endpoints; heavy indexing
  (1,595 `index=True`) favors reads (see `DATABASE_PERFORMANCE_REVIEW.md`).
- **Async:** FastAPI is async-capable, but many handlers are sync DB calls; combined
  with single-worker, sync DB work occupies the worker thread pool.

## Per-capability latency (characterized, not load-tested)

Report/packet/evidence generation, Digital-Twin retrieval, and baseline lookup were
**not isolated-benchmarked** this phase (they require seeded governed data and auth
context). By construction: report/packet builders are the heaviest (CPU + multiple
queries); Digital-Twin/baseline lookups are indexed reads (should be fast); evidence
package generation assembles + checksums (I/O-bound). These are **characterized**
targets for the deferred load test, not measured here.

## Findings
| ID | Sev | Finding |
|---|---|---|
| PERF-05 | MAJOR | Slow startup (~24 s import) + ~198 MB baseline → deploy/rollback/autoscale latency |
| PERF-01 | MAJOR | Single uvicorn worker per pod (no `--workers`); CPU-bound handlers block the loop |
| PERF-07 | MAJOR | Production throughput/latency **not** load-tested (no prod-representative env) |

**Positive:** trivial-path latency is low in-process; `/ready` DB gate is fast; the
architecture is stateless (horizontally scalable in principle).
