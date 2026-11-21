# Milestone 9 — Enterprise Release-Readiness Assessment (v1)

**Issue #191 (M9.4) · PR #181 (DRAFT) · reviewed baseline `bed42c86f982efc845130ec65d3b46bdc2d06899`
(application code `829f36a`; `git diff 829f36a bed42c8 -- backend/app backend/alembic` is empty).**
Supersedes release-gate assessment v8 for Milestone 9 (v8 preserved).

**Recommendation to the release authority: NO-GO / HOLD.** This is the change author's recommendation, not a
release decision. **Independent assurance is NOT complete.** No independent reviewer, approver or release
authority has acted.

## 0. What Milestone 9 did — and did not — achieve

| Category | Status | Count |
|---|---|---|
| **Preparation (author)** | **complete** | handbook, 40-tripwire ledger, PA-1 architecture packet, governance approval matrix, HIST authorization package, this assessment, evidence freeze, rehearsals |
| **Independent verification** | **NOT STARTED** | 0 reviewers appointed · 0 runs by a non-author · 0 dispositions (40 PENDING) |
| **Signed governance** | **NONE** | 0 of 12 approval-matrix rows signed (GD-5…9, AUTH-1/2, PA-1, CLIN-1, HIST, operations attestation, release) |
| **Release decision** | **NONE** | — |

**Reason independent verification did not start:** the repository has a single collaborator (the owner), and
all commits in scope were produced for that owner by an AI coding agent. Neither is independent. The release
authority must appoint a reviewer and approvers (governance matrix row 0).

## 1. Evidence freeze (Phase 1)

| Item | Value |
|---|---|
| Frozen SHA / tree | `bed42c8…` / recorded in `evidence/m9/freeze-bed42c8.json` |
| Files frozen | 230 (hashed from the git object at `bed42c8`, not the working tree) |
| Scope | evidence manifest + records, all evidence directories (Batch 7, Batch 8, PA-1), every P472-03 / GD / clinical document incl. all preserved versions of risk registers (v1–v8), ledgers (v1–v3), tripwire registers (v1–v6), review packets (Batch 7 guide + generated, Batch 8 generated, PA-1), assertion change log, review kit and reproduction scripts, tripwire test files, findings register, Alembic versions, `render.yaml`, CI workflow; digest of all of `backend/app` |
| CI records in the freeze | every CI record from `records.json` plus `bed42c8` runs (below) |
| Verification | `python backend/scripts/m9_evidence_freeze.py verify docs/enterprise-readiness/evidence/m9/freeze-bed42c8.json` → **0 integrity failures** (author run) |

## 2. Exact-SHA reconciliation (Phase 5)

### 2.1 CI on `bed42c8` (the frozen baseline)

| Workflow / job | Result |
|---|---|
| Pilot Zero Gate run `44840371217` — Backend tests (SQLite), job `136646947604` | **9317 passed, 3 skipped, 0 xfailed, 0 failed** |
| — Backend tests (PostgreSQL 16, Alembic chain step), job `136646947540` | **9318 passed, 2 skipped, 0 xfailed, 0 failed**; Alembic step success |
| — Secret scan, Ruff, Frontend build, Dependency audit (report-only) | success |
| Core CI `44840371257`, Backend Compliance `44840371224`, Security Baseline `44840371271`, Security Hardening `44840371359`, Enterprise Quality Gate `44840371212` | success |

These match CI on `829f36a` (run `44834645331`) exactly. The Milestone 9 commit (documents, evidence, three
new scripts; no application code) triggers its own CI; the reviewer should cite that run as well.

### 2.2 Local author evidence

| Check | SHA | SQLite | PostgreSQL 16.15 |
|---|---|---|---|
| Full backend suite | `829f36a` (= `bed42c8` app code) | 9317 / 3 / 0 / 0 | Alembic up/down/up exit 0; 9318 / 2 / 0 / 0 |
| Alembic | `bed42c8` | single head `b5a2c7e19d40` | up/down/up exit 0 (CI-faithful) |
| Route sweep (1,913 routes) | `829f36a` | 0 findings; 0 foreign-write routes | 0 / 0 |
| Register-driven isolation | `829f36a` | 17/17 | — |
| Browser E2E (Chromium, real login) | `829f36a` | 6/6 twice | — |
| Frontend | `829f36a` | `npm test` 48/48; build ok | — |
| Review kit, GuardianX P1/P2 (RB-T24…T37) — **M9 rehearsal** | `bed42c8` | **48/48 variants matched** | **48/48 matched** |
| Review kit, PA-1 (RB-T38…T40) | `829f36a` | 12/12 | 12/12 |
| Review kit, RB-T01…T23 | Batch 7/8 (after `6a661bb`) | 136/136 merged (all tripwires then) | 136/136 |
| A-1 mutation check (6 mutations) — **M9** | `bed42c8` | **6/6 as expected** (after correcting one author expectation, disclosed) | **6/6** |
| PA-1 reproduction | before `8bfcc9a`/`c2014ff`, after `829f36a` | reproduced / closed | reproduced / closed |

Gaps in reconciliation, stated plainly:
- RB-T01…T23 were last run through the kit at Batch 7/8 SHAs, not at `bed42c8`. The application code for
  those findings has not changed since, and the full suites at `bed42c8` pass, but **a kit run at `bed42c8` for
  those 23 tripwires exists only for the reviewer to make**.
- Browser E2E and the sweeps ran at `829f36a`, not `bed42c8`; the application code is identical.
- All local evidence is LOCAL-AUTHOR.

## 3. Gate matrix

| Gate | Status | Evidence class | What closes it |
|---|---|---|---|
| G1 tenant isolation (resolvers) | author-remediated; **PENDING** review | CI + LOCAL | non-author review |
| G2 sweep / register | 0 findings both DBs; **blind spots open** (164 role-gated, ~729–735 partly exercised, 353 leads) | LOCAL | independent probing (handbook §6) |
| G3 AW-07 manufacturer identity | partly remediated; **OPEN** | — | GD-9 |
| G4 replay / object scope | author-remediated; **PENDING** | LOCAL | review |
| G5 GD-3 | **PENDING** | — | review + decision |
| G6 PA-1 | environment gates author-remediated; **governance OPEN**; new findings PA1-08…PA1-11 (admin minting, non-durable revocation, log-only admin access, admin-grants-admin) | CI + LOCAL | PA-1 decision + review |
| G7 GD-5…GD-9, AUTH-1/2, CLIN-1 | **PENDING — none signed** | — | approval matrix |
| G7a GuardianX write authorization | fail-closed floor, not complete (ownerless keys first-writer) | LOCAL + CI | GD-7 |
| G7b GuardianX explanations | author-remediated; review pending | LOCAL + CI | review RB-T32, T34…T37 |
| G8 clinical workflow | **PENDING** | — | clinical owner (CLIN-1) |
| G9 frontend contract | E2E 6/6 ×2; owner review pending | LOCAL | frontend/API owner |
| G10 CI security/lint/quality | **PASS** on `bed42c8` | CI | — |
| G11 CI backend suites | **green, 0 xfail** on `bed42c8` | CI | not a release pass while tripwires are undispositioned |
| G12 historical access | **BLOCKED — NOT REQUESTED** | — | HIST authorization package |
| G13 independent review | **NOT STARTED — 0 reviewers; no eligible reviewer in repository** | — | release authority appoints |
| G14 tripwires | **40 release blockers: 40 author-converted, 0 failing, 0 dispositioned** | CI + LOCAL | M9 ledger rows by non-authors |
| G15 release decision | **PENDING** | — | release authority |
| G16 deployment contract | `render.yaml` closed; **deployed variables not attested** | — | operations attestation (governance matrix §4) |

## 4. Residual risk (top items; full list `p472-03-residual-risk-register-v9.md`)

| Risk | Residual | Note |
|---|---|---|
| R-NO-INDEPENDENT-REVIEWER | blocking | nothing can be dispositioned or signed |
| R-ADMIN-BOOTSTRAP-TOKEN (PA1-08) | **High if set in production** | deployed value unknown |
| R-ADMIN-LOG-ONLY / R-PA1 (PA1-10) | High | standing global-admin cross-tenant access |
| R-SWEEP-BLINDSPOTS | High | oracle cannot see role-gated, partly exercised, response leakage, IDOR |
| R-HIST | unknown | exposure windows still open on any environment running `main` |
| R-PA1-CONTRACT | Medium (availability) | deployments relying on removed exception will not start |
| R-PA1-NONPROD | Medium | public literals and header-trusting dev auth outside production |
| R-GX-OWNERLESS-KEYS / WRITE-RACE | Low–Medium | GD-7 |
| R-PORTFOLIO-LATENT, R-BOOTSTRAP-REENABLE, R-ADMIN-GRANTS-ADMIN | Medium | PA-1 / GD-8 |

## 5. Deployment-readiness checklist (all unchecked)

- [ ] Independent reviewer(s) appointed; independence statements recorded
- [ ] 40 ledger rows dispositioned by non-authors (or explicitly ACCEPT-RISK with owner + expiry)
- [ ] A-1 judged by a non-author
- [ ] PA-1 decision signed (owner + second approver); RB-T38…T40 accepted with it
- [ ] GD-5…GD-9, AUTH-1, AUTH-2, CLIN-1 signed
- [ ] AUTH-2 inventory of `users.role` and admin assignments completed by an authorized operator
- [ ] Operations attestation of deployed variables (governance matrix §4), web and worker
- [ ] HIST authorized; evidence preserved; suspected-exposure record opened
- [ ] CI green on the exact SHA to be released, reviewed by a non-author
- [ ] Release authority decision recorded

## 6. Unresolved blockers to GO

1. No independent reviewer exists or has been appointed.
2. 40 undispositioned release blockers.
3. 0 signed governance decisions, including PA-1 and the deployment-gating AUTH-2.
4. Standing privileged-access risks (PA1-08, PA1-10) with unknown production configuration.
5. Historical access not investigated; windows open.
6. Deployed configuration not attested against the new startup refusal list.

## 7. Recommendation

**NO-GO / HOLD.** PR #181 stays **DRAFT**. P472-03, PA-1 and all governance items stay **OPEN**. No merge, no
deploy, no production access. The release authority alone decides release.
