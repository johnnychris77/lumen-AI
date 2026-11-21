# P472-03 — Release-gate evidence index (v1)

| | |
|---|---|
| Reviewed commit | **`1ff863d394d8a26a9cd8ad56d36dcf390bcd3c85`** (PR #181 head) |
| Branch | `engineering/render-local-inference-p47` |
| PR state | **draft · open · not merged** (verified) |
| Release disposition | **HOLD / NO-GO** |
| P472-03 status | **OPEN** |
| Prepared by | The remediation author (this is **not** an independent review) |

**Classification legend:** PASS (verified technical requirement satisfied) ·
PENDING (evidence or decision not yet available) · BLOCKED (dependency or
approval missing) · FAIL (verified requirement not satisfied) · NOT ASSESSED
(review has not occurred). **A passing automated test is never independent
reviewer approval.**

## 1. CI evidence for the reviewed head

Run `44431365412` ("Pilot Zero Gate"), event `pull_request`, head_sha `1ff863d`,
all 13 jobs **completed**.

| Check | Status | Evidence class |
|---|---|---|
| Ruff (backend) | success | PASS |
| Secret scan / secrets-scan | success | PASS |
| backend-security-and-lint | success | PASS |
| backend-core-ci | success | PASS |
| backend-compliance-tests | success | PASS |
| Run LumenAI security hardening tests | success | PASS |
| enterprise-quality-gate | success | PASS |
| Dependency audit (report-only) | success | PASS |
| Frontend build / frontend-security-and-build | success | PASS |
| **Backend tests (SQLite)** | **success** | **PASS** |
| **Backend tests (PostgreSQL 16)** | **success** | **PASS** |

**Backend tests (SQLite)** — job `135249265383`, conclusion **success**:
`8505 passed, 3 skipped, 15 xfailed` (0 failed, 0 unexpected-pass) in 17m34s.

**Backend tests (PostgreSQL 16)** — job `135249265861`, conclusion **success**.
The job's "Alembic chain applies to PostgreSQL" step passed (migration chain
including GD-3 `d8f3a6b914c7` applies on PG16), and the "Run full suite on
PostgreSQL" step completed **success** → **0 failed, 0 unexpected-pass**. The
exact passed/skipped/xfailed integer line is not reproduced here because the
step's stdout is overwritten in the retrievable log tail by the PostgreSQL
container teardown log-dump; the **`success` conclusion is authoritative** that
the full suite passed (pytest exits non-zero on any failure or unexpected pass,
which would fail the step and the job). The SQLite job on the **identical tree**
gives the companion exact figures above; by the established Batch-1/Batch-2
pattern PG16 differs only by the PostgreSQL-only Alembic test (one more passed,
one fewer skipped) — stated as the known pattern, not substituted for the PG16
count.

**Reviewed commit note:** `1ff863d` is the task's reference commit; the current PR
head `33f1ed5` adds only this assurance package (7 docs) on top of it, so backend
test behaviour is identical. Its run was still executing at the time of writing.

## 2. Per-area evidence

| Area | Evidence | Class |
|---|---|---|
| Batch 2 fixes implemented (AW-01, AW-02, AW-05, AW-12, AW-13, GD-1, GD-2) | commits `cf0eda2`…`63bc840`; author tests pass | PASS (implemented) / **NOT ASSESSED** (independent review) |
| Batch 2 independent security review | — | **NOT ASSESSED** (AWAITING NON-AUTHOR REVIEW) |
| GD-3 tenant-private floor implemented | `78426ce`, `38d1222`; 5 tenant-private tests + 38 adversarial baseline-route tests pass | PASS (implemented) / **NOT ASSESSED** (independent review) |
| GD-3 migration preserves + quarantines legacy rows | PG16 validation, up/down reversible | PASS (representative) / **PENDING** (production migration readiness) |
| GD-3 ownership/sharing model | `c9a0f73` design only | **BLOCKED** (governance approval) |
| Manufacturer-managed category | depends on AW-07 | **BLOCKED** (AW-07 open) |
| Clinical-workflow impact of quarantine | `gd3-quarantine-impact-and-attribution-proposal.md` §2 | PASS (documented) / **PENDING** (owner approval) |
| Legacy attribution | procedure proposed; none performed | **BLOCKED** (owner approval); no production attribution |
| GD-1, GD-2, GD-3, GD-4 policy sign-off | none collected | **PENDING** / **NOT ASSESSED** |
| AW-07 manufacturer identity | strict xfail confirms finding | **FAIL** (open finding; unverified header) |
| Full application-wide tenant isolation | not claimed | **NOT ASSESSED** / open findings remain |

## 3. Strict expected-failures on the reviewed tree (15) — all are open findings

Enumerated by `pytest -rx`. None was converted to a pass; each pins an open
finding. See `p472-03-residual-risk-register-v1.md` for the full list and the
AW-08-artifact distinction.

| Finding | Count | Class |
|---|---|---|
| AW-03 (header re-read) | 2 | OPEN |
| AW-04 (query/path/body tenant) | 5 | OPEN |
| AW-06M (members pooled in default-tenant) | 2 | OPEN |
| AW-06N (no-membership pooled) | 2 | OPEN |
| AW-07 (manufacturer identity by header) | 1 | OPEN — GD-3 category-B blocker |
| AW-08 (tenant table read, no predicate — genuine) | 3 | OPEN |

## 4. Overall gate

**HOLD / NO-GO.** The full SQLite and PostgreSQL 16 CI suites on `1ff863d` now
pass (SQLite `8505 passed / 3 skipped / 15 xfailed / 0 failed`; PG16 conclusion
`success`), but passing CI is **not** release readiness: **no independent
non-author review has occurred**, **no governance policy is signed off**, and
**AW-07 and the other application-wide findings remain open**. Nothing here
authorizes merge, deploy, attribution, or finding closure.
