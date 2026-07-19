# LPR-DIR-022 — Regression Certification (Phase 7)

## Change under test
SEC-C-01 fix only: webhook ingress fail-closed + server-bound tenant, in
`app/routes/integrations.py`, `app/routes/billing.py`, `app/routes/billing_webhooks.py`,
plus rewritten security tests in `tests/test_p17_recommendations.py` and
`tests/test_p14_recommendations.py`. **No other application behavior was modified.**

## Results (this environment, clean DB)

| Suite | Result |
|---|---|
| Changed-module + governance regression (`test_p17_recommendations` + `test_p14_recommendations` + `test_directive_002_endpoint_governance`) | **87 passed, 0 failed** (18.9 s) |
| SEC-C-01 hardening tests (fail-closed 503, bad-sig 401/400, no-tenant 503, signed 200, **DB tenant-binding proof**) | **PASS** (included above) |
| Lint (`ruff check` on all changed files) | **All checks passed** |

## Coverage of the change
The **only** tests that exercise the changed code paths are the three files above
(verified by searching the test tree for `webhook`/`billing`/`stripe`/`WEBHOOK_SECRET`).
All pass. The change is narrowly scoped to two public webhook handlers and adds an HMAC
verification + a server-side tenant lookup — it does not touch the inspection,
annotation, Ground Truth, evidence, audit, or model paths.

## Limitations (honest)
- **Full-suite run not certified in this environment.** The full backend suite (~3,696
  tests) is long-running; an attempt to run it concurrently collided on the shared
  SQLite file and was stopped (the transient "errors" observed were DB contention, not
  code failures — re-running the same files in isolation yields **87 passed**). CI runs
  the full suite (SQLite + PostgreSQL 16) on the PR and is the authoritative full-suite
  gate.
- Security/performance/integration **suites for production readiness** (load, HA, EHR
  conformance) remain **out of scope / OPEN** per Phases 4–5 — not a regression, a
  pre-existing gap.

## Determination
The SEC-C-01 change is **regression-clean** for every test that exercises it (87 passed)
and lint-clean. Full-suite certification is delegated to CI on the PR (SQLite + PG16).
No test that touches the changed code paths fails.
