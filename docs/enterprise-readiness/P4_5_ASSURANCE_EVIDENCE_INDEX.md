# P4.5 — Assurance Evidence Index & Chain of Custody

**Prepared:** 2026-11-17 · **Mode:** read-and-verify documentation. **No code changed, no
merge, no deployment.** This index is an evidence map for a qualified **independent non-author**
reviewer. It does **not** approve anything.

## 0. Evidence-class legend (kept strictly separated)
- **[VF] Verified fact** — directly confirmed this session against primary sources (git, CI API, file contents).
- **[AT] Automated test result** — produced by CI or local pytest; necessary, not sufficient; not an approval.
- **[DA] Developer assertion** — a claim by the implementing (AI) workflow, to be independently re-verified.
- **[HD] Human decision required** — not yet made; left blank for the authorized reviewer.

## 1. Baseline, SHAs & chain of custody  [VF unless noted]

| Ref | Value |
|---|---|
| `origin/main` | `0f2ec588d24b7c64ccacd84adf67e89cb1ec1676` (unchanged; nothing from the stack merged) |
| PR #176 head (P4.1 security) | `fdaee8e2135fea7d2a5581fbe7246014fe2b9219` |
| PR #177 head (P4.3 research) | `b35e5527a1de8d16b0bfb10742105a3068e6312f` |
| PR #178 head (P4.4 combined-integration validation) | `8574a2aa4cea03899e4146735ace61e2d51c92e8` |
| Reported combined **code** commit | `7c0f679` (= `c111d93` + merge #176 + merge #177; docs commits sit atop) |
| Common parent / integration base (#174 head) | `c111d93e11feea2ee6a2c6ab17277218c78ba3da` |
| **Chain of custody** | `7c0f679`, `fdaee8e` (#176), `b35e552` (#177) are all **ancestors of** `8574a2a` (#178) — the combined branch provably contains both remediations. |
| PR states | #176, #177, #178 all **open, draft, unmerged** (verified). |

## 2. CI / job-level results  [AT]

PR #178 head `8574a2a` — **all 7 checks green** (GitHub Actions runs 44163452411 / 44163452263):
Ruff (backend) ✅ · Secret scan ✅ · Backend tests (SQLite) ✅ · **Backend tests (PostgreSQL 16) ✅** (completed 20:11:39Z) · Frontend build ✅ · Dependency audit (report-only) ✅ · enterprise-quality-gate ✅.
PR #176 (`fdaee8e`) and #177 (`b35e552`): all 7 checks green on their heads (verified earlier).
*Note:* no separate "Pilot Zero Gate" check run is observed on these heads; only the 7 jobs above executed — **not claiming a workflow that did not run.** [VF of what ran]

## 3. Evidence register

Columns: **ID · Path/reference · Commit · Control/finding · Verification method · Reviewer required · Limitations · Status/class**

| ID | Path / immutable ref | Commit | Control / finding | Verification method | Reviewer required | Limitations | Status |
|----|----------------------|--------|-------------------|---------------------|-------------------|-------------|--------|
| EV-01 | `docs/enterprise-readiness/P4_1_SECURITY_FINDINGS_REGISTER.md` | `fdaee8e` (#176) | SEC-176 A/B/C/#1/#3/#7 register | Read; cross-checked to code | Independent security | Author-produced register [DA] | Documented [VF-exists] |
| EV-02 | `docs/enterprise-readiness/P4_1_SECURITY_REMEDIATION_EVIDENCE.md` | `fdaee8e` | SEC-176 remediation + tests | Read; test re-run | Independent security | Author-produced [DA] | Documented |
| EV-03 | `backend/tests/test_sec176_critical_findings_remediation.py` | `fdaee8e` | SEC-176 regression (8 SQLite + 1 PG16) | Executed (CI + local) | Security | Failing-before-fix shown via stash [DA] | Passing [AT] |
| EV-04 | `docs/enterprise-readiness/P4_2_RESEARCH_STACK_SECURITY_TRIAGE.md` | `fdaee8e` | #164/#168 triage, integration matrix | Read; re-verified vs tip | Independent security | Author triage [DA] | Documented |
| EV-05 | `docs/enterprise-readiness/P4_3_RESEARCH_BENCHMARK_REMEDIATION.md` | `b35e552` (#177) | RGI-01..13 research remediation | Read; test re-run | Research + security | Author-produced [DA] | Documented |
| EV-06 | `backend/tests/test_p4_3_research_benchmark_remediation.py` | `b35e552` | RGI-01/02/03/04/05/06/07/08/09/11/13 | Executed (CI + local) | Research + security | Failing-before-fix = import error on baseline [DA] | Passing [AT] |
| EV-07 | `docs/enterprise-readiness/P4_4_COMBINED_INTEGRATION_REVIEW.md` | `8574a2a` (#178) | Combined integration, artifact compat | Read; combined CI green | Independent security | Author-produced [DA] | Documented |
| EV-08 | `docs/enterprise-readiness/P4_4_INSTITUTIONAL_GOVERNANCE_DECISIONS.md` | `8574a2a` | RGI-01/RGI-02 decision package | Read | Institutional authority | No approval created | OPEN [HD] |
| EV-09 | `docs/enterprise-readiness/P4_4_SCIENTIFIC_METRIC_METHODOLOGY.md` | `8574a2a` | RGI-10 methodology | Read | Scientific authority | Implementation preserved | OPEN [HD] |
| EV-10 | `docs/enterprise-readiness/SEC-174-02_DISPOSITION.md` | `c111d93` | SEC-174-02 latent egress | Read; criteria captured | Independent security | Decision field blank | OPEN [HD] |
| EV-11 | `docs/enterprise-readiness/INDEPENDENT_SECURITY_REVIEW_INSTRUCTIONS.md` + `P3_SECURITY_REVIEW_HANDOFF.md` | `c111d93` | SEC-175-01 closure procedure | Read | Non-author reviewer | Reviewer-decision section empty | OPEN [HD] |
| EV-12 | Combined full suite (SQLite) | `7c0f679` | Integrated regression | `pytest tests/ -q` | — | SQLite; PG16 gated | **4131 passed / 19 skipped** [AT] |
| EV-13 | Combined PG16 (CI, #178) | `8574a2a` | PG16 + concurrency (Finding D / SEC-174-01) | CI job | Security | Ran in CI, not locally | **green** [AT] |
| EV-14 | `backend/research/lens_vision/artifact_store.py` + `tests/test_p4_3_*` | `b35e552` | RGI-04 tenant-safe store | Code read + ad-hoc exerciser | Security | Legacy-ref break noted (see P4.5 legacy doc) | Implemented [VF] / legacy OPEN [HD] |
| EV-15 | Alembic chain | `8574a2a` | Migration integrity | `alembic heads`/`history` | Security | fresh-DB upgrade is PG-only (pre-existing DDL) | single head `f1a2b3c4d5e6`, 19-edge linear [VF] |

## 4. Separation of evidence types (summary)
- **Verified facts [VF]:** SHAs, ancestry, PR states, CI green status, migration single-head, document existence, artifact-store behaviour exercised this session.
- **Automated results [AT]:** EV-03, EV-06, EV-12, EV-13 (and the 7 CI jobs). Necessary, not sufficient — **not** approval.
- **Developer assertions [DA]:** all author-produced registers/evidence/triage docs; each must be independently re-verified.
- **Human decisions required [HD]:** RGI-01, RGI-02, RGI-10, SEC-174-02, SEC-175-01, legacy-artifact disposition, and the final release decision. **None made.**

## 5. Reviewer entry points
Start at `P4_5_RELEASE_READINESS_DECISION.md` → follow to the control checklist
(`P4_5_INDEPENDENT_SECURITY_REVIEW.md`), the governance packages
(`P4_5_INSTITUTIONAL_AUTHORIZATION_APPROVAL.md`, `P4_5_SCIENTIFIC_METHODOLOGY_APPROVAL.md`), the
risk register (`P4_5_ENTERPRISE_RISK_REGISTER.md`), and the disposition forms herein.
