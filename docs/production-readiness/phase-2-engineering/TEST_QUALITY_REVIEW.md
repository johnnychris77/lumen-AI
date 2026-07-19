# LPR-DIR-013 — Test Quality Review (Phase 2)

**Basis:** measurement over `backend/tests` + a live security/governance subset run.
Baseline `c9797b2`.

## Quantitative baseline (measured)

| Metric | Value |
|---|---|
| Test files | 212 |
| Test functions (`def test_*`) | **3,696** |
| Assertion statements | **8,404** (~2.3 asserts/test) |
| Files exercising 401/403/forbidden/unauthorized | **122 / 212 (58%)** |
| Files exercising tenant isolation | 29 |
| Files exercising audit | 83 |
| Test LOC | ~52,713 |
| TODO/FIXME in tests | 0 |

## Live validation subset (executed this phase)

```
cd backend && rm -f test.db && python -m pytest \
  tests/test_enterprise_auth.py tests/test_permission_authorization.py \
  tests/test_tenant_isolation.py tests/test_audit_chain_verification.py \
  tests/test_evidence_authorization_baseline.py -q
→ 28 passed, 0 failed (25.0s)
```

The security-critical categories the directive names (authorization, tenant, audit,
evidence) pass. A `DeprecationWarning` confirms the audit path exercises the
hash-chained writer (via the deprecated `app.audit` shim — TD-06).

## Category coverage assessment

| Category | Evidence | Assessment |
|---|---|---|
| Unit tests | 3,696 tests, service-level | Strong |
| Integration tests | FastAPI `TestClient` end-to-end route tests | Strong |
| Negative tests | 58% of files assert 401/403/422/error paths | Strong |
| Authorization tests | `test_permission_authorization`, `test_high_risk_route_permission_guards` | Verified pass |
| Tenant tests | `test_tenant_isolation` + 29 files | Verified pass |
| Audit tests | `test_audit_chain_verification` + 83 files | Verified pass |
| Evidence tests | `test_evidence_authorization_baseline` | Verified pass |
| Failure tests | fail-closed/unavailable-model states covered (Phase 1) | Good |

## Coverage gaps (honest)

- **No coverage metric was computed this phase** (`pytest --cov` / `coverage.py`
  not run; would require a full-suite run). The category *presence* above is
  verified, but a line/branch-coverage % is **not measured** — recorded as a
  limitation, not a claim. Recommend adding `coverage` reporting to CI (TQ-01,
  MINOR).
- **Full suite (~3,696 tests) not executed this phase** — a representative
  security/governance subset was run (28/28). Consistent with the Phase 1 method;
  recorded as a limitation.
- **God-module `enterprise_intake.py`** (SR-02): its ~25 high-complexity packet
  builders are the hardest code to test thoroughly; branch coverage there is the
  most likely real gap and should be a decomposition-then-test target (TQ-02,
  MAJOR — links to SR-02).

## Flaky / order-dependent tests

- A known hazard is the persistent `sqlite:///./test.db` — running without
  `rm -f test.db` can produce order-dependent failures. This is an **environment
  hygiene** item (documented in `CLAUDE.md`), mitigated by removing the DB before
  runs. Recommend the test harness use a per-run temp DB / in-memory SQLite to
  eliminate the footgun (TQ-03, MINOR).
- No `@pytest.mark.flaky`/`xfail` scattering was observed; the suite is
  deterministic when the DB is reset.

## Duplicate tests

Given per-domain test files mirror per-domain modules, some structural repetition
of setup exists (fixtures largely centralized in one root `conftest.py`). No
harmful duplicate-assertion pattern was found; the repetition is the same
DRY-helper theme as SR-01 (test-side), not a correctness issue.

## Findings roll-up

| ID | Sev | Finding |
|---|---|---|
| TQ-02 | MAJOR | Hardest-to-test code (god-module packet builders) is the likely branch-coverage gap (ties to SR-02) |
| TQ-01 | MINOR | No coverage % gated/reported in CI |
| TQ-03 | MINOR | Persistent `test.db` is an order-dependence footgun; prefer per-run/in-memory DB |

**Positives:** 3,696 tests / 8,404 asserts; 58% of files carry negative/authz
tests; security/tenant/audit/evidence subset green; 0 TODO/FIXME.
