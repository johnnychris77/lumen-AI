# LPR-DIR-015 — Load Test Report (Phase 4)

## Honesty statement (read first)

A **production-representative load test was NOT executed.** No load-testing tool
(`locust`, `k6`, `wrk`, `ApacheBench`) is installed in this environment, and — more
fundamentally — **there is no production-representative target**: this is an
ephemeral single container with a SQLite test DB and a synchronous in-process test
client. Any throughput/latency numbers produced here would not reflect a
multi-worker ASGI deployment against PostgreSQL, and **fabricating such numbers is
prohibited**. This report therefore records what *was* measured, what a proper load
test must cover, and marks production load testing as **DEFERRED (blocking a
production PASS)**.

## What was measured (in-process, non-production)

| Workload | Result | Caveat |
|---|---|---|
| `/health` 300 iters | avg 6.94 ms, p95 7.85, p99 8.93 | in-process, SQLite |
| `/ready` 300 iters | avg 8.37 ms, p95 9.28, p99 15.82 | includes DB SELECT 1 |
| 10 threads × 50 req `/health` | ~101 req/s wall | **GIL/TestClient artifact — not capacity** |

These confirm the code path is cheap for trivial endpoints in-process; they do **not**
establish average/p95/p99 under realistic concurrency, nor throughput, saturation,
or error rate at load.

## Required load-test plan (for Phase 5, against a prod-representative env)

| Workload | Definition | Metrics to capture |
|---|---|---|
| **Normal** | expected steady-state concurrent users/inspections | avg, p95, p99 latency; throughput; error rate; CPU/mem |
| **Peak** | daily/shift peak (e.g. shift changeover) | p95/p99 under sustained peak; DB pool saturation; queue depth |
| **Burst** | sudden spike (e.g. bulk image upload, report run) | tail latency, 5xx rate, recovery time to baseline |

Target endpoints (heaviest first): enterprise packet/PDF/ZIP builders
(`enterprise_intake.py`, F/66), evidence package generation, bulk image ingestion,
dashboard/list endpoints (N+1 exposure), inspection create/close, Digital-Twin +
baseline lookups.

Tooling: `k6` or `locust` against a multi-worker (gunicorn + UvicornWorker) deploy
on a seeded PostgreSQL of representative size; capture with the `/metrics` endpoint +
DB stats; profile with `py-spy`/`EXPLAIN ANALYZE`.

Pass criteria to define with the business: e.g. p95 < Xms at N concurrent users,
error rate < 0.1%, no pool exhaustion, graceful degradation on burst.

## Status
**Load testing DEFERRED.** This is the single largest evidence gap for a production
performance PASS and is the #1 Phase 5 entry condition. It is an **environment/
prerequisite gap, not a code defect** — the code is load-testable (see
`PENETRATION_TEST_READINESS.md` analog and the plan above).
