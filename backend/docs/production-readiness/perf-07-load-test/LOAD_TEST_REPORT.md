# PERF-07 — Load-Test Harness & Baseline Measurement Report

**Finding addressed:** PERF-07 (Phase-4 Performance & Resilience review, HIGH) —
*"production load/stress testing not executed → scaling limits & p95/p99 unknown;
no production-representative environment or load tool (locust/k6/wrk/ab) available."*

**Status of this deliverable:** The missing load tool now exists in-repo, is
runnable, is regression-covered in CI, and has been executed to produce real
measured numbers. The remaining gap — running it against a
production-representative, multi-replica deployment on managed PostgreSQL —
is explicitly **still open** and is called out below. This report does not
claim production performance figures.

---

## 1. What was built

| Artifact | Path | Purpose |
| --- | --- | --- |
| Load-test harness | `backend/scripts/load_test.py` | Async, concurrent HTTP load generator (stdlib + `httpx`, already a backend dependency). Reports throughput, error rate, and the latency distribution (mean/p50/p90/p95/p99/max) per-endpoint and aggregate. Exits non-zero if the error rate exceeds a threshold, so it can gate CI or a release check. |
| Example scenario | `backend/scripts/load_scenarios/read_mixed.json` | Weighted read-mostly scenario template for a seeded environment. |
| Unit tests | `backend/tests/test_load_test_harness.py` | Covers the deterministic logic (percentiles, weighted plan expansion, summarization, scenario loading). Runs in CI without a live server. |
| Evidence | `backend/docs/production-readiness/perf-07-load-test/evidence/local_dev_c32.json` | Full JSON report from a recorded local run. |

The harness accepts any target via `--base-url`, so the *same tool* runs
unchanged against staging or a production-representative environment when one
is provisioned — nothing about it is sandbox-specific.

---

## 2. How to run it

```bash
cd backend

# Boot a server (any environment). Locally:
DATABASE_URL="sqlite:///./_lt.db" ENABLE_DEV_AUTH=true DEV_AUTH_TOKEN=dev-token \
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8077 &

# Default scenario (unauthenticated /health + /ready — reproducible anywhere):
python scripts/load_test.py --base-url http://127.0.0.1:8077 \
  --concurrency 32 --duration 15 --out results.json

# Authenticated mixed workload against a SEEDED environment:
python scripts/load_test.py --base-url https://staging.example \
  --scenario scripts/load_scenarios/read_mixed.json \
  --auth-token "$DEV_AUTH_TOKEN" --concurrency 64 --duration 60
```

The default scenario deliberately uses only `/health` (liveness — pure ASGI +
app overhead) and `/ready` (readiness — includes a real `SELECT 1` DB
round-trip). Both return `200` on any booted instance with no seeded data, so
the default run is reproducible everywhere. Authenticated, data-dependent
endpoints belong in a scenario file pointed at a seeded environment.

---

## 3. Measured baseline (local dev — NOT production)

**Environment (honest disclosure):** single-process `uvicorn --workers 1`,
SQLite (`DATABASE_URL=sqlite:///./_lt.db`), 4 vCPU sandbox container, Python
3.11.15, Linux, code at commit `deb3f1f`. Loopback (no real network). The load
generator and the server share the same host and CPU.

Concurrency sweep, default scenario (`/health` + `/ready`, 50/50), 12 s each
after a 2 s warmup:

| Concurrency | Throughput (req/s) | Errors | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | **493** | 0 | 28 | 49 | 79 | 483 |
| 32 | 332 | 0 | 65 | 282 | 425 | 927 |
| 64 | 165 | 0 | 279 | 1066 | 1543 | 2628 |
| 128 | 185 | 0 | 382 | 2306 | 4834 | 5929 |

(The c=32 row above is the recorded 15 s evidence run; the others are from the
12 s sweep.)

### What this shows

- **Zero errors** at every concurrency level up to 128 — the app stays correct
  under load; it does not shed or crash, it queues.
- **A single process saturates early.** Throughput *peaks around concurrency 16*
  (~490 req/s) and then *falls* as concurrency rises, while tail latency
  explodes (p99 from 79 ms → 4.8 s). This is the textbook single-worker
  ceiling: one Python process serving a synchronous DB path can only do so much
  work in parallel, so past its knee, added concurrency just deepens the queue.
- **Direct implication for deployment:** throughput scales by adding
  **replicas/workers**, not concurrency against one process. This is exactly
  what RES-01 (scheduler leader election, this branch) unblocks — it makes
  running multiple replicas safe by ensuring the background schedulers execute
  on only one of them.

### What this does NOT show

These numbers characterize framework + connection-pool + DB-round-trip overhead
of **one process on SQLite on a shared-CPU box**. They are **not**:

- production throughput or latency (different hardware, dedicated network,
  managed PostgreSQL with a real connection pool, multiple replicas/workers);
- representative of authenticated, data-heavy endpoints (the default scenario
  is intentionally two lightweight probes);
- a stress/soak result (no ramp-to-failure, no multi-hour endurance run).

---

## 4. Remaining open work (PERF-07 not fully closed)

| Item | Blocker | What closes it |
| --- | --- | --- |
| Run against a production-representative env | No managed Postgres / multi-replica deployment provisionable in this sandbox | Point the existing harness at staging: `--base-url https://staging … --scenario read_mixed.json` |
| Authenticated mixed-workload numbers | Requires a seeded environment with real tenant data | Seed staging, supply `--auth-token`, expand `read_mixed.json` |
| Stress test (ramp to failure) | Same env blocker | Sweep `--concurrency` upward until error rate / latency SLO breaks |
| Soak test (endurance) | Same env blocker | Long `--duration` run; watch for memory growth / leak |
| Multi-worker / multi-replica scaling curve | Same env blocker | Repeat the sweep at 2/4/N workers to plot the horizontal-scaling curve |

**Honest bottom line:** PERF-07's tooling gap is **closed** — a real, runnable,
tested load tool now exists and has produced real baseline numbers. PERF-07's
*production-load-validation* gap remains **open**, gated on a
production-representative environment that cannot be provisioned in this
sandbox. This report makes no production or clinical performance claim.
