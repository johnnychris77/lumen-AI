# LPR-DIR-025 — Blocker Closure Report (Workstream 3)

**Honesty rule applied:** a blocker is closed **only** when its fix is merged into the
release baseline (`main`) and verifiable there. CI-green on a feature branch does **not**
close a blocker.

## Critical

| ID | Status on baseline | Merged evidence | Verification evidence | Remaining work |
|---|---|---|---|---|
| **SEC-C-01** (webhook fail-open + tenant injection) | **OPEN** | ❌ Fix is in PR **#119**, **not merged** (`f291186` not an ancestor of `main`) | Code proof: `main:backend/app/routes/integrations.py:827` still reads `X-Tenant-Id` for tenant; `billing.py::stripe_webhook` on main still parses raw payload when secret unset | **Merge PR #119** into `main`; then re-verify on the baseline |

## High (8) — all OPEN on baseline

| ID | Status | Merged evidence | Remaining work |
|---|---|---|---|
| SEC-H-01 (hardcoded secret fallbacks) | **OPEN** | none merged | Remove dev fallbacks (partial startup guard exists on main) |
| SEC-H-02 (no fail-closed startup secret validation) | **OPEN** | none merged | Fold all secrets into an invoked `Settings.validate()` |
| PERF-07 (no production load test) | **OPEN** | none merged | Run on a managed environment (infra) |
| SCAL-01 (single Postgres/worker) | **OPEN** | none merged | HA Postgres + multi-worker (infra) |
| RES-01 (in-process scheduler duplication) | **OPEN** | none merged | Leader election (infra) |
| OPS-INC-01 (no alerting / incident response) | **OPEN** | none merged | Alert rules + on-call (infra/process) |
| OPS-DEP-01 (deploy stub) | **OPEN** | none merged | Real rollout automation (infra) |
| OPS-DEP-02 (no rollback drill) | **OPEN** | none merged | Executed rollback drill (infra) |

## Operational / Security / Performance / Infrastructure (selected MAJOR/MEDIUM)
AR-16/17/18, SR-01/02, DH-01, CFG-01, DB-05, SEC-INF-01, ENV-01, OPS-OBS-01/02 — **all
OPEN on baseline** (no remediation PR merged).

## Summary
- **Blockers closed on the baseline: 0.**
- **SEC-C-01 CRITICAL: OPEN** (fix unmerged; code on `main` still vulnerable).
- **8 HIGH: OPEN.** The one code fix (#119) that would close SEC-C-01 is **not in the
  baseline**, so — per the honesty requirement — it is reported as **not closed**.
