# LPR-DIR-025 — Merged Baseline Regression (Workstream 4)

**Results must be from the merged baseline (`main` @ `3c30d8a`).** The verification tree
used here has **backend code identical to `main`** (`git diff --stat origin/main --
backend/` = empty; only added docs differ), so the run below exercises the baseline code.

## Evidence

| Check | Result | Source |
|---|---|---|
| Merged-baseline regression slice (`test_p17_recommendations.py` + `test_directive_002_endpoint_governance.py`) | **45 passed, 0 failed** (40 s, clean DB) | run on this tree (backend == main) |
| Full backend suite — unit + integration (SQLite + PostgreSQL 16) | **PASS on every merge** | required CI gate on `main`; each PR in the merge history passed both jobs before merging |
| Security tests | **PASS on baseline** | `Run LumenAI security hardening tests` + `backend-security-and-lint` required checks |
| Lint (ruff) | **PASS on baseline** | `Ruff (backend)` required check |
| Type checking | **N/A as a gate** | no dedicated mypy/pyright CI job in the workflow set (not a regression — a pre-existing coverage gap) |

## Honest caveat (critical)
The baseline **passes its own test suite**, but on `main` `test_p17_recommendations.py::
TestWebhook` still asserts the **old fail-open behavior** (`200` with no signature and an
`X-Tenant-Id` header). So "green regression on the baseline" **coexists with SEC-C-01
being open** — the baseline's tests encode the vulnerability. The corrected tests (which
assert fail-closed 503/401 and prove server-side tenant binding) live in PR **#119** and
are **not on the baseline**. A green baseline regression here is therefore **not**
evidence that SEC-C-01 is closed.

## Determination
The merged baseline is **regression-green against its current suite** (45/45 slice; full
suite CI-gated on every merge; ruff/security green). This confirms `main` is not broken —
it does **not** confirm any blocker closure, and specifically does not close SEC-C-01.
