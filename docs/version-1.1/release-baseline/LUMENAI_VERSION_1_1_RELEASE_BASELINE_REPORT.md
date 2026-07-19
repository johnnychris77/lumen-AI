# LumenAI — Version 1.1 Release Baseline Report (LPR-DIR-025)

**Governance basis:** the authorized release baseline `main` @ **`3c30d8a`**, verified by
direct `git` inspection. **Honesty rule enforced throughout: CI-green on a feature branch
closes no blocker — only a merge into `main` does.**

## 1. Executive Summary
The release baseline is **precisely verified**. Every Version-1.1-adjacent PR merged into
`main` is **documentation/assessment**; **no V1.1 code change is in the baseline.** The
one code fix that would close the CRITICAL — **SEC-C-01, PR #119** — is **CI-green but
NOT merged**, so on merged evidence **SEC-C-01 remains OPEN on the baseline** (verified by
code: `main` still reads the tenant from the `X-Tenant-Id` header in the fail-open
webhook). All 8 HIGH blockers remain OPEN. Version 1.1 therefore qualifies as a
**Development Build only**.

## 2. Release Baseline
`main` @ `3c30d8a` (merge of PR #117). Composed of merged docs PRs #108–#118. Merges are
CI-gated (SQLite + PG16 backend tests, ruff, security/secret scans, compliance gates).
**`v1.1.0` tag is stale/divergent** (points to old `5a747af`, not an ancestor of `main`);
no valid V1.1 release tag exists. (`RELEASE_BASELINE_VERIFICATION.md`)

## 3. Pull Request Status
Merged: #108–#118 (all docs). **Not merged:** **#119** (SEC-C-01 code fix, open/draft,
`f291186`, CI-green full suite) and #120 (pilot EXECUTION-BLOCKED docs, open).
(`VERSION_1_1_PR_STATUS.md`)

## 4. Blocker Closure
**Closed on baseline: 0.** SEC-C-01 **OPEN** (fix unmerged; `main` code still vulnerable).
8 HIGH **OPEN** (none merged). (`BLOCKER_CLOSURE_REPORT.md`)

## 5. Regression Verification
Merged-baseline slice **45 passed / 0 failed** (backend tree == `main`); full suite CI-
gated on every merge; ruff/security green. **Caveat:** the baseline's own webhook tests
still assert the *fail-open* behavior and pass — a green baseline does **not** imply
SEC-C-01 is closed. (`MERGED_BASELINE_REGRESSION.md`)

## 6. Configuration Audit
Migrations/flags unchanged by V1.1; startup guards partially mitigate secrets; **the
webhook-secret + tenant-binding config contract needed for SEC-C-01 is on PR #119, not
merged**; deploy stub / single-worker / replica drift all unchanged.
(`CONFIGURATION_AUDIT.md`)

## 7. Release Assessment
**DEVELOPMENT BUILD.** Not an Internal Release Candidate (open CRITICAL on baseline), not
a Pilot Candidate (LPR-DIR-023 = EXECUTION BLOCKED), not a Production Candidate.
(`VERSION_1_1_RELEASE_ASSESSMENT.md`)

## 8. Executive Recommendation
**Merge PR #119** (closes SEC-C-01 in code; regression-clean on SQLite + PG16), then re-run
this verification to confirm the CRITICAL is closed *on `main`* — that is the single gate
from Development Build to Internal Release Candidate. Then address the HIGH infra blockers
on a managed environment. **Do not cut a `v1.1.*` release tag** until SEC-C-01 is verified
closed on the baseline. No production authorization; no clinical claims.

## Operational Decision

> ## 🟠 RELEASE BASELINE VERIFIED — BLOCKERS REMAIN
> The baseline (`main` @ `3c30d8a`) is precisely verified from merged evidence. **By that
> evidence, 1 CRITICAL (SEC-C-01) + 8 HIGH remain OPEN on the baseline** — the SEC-C-01
> fix is CI-green on PR #119 but **not merged**, and `main`'s code is still vulnerable. No
> blocker is reported closed; a green feature-branch CI was **not** converted into a
> closure. The baseline is a **Development Build**, not a release candidate.

## Deliverables index
| # | File |
|---|---|
| 1 | `RELEASE_BASELINE_VERIFICATION.md` |
| 2 | `VERSION_1_1_PR_STATUS.md` |
| 3 | `BLOCKER_CLOSURE_REPORT.md` |
| 4 | `MERGED_BASELINE_REGRESSION.md` |
| 5 | `CONFIGURATION_AUDIT.md` |
| 6 | `VERSION_1_1_RELEASE_ASSESSMENT.md` |
| 7 | `EXECUTIVE_RELEASE_REVIEW.md` |
| 8 | `LUMENAI_VERSION_1_1_RELEASE_BASELINE_REPORT.md` (this file) |
