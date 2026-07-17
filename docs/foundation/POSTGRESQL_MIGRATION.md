# PostgreSQL Migration — Executed Verification

## Status

**PostgreSQL is the supported authoritative persistence layer**, selected
by `DATABASE_URL`. SQLite remains supported for development and tests.
This document records the first *executed* verification of the platform
against a real PostgreSQL server — before this sprint, PostgreSQL support
existed in code (`app/db/session.py` normalizes `postgres://`,
`alembic/env.py` reads `DATABASE_URL`, `psycopg2-binary` is a pinned
dependency) but every run this program had ever recorded used SQLite.

## Executed evidence (2026-07-16, development container)

Server: PostgreSQL 16.13 (Ubuntu), local instance, port 5433.

1. **Full Alembic chain applied cleanly** — all 13 revisions,
   `001` → `d4e8a1c93f57` (the new `governed_objects` table), producing
   **431 tables**:

   ```
   DATABASE_URL=postgresql://lumenai@127.0.0.1:5433/lumenai alembic upgrade head
   ```

2. **Rollback exercised**: `alembic downgrade -1` then `upgrade head`
   succeeded against the live PostgreSQL database.

3. **Full backend test suite executed against PostgreSQL** (separate
   `lumenai_test` database) — final result recorded in
   `FOUNDATION_ACCEPTANCE.md`.

## Real defects the PostgreSQL run surfaced (and fixed)

This is why the executed run matters: the first pass failed 110 of 3,682
tests, and every failure traced to behavior SQLite silently tolerates:

1. **Overflowing VARCHARs holding real application values.**
   `inspections.disposition` was `String(30)` while the application
   itself writes the 52-character disposition
   `"AI ANALYSIS UNAVAILABLE — MANUAL INSPECTION REQUIRED"`; three
   `supervisor_reviews` columns had the same defect. Widened in the
   models + migration `e7b2f4a86c31`.
2. **Audit evidence could be silently truncated.** `audit_logs.details`
   was `String(4000)`; real compliance-evidence-bundle events exceed
   that. SQLite stored them fully despite the declared limit (masking
   the bug); PostgreSQL rejected them. Changed to `Text` — audit
   evidence is never truncated (same migration).
3. **FK-ordering bug in recall-signal promotion**
   (`p20_network_intelligence`): the anonymized contribution row was
   flushed before the `recall_signals` row its FK references (the FK
   targets a non-PK unique column, which SQLAlchemy's flush ordering
   does not treat as a dependency). Fixed with an explicit flush.
4. **Aborted-transaction handling in the new GPAE deep health check** —
   a failed component probe left the shared session unusable on
   PostgreSQL; the check now rolls back after each failed component.
5. **Test-infrastructure PostgreSQL-isms**: explicit-id seeding that
   didn't advance the sequence (`enterprise_findings`), a fabricated
   67-character "sha256" in a fixture, and tamper-simulation tests that
   now must tamper via raw SQL because ORM tampering is blocked by the
   new audit immutability guards.

After the fixes the suite converged to **all tests passing on
PostgreSQL** (see `FOUNDATION_ACCEPTANCE.md` for exact counts).

4. **pg_dump / pg_restore round-trip executed** — including a real
   DROP DATABASE and full recovery; see `DISASTER_RECOVERY.md`.

## How to run LumenAI on PostgreSQL

```bash
export DATABASE_URL="postgresql://<user>:<password>@<host>:<port>/<db>"
cd backend
alembic upgrade head          # never create_all in production
uvicorn app.main:app
```

Notes:

* Credentials live only in the environment (or a managed secrets
  provider) — `alembic/env.py` and `app/db/session.py` contain none.
* `app.main` still calls `Base.metadata.create_all` on startup for dev
  convenience; on a migrated database this is a no-op for existing
  tables. Managed deployments should treat Alembic as the source of
  schema truth.
* Test suite against PostgreSQL:
  `DATABASE_URL=postgresql://... python -m pytest tests -q` from
  `backend/` (conftest honors a pre-set `DATABASE_URL` and only defaults
  to SQLite when unset).

## Honest limitations

* The verification server was a locally spawned instance inside an
  ephemeral development container — it proves engine compatibility and
  procedure correctness, not managed-service durability, HA, or
  connection-pool behavior under production load.
* SQLite remains the default for tests; PostgreSQL runs are opt-in via
  `DATABASE_URL` (kept this way so the 2,000+ test suite stays fast for
  every contributor).
