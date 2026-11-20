# P472-03 — Enterprise Release-Gate Assessment and Evidence Index (v6 — Batch 7)

**PR #181 (DRAFT) · Issue #189 · P472-03 OPEN** · supersedes the v5 evidence index (preserved).

**Recommendation for the release authority: NO-GO / HOLD.** It is a recommendation, not a release decision.
Engineering does not authorize releases. No reviewer, signatory or release authority has acted on any item in
this document.

## 0. How to read this document — four separate kinds of evidence

| Class | Meaning | Count at Batch 7 |
|---|---|---|
| **CI** | GitHub Actions results on author-pushed commits | see §3 |
| **LOCAL-AUTHOR** | runs by the change author in the development container | see §3 |
| **INDEPENDENT** | reviews or runs by a non-author | **0 — none performed** |
| **GOVERNANCE** | signed decisions or release authorizations | **0 — none signed** |

Nothing below is an independent finding, an approval or a release authorization. "Remediated" means only that
an author fix exists and its reproduction now passes. It does not mean accepted or closed. The SHA-indexed
manifest is `evidence/p472-03-batch7/manifest.json`, built from `records.json` by
`backend/scripts/p472_03_evidence_manifest.py`.

## 1. Batch 7 commits (baseline `c6ba66c`)

| SHA | Content | Changes app code? |
|---|---|---|
| `bd7af7c` | CI: `-rfEsxX`, JUnit, artifacts on every run, failure summary, health-check database | no (CI only) |
| `2aa7680` | B7.0/B7.1 tripwire review kit, evidence-manifest generator, preserved Batch 6 evidence | no |
| `4667ab8` | B7.1/B7.3/B7.4 review packets, governance packets, clinical packet, registers | no |
| `6a661bb` | **GuardianX source-object writes fail closed** (GD7-05 write side; RB-T29…T33) — **final application code** | **yes** |
| `3fbbe65` | B7.2 anomaly report v1, risk register v6, RB-T29…T33 in registers and kit | no |
| `7cc7bfb` | Kit: RB-T04 before-SHA corrected (`fbd2581^`, not `30638f0^`) | no |
| `992a227` | **B7.2 root cause**: scheduler contamination of the SQL oracle; harness guard + 2 regression tests | tests only |
| this commit | kit RB-T28 coverage note, generated packets, records/manifest, this assessment | no |

## 2. Priority 1 — GuardianX GD7-05 / RB-T28 (write-side authorization)

| Question | Answer (LOCAL-AUTHOR evidence, SQLite and PostgreSQL 16.15) |
|---|---|
| Did RB-T28 demonstrate write-side authorization? | **No.** It passed because B6.2 filters the victim's reads. The foreign write itself succeeded |
| Reproduction at `4667ab8` | Tenant B `POST /evidence` under tenant A's inspection → **201**, row persisted with B as audit owner. Under A's ownerless `capa_suggestion` key → **201**. Under a non-existent inspection → **201**. B's explanation under A's inspection appeared in **A's replay**. B read A's explanations. `tenant_id_for_digital_twin` returned another tenant's twin health. The dry-run classifier attributes injected rows to the injector (`evidence/p472-03-batch7/gd7-05-write-side/`) |
| Strict write-side tripwires | RB-T29 (foreign owned source), RB-T30 (ownerless key in use), RB-T31 (explanation under foreign source), RB-T33 (digital-twin claim): each failed on its own assertion at `4667ab8`, then was converted at `6a661bb` with assertions unchanged. **RB-T32** (explanations disclosed cross-tenant) **stays a FAILING strict xfail** |
| RB-T28 | Preserved. Its assertion is unchanged; its set-up now seeds the foreign entry through the service, because the HTTP write is refused. The packet carries a **LIMITED COVERAGE** note. **RB-T28 is not independently accepted and must not be cited as write authorization** |
| What was implemented (`6a661bb`) | A fail-closed floor, from established policy only. `inspection`/`workflow_execution` sources must exist in the caller's verified tenant (otherwise 404, with no existence oracle). Writes into an ownerless key that already holds entries not provably the caller's are refused (403). Malformed source fields → 422. The digital-twin tenant claim goes through `refuse_other_tenants` (403) |
| What remains blocked on GD-7 (unsigned) | ownerless-key semantics (fresh keys are still first-writer; no namespace); explanation ownership and read gating (RB-T32); legacy contaminated rows; tenantless audit-evidence package; concurrent first-write race |
| Same-tenant writes | Controls pass (owner writes evidence and explanations under its own inspection and workflow execution; legacy pooled entries unreadable) |
| **Classification** | **GuardianX write authorization: NOT remediated, partial fail-closed floor only, NOT independently reviewed.** Separate open risks: R-GX-WRITE-AUTHZ, R-GX-EXPLAIN-READ (High), R-RBT28-COVERAGE, R-GX-OWNERLESS-KEYS, R-GX-WRITE-RACE, R-GX-LEGACY-CONTAMINATION, R-GX-PKG-TENANTLESS |

Design and inventory: `p472-03-batch7-gd7-05-write-side-authorization-v1.md`.

## 3. Verification record (exact counts)

### 3a. CI

| Commit | SQLite job → result | PostgreSQL 16 job → result |
|---|---|---|
| `2976b4e` | `135978365627` → 9223 passed, 3 skipped | `135978365382` → **1 failed**, 9223 passed, 2 skipped. **Root cause identified (B7.2 v2):** the nightly scheduler job's SQL was attributed to a request that the route correctly refused with 403. This is a test-oracle defect |
| `4667ab8` | `136025385538` → 9223 passed, 3 skipped, 0 xfailed | `136025385909` → 9224 passed, 2 skipped, 0 xfailed |
| `6a661bb` | `136031688736` → 9238 passed, 3 skipped, **1 xfailed** | `136031688345` → 9239 passed, 2 skipped, **1 xfailed** |
| `3fbbe65` | `136034982462` → 9238 passed, 3 skipped, 1 xfailed | `136034982422` → 9239 passed, 2 skipped, 1 xfailed |
| `7cc7bfb` | `136046505144` → 9238 passed, 3 skipped, 1 xfailed | `136046505518` → 9239 passed, 2 skipped, 1 xfailed |
| **`992a227`** (final code + B7.2 harness) | `136056334880` → **9240 passed, 3 skipped, 1 xfailed, 0 failed** | `136056335112` → **9241 passed, 2 skipped, 1 xfailed, 0 failed** |
| all of the above | secret scan, Ruff, frontend build, dependency audit (report-only): success | |

The 1 xfailed is **RB-T32**, an open finding. It is **not** a pass.
Skips (itemised): `test_benchmarking.py:83` (no hospitals), `test_p10_digital_twin.py:317` (no open alerts);
SQLite only: `test_p472_trusted_inference_provenance.py:788` (PostgreSQL-only Alembic chain).
Earlier PG16 failures on `3f479d9`/`c63d398`/`bc0cb94` are now **confirmed from their CI logs** as the census pin.
They were previously only inferred.

### 3b. LOCAL-AUTHOR on the final code

| Check | Command / source | Result |
|---|---|---|
| Full suite, SQLite | isolated worktree at `992a227`, `pytest tests -q -rfEsxX --junitxml` | **9240 passed, 3 skipped, 1 xfailed (RB-T32), 0 failed** (20 m 03 s). Identical to CI |
| Full suite, PostgreSQL 16.15, CI-faithful | `ci_pg_repro.sh`: fresh DB, Alembic up/down/up (exit 0), full suite on the same DB | **9241 passed, 2 skipped, 1 xfailed (RB-T32), 0 failed** (30 m 53 s). Identical to CI |
| The two suites ran concurrently | in **separate worktrees and databases** (not the shared-directory set-up that produced the invalid Batch 6 run) | — |
| Batch 2 route harness, both DBs | `pytest tests/test_p472_03_batch2_remediation.py` | SQLite 1926 passed; PG16 1926 passed |
| B7.2 deterministic reproduction | `b72_repro_plugin.py`, guard off / on | guard off: 3 of 5 (+1 of 2) failed with the CI assertion; guard on: 0 of 7 |
| GD7-05 write-side reproduction | `p472_03_gx_source_write_repro.py` at `4667ab8` / `6a661bb`, SQLite + PG16.15 | before: 201 / 201 / 201 (+ cross-tenant replay, twin claim); after: 404 / 403 / 404 / 404 / 403 |
| Tripwire review kit | `p472_03_tripwire_review_kit.py run`: before/after × original/final assertions, SQLite and PG16.15 | **112/112 variants matched expectation on each DB.** RB-T32 fails as an open finding (expected); RB-T28 after/original fails because its original set-up's foreign write is now refused. Controls passed: findings 2, harness 917, genesis 8, gd7 7, batch7 6 |
| Sweep, SQLite | `tenant_isolation_matrix.py --sweep sqlite` (`3fbbe65`, application code identical to `992a227`) | 1,913 routes, **0 findings**, 0 foreign-write routes; role-gated 164, partly exercised 735, unscoped leads 353 |
| Sweep, PostgreSQL 16.15 | `--sweep postgres` (`992a227`) | 1,913 routes, **0 findings**, 0 foreign-write routes; role-gated 164, partly exercised 729, unscoped leads 353 |
| **Sweep coverage change** | regenerated matrix | `POST /api/guardianx/evidence` and `/explainability` now return **422 at the sweep baseline** (its generic body names no valid source), so the sweep only *partly* exercises them. Their authorization rests on the dedicated tests RB-T29…T33, **not** on the sweep (R-SWEEP-BLINDSPOTS) |
| Register / matrix | regenerated from both sweeps | register empty; register-driven isolation tests **17/17** |
| Browser E2E | Chromium, real login, real backend, `tenantContext.e2e.mjs` on `992a227` | **6/6, twice** |
| Frontend | `npm test`; `npm run build` | 48/48; built |
| Ruff | `ruff check backend/app backend/tests` | All checks passed |
| Alembic | evidence manifest check; CI-faithful run | single head `b5a2c7e19d40`; up/down/up exit 0 |

Logs, JUnit, sweep JSONs and E2E output: `evidence/p472-03-batch7/final-992a227/`. Kit results: `evidence/p472-03-batch7/kit/`.
GD7-05 reproductions: `evidence/p472-03-batch7/gd7-05-write-side/`. B7.2: `evidence/p472-03-batch7/b72-ci-repro/`.

## 4. Gate matrix

| Gate | Status | Evidence class | What closes it |
|---|---|---|---|
| G1 tenant isolation (resolvers) | technically remediated; **PENDING** review | CI + LOCAL | non-author review of packets A′–E′ |
| G2 residual register / sweep | 0 sweep findings; oracle has blind spots (R-SWEEP-BLINDSPOTS, High) | LOCAL | review of unscoped leads, role-gated and partly-exercised routes |
| G3 AW-07 manufacturer identity | partly remediated; **OPEN** | — | GD-9 |
| G4 replay / object scope | remediated; **PENDING** review | LOCAL | review |
| G5 GD-3 | **PENDING** | — | review + decision |
| G6 PA-1 standing platform-admin / dev-token | **OPEN** (High) | — | PA-1 decision; unify gating; refuse at startup |
| G7 GD-5…GD-9, AUTH-1/2, CLIN-1 | **PENDING — none signed** | — | signatures (packets B7.3/B7.4) |
| **G7a GuardianX write authorization** | **OPEN — partial floor, NOT remediated** | LOCAL + CI | GD-7 decision; non-author review of RB-T29…T31/T33 |
| **G7b GuardianX explanation disclosure (RB-T32)** | **FAIL — strict tripwire failing** | CI + LOCAL | GD-7 ownership decision, then read gating |
| G8 clinical workflow | **PENDING** | — | clinical owner |
| G9 frontend contract | browser E2E (§3b); **PENDING** owner review | LOCAL | frontend/API owner |
| G10 CI security/lint/quality | PASS on `992a227` (secret scan, dependency audit, Ruff, frontend build) | CI | — |
| G11 CI backend suites | green with 1 xfail (RB-T32) since `6a661bb`. The `2976b4e` PG16 failure is explained; that explanation is author analysis, with review pending | CI | review B7.2 v2; residuals R-SCHED-SHUTDOWN, R-NIGHTLY-SILENT, R-ORACLE-SESSION-WIDE |
| G12 historical access | **BLOCKED** (production access; incident response) | — | authorize HIST plan + B7.4 additions |
| G13 independent review | **PENDING — 0 reviewers assigned** (1 collaborator, 0 PR reviews) | — | release authority appoints reviewers |
| G14 tripwires | **33 release blockers**: 32 author-converted + RB-T32 failing; **0 dispositioned** | CI + LOCAL | disposition ledger rows signed by non-authors |
| G15 release decision | **PENDING** | — | release authority |

## 5. Required human decisions (none made)

1. Appoint non-author reviewers for the 33 tripwire packets (`p472-03-batch7-tripwire-review-packets-generated-v1.md`,
   ledger `p472-03-batch7-tripwire-disposition-ledger-v1.md`).
2. **GD-7** — GuardianX ledger and explanation ownership, ownerless-key semantics, legacy rows. This unblocks
   RB-T32 and the remaining write authorization.
3. GD-5, GD-6 (Genesis self-publication), GD-8, GD-9, AUTH-1, AUTH-2, **PA-1**, CLIN-1 — packets in
   `p472-03-batch7-governance-decision-packets-v1.md` and `p472-03-batch7-clinical-data-governance-packet-v1.md`.
4. Authorize the historical-access investigation (HIST), including GuardianX writes and reads before Batch 6/7.
5. Review B7.2 v2. Decide R-SCHED-SHUTDOWN and R-NIGHTLY-SILENT.
6. The release decision itself.

## 6. Recommendation

**NO-GO / HOLD.** It rests on these facts:
* a failing strict security tripwire (RB-T32, cross-tenant explanation disclosure, High);
* GuardianX write authorization not remediated;
* 33 undispositioned release blockers;
* zero independent reviews;
* zero signed governance decisions;
* PA-1 open (High);
* historical access not investigated.

**PR #181 stays DRAFT, P472-03 OPEN. No merge, no deploy.**
