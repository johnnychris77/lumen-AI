# LPR-DIR-015 — Database Performance Review (Phase 4)

**Basis:** ORM/model + engine inspection at `bd94bc5`. Authoritative DB is
PostgreSQL (SQLite for tests).

## Schema / indexing (measured)

| Metric | Value |
|---|---|
| `index=True` columns | **1,595** |
| `unique=True` | 60 |
| `ForeignKey` | 18 |
| `__table_args__` (composite indexes) | 7 |
| Migrations | 13 |

**Read posture: heavily indexed** — good for point/range reads (Digital-Twin,
baseline, dataset lookups). Trade-offs: (a) **write amplification** — 1,595 indexes
add per-INSERT/UPDATE cost and storage; worth confirming each index is query-backed
(**DB-03**, tune in a load test); (b) only 18 explicit FKs across 147 models suggests
some relations rely on app-level integrity rather than DB constraints (**DB-04**).

## Connection pooling (code-confirmed)

`db/session.py`: `create_engine(DATABASE_URL, pool_pre_ping=True)` — **no explicit
`pool_size`/`max_overflow`**, so SQLAlchemy defaults apply (**QueuePool: 5 +
10 overflow = 15 connections/process**). `routers/auth_simple.py` creates a
**second engine** (its own pool).

- **DB-01 (MAJOR):** default pool (15/process) is likely **too small for production
  concurrency**; with 2 replicas × 1 worker that's ≤30 connections, but under burst
  or if `--workers` is later increased, pool exhaustion → request queueing/timeouts.
  Tune `pool_size`/`max_overflow`/`pool_timeout` to the DB's `max_connections`
  budget (and add PgBouncer for many pods).
- **DB-02 (MEDIUM):** the second engine in `auth_simple.py` fragments pooling and
  duplicates connection budget; consolidate onto one engine (ties to auth
  consolidation SEC-M-02).

## N+1 / ORM efficiency

**Eager-loading (`joinedload`/`selectinload`/`subqueryload`): 0 occurrences** across
the entire backend. Combined with heavy relationship use and 66× `_row_to_dict`
serialization helpers, lazy relationship access in loops is a **real N+1 query
risk**.

- **DB-05 (MAJOR):** N+1 risk is present and **unquantified** — list/dashboard/report
  endpoints that iterate rows and touch relationships will emit N+1 queries. Needs a
  query-count profile under representative data (SQLAlchemy echo / `EXPLAIN`) and
  targeted `selectinload` on hot list endpoints.

## Locking / transaction duration

- Session-per-request via `get_db`; commits explicit. The heavy packet/PDF builders
  (`enterprise_intake.py`) run multiple queries within a request — long
  transaction/hold time on the single worker (ties PERF-01). Recommend read-only
  transactions for reporting and shorter transaction scopes (**DB-06**, MEDIUM).
- No long-held advisory locks observed; the dataset dedup TOCTOU (Phase 3 SEC-L-01)
  is a correctness item, not a lock-contention one.

## Read / write / search benchmarks

Not run against PostgreSQL this phase (no prod-representative DB; SQLite is not
representative of Postgres planner/locking). **DB read/write/search benchmarking is
deferred** to the load test with a seeded Postgres dataset — recorded as a
limitation, not a claim.

## Database growth
See `CAPACITY_PLANNING_REPORT.md` — audit (append-only, hash-chained) and evidence
grow monotonically (retention-first, no hard delete), the dominant long-term DB
growth drivers.

## Findings roll-up
| ID | Sev | Finding |
|---|---|---|
| DB-01 | MAJOR | Default connection pool (15/proc) untuned for production concurrency |
| DB-05 | MAJOR | N+1 query risk — zero eager-loading; unquantified on list/report endpoints |
| DB-02 | MEDIUM | Second engine (`auth_simple`) fragments pooling |
| DB-06 | MEDIUM | Long report/packet transactions on single worker |
| DB-03 | MEDIUM | 1,595 indexes → write amplification; confirm each is query-backed |
| DB-04 | LOW | Only 18 explicit FKs — some relational integrity is app-level |

**Positive:** `pool_pre_ping` (dead-connection resilience), heavy read indexing,
13 tracked migrations, PostgreSQL as authoritative store.
