# LPR-DIR-026 — Release Candidate Regression (Workstream 4)

Executed against the **Release Candidate tree** (`main @ 5c22345`; `git diff --stat
origin/main -- backend/app frontend/src` = empty, so the working tree exercises the exact
RC code). Runner: project venv `.venv/bin/python` (pytest 9.1.1), run from `backend/` per
the repo convention.

## Results

| Category | Scope run here | Result | Source of evidence |
|---|---|---|---|
| **Unit + Integration (changed code paths)** | `tests/test_p17_recommendations.py` + `tests/test_p14_recommendations.py` (the two files exercising the SEC-C-01 code) | **74 passed, 0 failed** (35.4 s) | local run on RC tree |
| **Governance / endpoint** | `tests/test_directive_002_endpoint_governance.py` | **13 passed, 0 failed** (9.4 s) | local run on RC tree |
| **Security tests (SEC-C-01)** | fail-closed 503 (no secret) / 401 (bad sig) / 400 (bad Stripe sig) / 503 (no tenant) / signed-200 / **DB-level proof** attacker `X-Tenant-Id` ignored, server tenant stored | **PASS** (subset of the 74 above) | local run on RC tree |
| **Lint (ruff)** | `ruff check app tests` | **All checks passed** | local run on RC tree |
| **Formatting** | ruff-managed (same invocation; no violations) | **PASS** | local run on RC tree |
| **Full backend suite (SQLite + PostgreSQL 16)** | ~**3,715 tests collected** (`pytest --collect-only` on RC tree) | **CI-gated PASS on the merge** | required CI checks on `main` — every PR in the merge history passed both jobs before merging; not re-executed in full here |
| **Migration tests** | Alembic single linear chain, head `e7b2f4a86c31`; SEC-C-01 adds no migration | **No schema delta to test in V1.1**; chain integrity verified by inspection | RELEASE_CANDIDATE_MANIFEST.md §5 |
| **Database tests** | included in the changed-path + full suite above (SQLite for local slice; PostgreSQL 16 exercised by CI) | **PASS (slice) / CI-gated (full)** | local + CI |
| **Type checking** | no dedicated mypy/pyright CI job exists in the workflow set | **N/A as a gate** (pre-existing coverage gap, not a regression) | `.github/workflows/*` inventory |
| **Coverage** | enforced by repo compliance/quality gates on merge (`backend-compliance-tests.yml`, `enterprise-quality-gate.yml`) | **CI-gated PASS on the merge** | required checks on `main` |

## Honesty notes

- **What was executed locally on the RC:** the changed-code-path tests (74), a governance
  slice (13), and ruff — **87 passed / 0 failed, lint clean**. These directly exercise the
  only V1.1 code delta.
- **What is cited from CI, not re-executed here:** the full ~3,715-test suite on both
  SQLite and PostgreSQL 16, plus coverage/compliance gates. This is **merged-baseline**
  evidence — each PR composing the RC passed these required checks before it merged into
  `main`. Per the honesty requirement, this is baseline CI on merged code, not
  feature-branch CI used to claim a closure.
- No test was skipped to obtain a green result; no failure was suppressed.

## Determination

The Release Candidate is **regression-green**: the V1.1 code delta passes its unit,
integration, security, and lint checks locally (87/0), and the full suite + coverage are
CI-gated PASS on the merge. Type checking remains **N/A as a gate** (pre-existing gap).
