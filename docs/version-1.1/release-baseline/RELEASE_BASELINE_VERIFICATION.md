# LPR-DIR-025 — Release Baseline Verification (Workstream 1)

All facts below are from direct `git` inspection of the authorized release baseline.

| Item | Finding |
|---|---|
| **Release / main branch** | `main` is the authorized release baseline. **HEAD = `3c30d8a`** (merge of PR #117). |
| **Merge history (first-parent, recent)** | #117 (Phase 9) → #114 → #112 → #111 → #108 → #115 → #116 → #118 (Phase 10 pilot) → #113 → #110 → #109 … all **documentation/assessment** PRs. |
| **Release tags** | `v1.1.0` exists **but is stale/divergent** — it points to an old commit `5a747af` ("chore: add .gitignore …") and is **NOT an ancestor of `main`**. A `vX.Y.Z` placeholder tag also exists. **There is no valid V1.1 release tag on the current baseline.** The RC marker `lumenai-v1.0.0-rc1` is local-only (never pushed). |
| **Protected branch state** | Merges into `main` are gated by required CI (SQLite + PostgreSQL 16 backend tests, ruff, security/secret scans, compliance + quality gates) — every merge in the history above passed those checks. |
| **SEC-C-01 fix presence** | The SEC-C-01 fix commit `f291186` (PR #119) is **NOT reachable from `main`** (`git merge-base --is-ancestor f291186 origin/main` → false). |
| **Direct code proof (baseline still vulnerable)** | `git show origin/main:backend/app/routes/integrations.py` line **827** still reads `tenant_id = request.headers.get("X-Tenant-Id") …` — the **fail-open webhook + attacker-controllable tenant (SEC-C-01) is present on the baseline**. |

## Determination
The release baseline is **precisely verified**: `main` @ `3c30d8a`, composed entirely of
merged documentation/assessment PRs. **No V1.1 code hardening has landed** — the SEC-C-01
fix is not merged, and the baseline still contains the vulnerable webhook code. There is
no valid V1.1 release tag. The baseline is well-defined; it **carries open blockers**.
