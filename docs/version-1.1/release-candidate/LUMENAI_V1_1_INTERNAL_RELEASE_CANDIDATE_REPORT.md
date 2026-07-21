# LumenAI — Version 1.1 Internal Release Candidate Report (LPR-DIR-026)

**Release Candidate:** `main @ 5c223450b4065011a52ff2dd244c6c5d91321dcc` (`5c22345`)
**`git describe`:** `lumenai-v1.0.0-rc1-19-g5c22345` · **Certified from merged evidence only.**
**Honesty rule enforced:** feature-branch CI closes nothing; only a merge into `main` counts.

---

## 1. Executive Summary

The Version 1.1 Internal Release Candidate is composed **exclusively of code merged into
the authorized baseline `main`**, at tip `5c22345`. The program's single CRITICAL release
blocker — **SEC-C-01** (webhooks fail-open + attacker-controllable tenant → cross-tenant
injection) — is now **CLOSED on the baseline**: its fix (PR #119) is merged, code-verified
fail-closed with server-side tenant binding, and regression-clean. All other merged V1.1
PRs (#108–#118) are documentation/assessment and contribute **no application code**. Two
governance PRs (#120, #121) remain OPEN/draft and are **excluded** (unmerged, docs-only);
no unmerged *implementation* work exists. On merged evidence the RC qualifies as an
**Internal Release Candidate** — the CRITICAL gate is cleared — but **8 HIGH blockers
remain OPEN** (mostly infrastructure/real-world), so it is **not** a Pilot or Production
Candidate.

## 2. Merge Verification

Every V1.1 PR was verified by `git` + GitHub metadata (MERGE_VERIFICATION.md). #108–#118:
**MERGED, docs-only** (empty `backend/app`+`frontend/src` diff). **#119: MERGED**, merge
SHA `5c22345`, merged 2026-07-19T22:28:14Z by johnnychris77 — the **only** app-code change
(`integrations.py`, `billing.py`, `billing_webhooks.py`; head `f291186` ∈ RC). #120/#121:
**OPEN/draft, excluded**. No rejected or blocked implementation PRs.

## 3. Release Candidate Manifest

RC = `main @ 5c22345` (RELEASE_CANDIDATE_MANIFEST.md). Only V1.1 code delta = SEC-C-01 fix.
**Schema head `e7b2f4a86c31`** (13-file linear chain; no V1.1 migration). Dependencies
unchanged (`requirements-lock.txt`, sha256 `d96ae3a7…`). **No valid V1.1 tag** — `v1.1.0`
(`5a747af`) is stale/divergent (not an ancestor of the RC). New config surface: webhook
secret + server-tenant env contract.

## 4. Security Verification

Re-evaluated on the merged baseline (BASELINE_SECURITY_VERIFICATION.md). **CRITICAL: 0
open** — SEC-C-01 **CLOSED (code)**, verified on `main` (503 no-secret / 401 bad-sig / 400
bad-Stripe-sig / 503 no-tenant; `X-Tenant-Id` header no longer trusted). **HIGH: 8 open**
(SEC-H-01/02 partially mitigated at startup; PERF-07, SCAL-01, RES-01, OPS-INC-01,
OPS-DEP-01/02 infra/process). MEDIUM/LOW open, non-blocking.

## 5. Regression Certification

Against the RC tree (RELEASE_CANDIDATE_REGRESSION.md): changed-code-path + governance slice
**87 passed / 0 failed**; **ruff clean**. Full suite **~3,715 tests collected**, CI-gated
PASS on both SQLite + PostgreSQL 16 on each merge (baseline CI on merged code, not
feature-branch CI). Type checking N/A as a gate (pre-existing gap). No test skipped or
failure suppressed.

## 6. Configuration Certification

RELEASE_CONFIGURATION_CERTIFICATION.md: env/secrets/OIDC/tenant/flags/migrations certified
consistent, with two carried conditions — (a) the new fail-closed webhook env vars **must
be provisioned per environment**; (b) production-deploy config remains OPEN (deploy stub
OPS-DEP-01, no rollback drill OPS-DEP-02, single worker SCAL-01). Rollback is
**schema-compatible by construction** (no V1.1 migration).

## 7. Integrity Verification

RELEASE_INTEGRITY_REPORT.md: real sha256 for source delta + dependency manifests; pinned
version/build metadata. **Container digests NOT AVAILABLE** (no image built/pushed — a `v*`
tag would trigger GHCR publish, deliberately not done). **Fresh tool-generated SBOM not
produced in this pass**; dependency fingerprint pinned via `requirements-lock.txt`. Nothing
fabricated.

## 8. Candidate Assessment

PILOT_CANDIDATE_ASSESSMENT.md: **Development Build ✅**, **Internal Release Candidate ✅**
(no open CRITICAL on the baseline), **Pilot Candidate ❌** (8 HIGH open; entry gate not
approved; LPR-DIR-023 EXECUTION BLOCKED), **Production Candidate ❌**.

## 9. Executive Recommendation

Freeze `main @ 5c22345` as the **Version 1.1 Internal Release Candidate**. The CRITICAL
gate is cleared on merged evidence. **Do not** advance to Pilot/Production on this RC and
**do not** cut a `v1.1.*` tag until the HIGH production blockers are closed on a managed
environment. Next milestone: address SEC-H-01/02 fully in code; execute PERF-07/SCAL-01/
RES-01/OPS-* on real infrastructure; then re-verify and tag. No production authorization;
no clinical or regulatory claims.

## 10. Residual Risks

1. Fail-closed webhooks reject traffic until secrets/tenant env vars are provisioned (by
   design). 2. Stale `v1.1.0` tag must not be mistaken for a release marker. 3. Eight HIGH
   infra/real-world blockers remain OPEN and are not closable from the repository. 4.
   Merged documentation is assessment, not delivered hardening — only SEC-C-01 is delivered
   code. 5. No container image / fresh SBOM exists yet for the RC (produced only at an
   authorized tagged build).

---

### Operational Decision

> ## 🟠 INTERNAL RELEASE CANDIDATE CERTIFIED — BLOCKERS REMAIN
> The RC (`main @ 5c22345`) is composed **only** of merged code. **SEC-C-01 (the sole
> CRITICAL) is CLOSED on the baseline** — cleared on merged evidence, not feature-branch
> CI — and regression is green. It is certified as the Version 1.1 **Internal Release
> Candidate**. **8 HIGH blockers remain OPEN** (mostly infrastructure/real-world), so it is
> **not** a Pilot or Production Candidate, and **no `v1.1.*` release tag is cut**. No
> production authorization; no clinical or regulatory claims.

### Deliverables index
| # | File |
|---|---|
| 1 | `MERGE_VERIFICATION.md` |
| 2 | `RELEASE_CANDIDATE_MANIFEST.md` |
| 3 | `BASELINE_SECURITY_VERIFICATION.md` |
| 4 | `RELEASE_CANDIDATE_REGRESSION.md` |
| 5 | `RELEASE_CONFIGURATION_CERTIFICATION.md` |
| 6 | `RELEASE_INTEGRITY_REPORT.md` |
| 7 | `PILOT_CANDIDATE_ASSESSMENT.md` |
| 8 | `EXECUTIVE_RELEASE_CERTIFICATION.md` |
| 9 | `LUMENAI_V1_1_INTERNAL_RELEASE_CANDIDATE_REPORT.md` (this file) |
