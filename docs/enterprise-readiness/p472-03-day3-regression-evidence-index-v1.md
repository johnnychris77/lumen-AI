# P472-03 — Day 3: Regression Evidence Index (v1)

**Program:** P472-03 Enterprise Tenant Isolation · **PR #181 (DRAFT)**
All runs use `cd backend && python -m pytest ...` from the `backend/` directory (per CLAUDE.md), on
a **fresh** `test.db` where noted (the shared SQLite file accumulates rows across runs and must be
reset to avoid false positives — see note 1). Ruff: `ruff check` clean on every changed file.

## 1. Changed files (Day 3)

| File | Change | Commit |
|---|---|---|
| `app/routes/vendor_analytics.py` | AW-08b: `resolve_tenant` + `_tenant_inspections` on 7 routes | `137e9b1` |
| `app/routes/accreditation.py` | AW-08a/AW-04: verified-tenant scope + ownership 404 | `fbd2581` |
| `app/auth/tenant_scope.py` | PA-1: security log on privileged cross-tenant resolution | `b7b2295` |
| `app/services/guardianx_audit_replay_service.py`, `app/routes/guardianx_assurance.py` | AW-08c: tenant-scoped replay | `ae54f5e` |
| `tests/tenant_isolation_sweep_runner.py` | GD-3 oracle: `\sWHERE\s` detector | `51c2133` |
| `tests/test_p472_03_batch2_remediation.py` | census 181→190; PA-1 logging regression tests | `137e9b1`,`fbd2581`,`b7b2295` |
| `tests/test_p19_accreditation.py` | legacy smoke tests select tenant via verified header | `fbd2581` |
| `tests/test_guardianx_assurance.py` | replay smoke seeds inspection in caller's tenant | `ae54f5e` |
| `tests/test_p472_03_application_wide_isolation.py` | oracle negative-control tests | `51c2133` |

## 2. Targeted regression (all on fresh `test.db`)

| Area | Command (`-k`) | Result |
|---|---|---|
| vendor analytics + accreditation | `accreditation or vendor_analytic or vendor_scorecard` | pass (XPASS tripwires excluded; see §4) |
| GuardianX assurance (full file) | `tests/test_guardianx_assurance.py` | **23 passed** |
| batch2 resolver unit + census + PA-1 log | `TestTheRule or privileged or not_logged or route_table or platform_administrator or development_tokens or disagreeing or no_membership or several_memberships` | **31 passed** |
| oracle negative controls | `unscoped_detector` | **2 passed** |
| P19 accreditation (full file) | `tests/test_p19_accreditation.py` | **23 passed** |

## 3. Adversarial synthetic-tenant probe (before/after)

Disposable SQLite DB, synthetic tenants only (`scratchpad/day2_probe.py`). After the fixes:

| Probe | Finding | Result |
|---|---|---|
| A viewer `GET /analytics/vendors` | AW-08b | **SECURE** — B vendor absent, A present |
| A admin `GET /accreditation/programs` | AW-08a | **SECURE** — B absent, A present |
| A admin `?tenant_id=B` | AW-04 | **SECURE** — HTTP 403, B absent |
| A `GET /guardianx/audit-replay/inspections/{B-id}` | AW-08c | **SECURE** — 403 at route |
| hospital user asserts `X-Manufacturer-ID` | AW-07 | **VULNERABLE** (expected — BLOCKED, no code change) |

## 4. Open-finding tripwires (RED by design — five of them)

The code is remediated, so five "fail-on-fix" guards now fire. Their artifacts are deliberately left
intact (closure is an independent-review action, not an AI action). CI is expected RED on exactly
these five until a human reviewer closes the findings:

- `test_p472_03_application_wide_findings.py::test_aw04_a_member_of_a_cannot_list_tenant_b_accreditation_programs` — XPASS(strict), AW-04
- `test_p472_03_application_wide_findings.py::test_aw08_listing_accreditation_programs_does_not_return_other_tenants` — XPASS(strict), AW-08a
- `test_p472_03_application_wide_findings.py::test_aw08_vendor_scorecard_does_not_aggregate_another_tenants_inspections` — XPASS(strict), AW-08b
- `test_guardianx_assurance.py::test_aw08_guardianx_replay_does_not_serve_another_tenants_inspection` — XPASS(strict), AW-08c
- `test_p472_03_application_wide_isolation.py::test_registered_findings_still_reproduce` — the sweep register still lists `GET /api/accreditation/programs: [AW-04]`, which the fix stopped reproducing. Removing the register entry = closing the finding (reserved for review); left intact.

## 5. PostgreSQL 16 migration review (disposable DB, dropped after)

- `alembic upgrade head` on a throwaway PG16 DB → GD-3 `tenant_id` columns present (nullable, no default).
- NULL-quarantine: tenant-A-scoped read returns only A; legacy NULL row matched by **0** tenant filters; B invisible.
- `alembic downgrade -1` → columns fully removed (reversible). DB dropped.

## 6. Full backend suite (SQLite)

Command: `cd backend && rm -f test.db && python -m pytest tests/ -q` (fresh DB).

> **Result (local full run on `51c2133`, reached 100%): 5 failed, 8526 passed, 3 skipped,
> 11 xfailed.** The **CI** job "Backend tests (SQLite)" on `51c2133`
> (run 44464032690) reports the identical tally: **5 failed, 8526 passed, 3 skipped, 11 xfailed**
> in 11m39s. **All five failures are the remediation tripwires in §4** — there is **no other new
> failure and no genuine regression.** (The opt-in
> `tenant_isolation_sweep_runner.py::test_run_sweep` requires `P472_SWEEP_OUT` and is not part of the
> normal suite; do not count it.)

## Notes
1. `backend/test.db` is a persistent SQLite file; repeated runs accumulate rows (e.g. duplicate
   `source_id='500'` ledger entries), which can produce spurious count-mismatch failures such as
   `test_replay_recommendation_composes_evidence_and_explanations`. Resetting the DB clears these;
   they are an environment artifact, not a code regression.
