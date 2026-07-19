# LPR-DIR-015 — Scalability Assessment (Phase 4)

**Basis:** architecture + deployment inspection at `bd94bc5`. Carries Phase 1 AR-08
(scalability uncharacterized) forward and quantifies the mechanisms.

## Scaling model

- **Stateless request handling** — the DB is the system of record; no in-process
  session state → the API is **horizontally scalable in principle** (add replicas).
- **Runtime:** Dockerfile runs **one uvicorn worker per pod** (no `--workers`);
  k8s runs **`replicas: 2`** with liveness/readiness probes. So today's concurrency
  ≈ 2 pods × 1 worker × (async I/O concurrency), scaled by adding pods.
- **Data tier:** single PostgreSQL instance (SPOF — Phase 1 AR-06); object storage
  external; Redis/RQ available.

## Per-dimension scalability

| Dimension | Scales by | Bottleneck / limit |
|---|---|---|
| Users / requests | horizontal pods | DB connection pool (DB-01) + single worker/pod (PERF-01) |
| Tenants | row-level tenant scoping | shared DB → noisy-neighbor; no per-tenant sharding |
| Inspections | pods + DB writes | audit-write-per-action + N+1 (DB-05) |
| Images | object storage (scales well) | ingestion hashing is CPU on the worker |
| Evidence packages | pods | synchronous assembly + checksum on the request path (offload to worker — SCAL-03) |
| Reports | pods | heavy packet/PDF builders (F/66) block the single worker (PERF-01) |
| Digital Twins | indexed reads | scales with DB read capacity |
| Datasets / candidate models | batch/offline | training is offline; registry reads scale |

## Bottlenecks (ranked)

1. **Single PostgreSQL instance (SPOF, AR-06)** — the hard vertical ceiling; mitigated
   only by read replicas / managed HA Postgres (not configured).
2. **Single uvicorn worker per pod (PERF-01)** — CPU-bound report/packet builders
   serialize; per-pod throughput is low for heavy endpoints.
3. **Connection pool (DB-01)** — default 15/proc caps concurrent DB work.
4. **In-process APScheduler (SCAL-02, see resilience)** — schedulers run on **every**
   replica → duplicated scheduled load and duplicate side effects (no leader
   election).
5. **N+1 queries (DB-05)** — amplify DB load on list/report endpoints as data grows.
6. **Synchronous heavy generation (SCAL-03)** — reports/evidence built on the request
   path rather than a background worker.

## Estimated scaling limits (honest, unmeasured)

**No production load test was run, so hard limits are not measured.** Directional
estimate from the mechanisms: with 2 single-worker pods + default pool + single
Postgres, the platform is suited to **pilot / low-hundreds-of-concurrent-users**
workloads; heavy report/packet endpoints will be the first to degrade under
concurrency. Scaling to production volume requires: multi-worker (gunicorn +
UvicornWorker) or more pods, a tuned pool + PgBouncer, HA Postgres (read replicas),
a distributed scheduler with leader election, and offloading heavy generation to the
worker queue. **These estimates must be confirmed by the deferred load test.**

## Findings
| ID | Sev | Finding |
|---|---|---|
| SCAL-01 | MAJOR | Single PostgreSQL + single-worker pods → vertical ceiling; HA/scale unproven (AR-06/AR-08) |
| SCAL-02 | MAJOR | In-process schedulers duplicate across replicas (no leader election) |
| SCAL-03 | MEDIUM | Heavy report/evidence generation on the request path, not offloaded to worker |

**Positive:** stateless design + external object storage + Redis/RQ availability mean
the scaling path is **well-understood and mechanical** (no redesign needed) — it is
provisioning + tuning + a background-worker split, all Phase-5 items.
