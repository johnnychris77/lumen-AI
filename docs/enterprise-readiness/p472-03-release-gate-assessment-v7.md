# P472-03 — Enterprise Release-Gate Assessment and Evidence Index (v7 — Batch 8)

**PR #181 (DRAFT) · Issues #190 / #189 · P472-03 OPEN** · supersedes v6 (preserved).

**Recommendation to the release authority: NO-GO / HOLD.** This is a recommendation, not a release decision. No
reviewer, signatory or release authority has acted on anything in this document.

## 0. Evidence classes

| Class | Meaning | Count at Batch 8 |
|---|---|---|
| CI | GitHub Actions on author-pushed commits | §3 |
| LOCAL-AUTHOR | runs by the change author in the development container | §3 |
| INDEPENDENT | reviews or runs by a non-author | **0 — none performed** |
| GOVERNANCE | signed decisions or release authorizations | **0 — none signed** |

"Remediated" means only that an author fix exists and its reproduction now passes.
Manifest: `evidence/p472-03-batch7/manifest.json`, rebuilt from `records.json`, which now includes the Batch 8
records.

## 1. Batch 8 commits (baseline `83dbf70`)

| SHA | Content | Application code? |
|---|---|---|
| `eec3bc8` | Tripwires RB-T34…T37 committed **failing** with the explanation reproduction script; application code unchanged | no |
| `c22a879` | **GuardianX explanations owned by their audit trail**; RB-T32 and RB-T34…T37 converted — **final application code** | **yes** |
| `6b2a8d6` | PA-1 environment-gate investigation (RB-T38…T40 **failing**), governance and forensic workflows, review kit | tests / docs / scripts |
| this commit | registers (tripwire v5, ledger v2, risk v7, governance v7), generated packets, records, manifest, this assessment | no |

## 2. Phase 1 — RB-T32 and the GuardianX explanation paths

Design and inventory: `p472-03-batch8-guardianx-explanation-ownership-v1.md`.

| | At `83dbf70` (fresh SQLite and PostgreSQL 16.15) | At `c22a879` |
|---|---|---|
| B reads A's explanations (list, by id, recommendation replay, audit-evidence package) | **200, A's private text** | 404 / own rows only |
| B appends a human override to A's explanation (a **write**) | **200, persisted** | **404, nothing persisted** |
| B writes an explanation under A's ownerless key | **201, shows in A's list** | **403** |
| Explanation with no provable owner (legacy) | served to every tenant | served to **no** tenant (quarantined) |
| Replay of another tenant's audit chain | verified and reported | "no events" (GD-2 scope); mixed chain 403 |
| Audit event for explanation writes | **none** | one per creation and override, under the verified tenant |
| Same-tenant list / read / override / replay / package | works | works |

Classification: **RB-T32 converted with its assertion unchanged, together with RB-T34…T37.** All five are author
conversions and remain release blockers pending a non-author disposition. **GD-7 is unsigned.** The floor reuses the
B6.2 audit-trail ownership rule and chooses neither Option T nor Option P. **RB-T28 remains read-side coverage
only.** GuardianX write authorization is a fail-closed floor, not a complete model: fresh ownerless keys are still
first-writer (R-GX-OWNERLESS-KEYS).

## 3. Verification record (exact counts)

### 3a. CI

| Commit | SQLite job → result | PostgreSQL 16 job → result |
|---|---|---|
| `83dbf70` (baseline) | run `44670488733` → success | success |
| `c22a879` (fix) | `136080604432` → **9256 passed, 3 skipped, 0 xfailed, 0 failed** | `136080603927` → **9257 passed, 2 skipped, 0 xfailed, 0 failed** |
| **`6b2a8d6`** (fix + PA-1 tripwires) | `136083146817` → **9258 passed, 3 skipped, 3 xfailed, 0 failed** | `136083146420` → **9259 passed, 2 skipped, 3 xfailed, 0 failed** |
| both runs | secret scan, Ruff, frontend build, dependency audit (report-only): success | |

`eec3bc8` was pushed together with `c22a879`, so CI never ran on it alone. Its failing tripwires are evidenced
locally and by the kit. **The 3 xfailed are RB-T38…T40: open PA-1 findings, failing on purpose. They are not
passes.**

Skips (itemised):
- `test_benchmarking.py:83` (no hospitals);
- `test_p10_digital_twin.py:317` (no open alerts);
- SQLite only: `test_p472_trusted_inference_provenance.py:788` (PostgreSQL-only Alembic chain).

### 3b. LOCAL-AUTHOR on the final code (`6b2a8d6`; application code `c22a879`)

| Check | Command / source | Result |
|---|---|---|
| Full suite, SQLite | isolated worktree, `pytest tests -q -rfEsxX --junitxml` | **9258 passed, 3 skipped, 3 xfailed (RB-T38…T40), 0 failed** (25 m 40 s) — identical to CI |
| Full suite, PostgreSQL 16.15, CI-faithful | `ci_pg_repro.sh`: fresh DB, Alembic up/down/up (exit 0), full suite | **9259 passed, 2 skipped, 3 xfailed, 0 failed** (40 m 41 s) — identical to CI |
| Explanation reproduction | `p472_03_gx_explanation_repro.py`, fresh SQLite + PG16.15 | before (`83dbf70`): 5 of 5 cross-tenant reads disclose; override 200 persisted; key injection 201 and visible; no audit event. After (`c22a879`): 0 disclose; override 404, nothing persisted; injection 403; foreign chain 0 events; owner controls work |
| GuardianX test files | 4 files, fresh SQLite and PG16 | 79 passed each (after fix) |
| Route-wide harness + isolation | `test_p472_03_batch2_remediation.py` + `test_p472_03_application_wide_isolation.py` | 1943 passed |
| Tripwire review kit | merged: RB-T01…T31/T33 from Batch 7 (after `6a661bb`); RB-T32 + RB-T34…T37 at `c22a879`; RB-T38…T40 at `6b2a8d6` | **136/136 variants matched expectation on SQLite; 136/136 on PG16.15.** A full-kit re-run was stopped at 32/29 variants (all matched) because of load; it was replaced by the targeted run. Logs are preserved |
| PA-1 probe | `p472_03_pa1_env_probe.py`, 8 configurations | render.yaml closed; PA1-01…03 reproduced (§G6) |
| Sweep, SQLite | `--sweep sqlite` at `6b2a8d6` | 1,913 routes, **0 findings**, 0 foreign-write routes; role-gated 164; partly exercised 735; unscoped leads 353 |
| Sweep, PostgreSQL 16.15 | `--sweep postgres` at `6b2a8d6` | 1,913 routes, **0 findings**, 0 foreign-write routes; role-gated 164; partly exercised 729; unscoped leads 353 |
| Register / matrix | regenerated from both sweeps | register empty; matrix unchanged; register-driven isolation **17/17** |
| Browser E2E | Chromium, real login, real backend | **6/6, twice** |
| Frontend | `npm test`; `npm run build` | 48/48; built (frontend unchanged since `c63d398`) |
| Ruff | `ruff check backend/app backend/tests` | All checks passed |
| Alembic | manifest check; CI-faithful run | single head `b5a2c7e19d40`; up/down/up exit 0 (no schema change in Batch 8) |

Evidence: `evidence/p472-03-batch8/` (`explanations-before/`, `explanations-after/`, `pa1/`, `kit/`,
`final-6b2a8d6/`).

**Failing security checks on the final code: 3** (RB-T38, RB-T39, RB-T40 — PA-1). **Reviewer decisions: 0.
Signed governance decisions: 0.**

## 4. Gate matrix

| Gate | Status | Evidence class | What closes it |
|---|---|---|---|
| G1 tenant isolation (resolvers) | technically remediated; **PENDING** review | CI + LOCAL | non-author review |
| G2 residual register / sweep | sweep 0 findings; oracle blind spots (R-SWEEP-BLINDSPOTS, High) | LOCAL | review of leads, role-gated, partly-exercised routes |
| G3 AW-07 manufacturer identity | partly remediated; **OPEN** | — | GD-9 |
| G4 replay / object scope | remediated (+ GD-2 chain scope, RB-T37); **PENDING** review | LOCAL | review |
| G5 GD-3 | **PENDING** | — | review + decision |
| **G6 PA-1** | **FAIL — 3 failing tripwires (RB-T38…T40)**; standing access, environment-gate defects, public demo token | LOCAL | PA-1 decision, then implementation and review |
| G7 GD-5…GD-9, AUTH-1/2, CLIN-1 | **PENDING — none signed** | — | signatures per the Batch 8 workflow |
| G7a GuardianX write authorization | fail-closed floor, **not complete**; review pending | LOCAL + CI | GD-7; review of RB-T29…T31, T33…T35 |
| G7b GuardianX explanation disclosure (RB-T32) | **author-remediated**; review pending (was FAIL in v6) | LOCAL + CI | review of RB-T32, T34…T37 |
| G8 clinical workflow | **PENDING** | — | clinical owner |
| G9 frontend contract | browser E2E (§3); **PENDING** owner review | LOCAL | frontend/API owner |
| G10 CI security/lint/quality | PASS on `c22a879` and `6b2a8d6` | CI | — |
| G11 CI backend suites | green, with 3 xfails (RB-T38…T40, open PA-1) on `6b2a8d6`; 0 xfails on `c22a879` | CI | not a release pass while tripwires fail or are undispositioned |
| G12 historical access | **BLOCKED** — forensic plan ready; production-access request **unsigned** | — | authorization (workflows doc Part B) |
| G13 independent review | **PENDING — 0 reviewers assigned** | — | release authority appoints reviewers |
| G14 tripwires | **40 release blockers**: 37 author-converted + **3 failing** (RB-T38…T40); **0 dispositioned** | CI + LOCAL | ledger v2 rows signed by non-authors |
| G15 release decision | **PENDING** | — | release authority |

## 5. Required human decisions (none made)

1. Appoint non-author reviewers for the 40 tripwire packets
   (`p472-03-batch8-tripwire-review-packets-generated-v1.md`, ledger v2).
2. **PA-1**: single production signal; refuse dev auth, default tokens and `DEMO_MODE` in production; demo-route and
   portfolio-access policy; platform-admin break-glass; bootstrap administrators.
3. **GD-7**: confirm or replace the explanation floor; ownerless-key semantics; legacy release with CLIN-1.
4. GD-5, GD-6, GD-8 (incl. portfolio access, PA1-04), GD-9, AUTH-1, AUTH-2, CLIN-1.
5. Authorize the historical-access investigation (HIST) and sign the production-access request.
6. The release decision.

## 6. Recommendation

**NO-GO / HOLD.** It rests on these facts:
* **three failing security tripwires** (PA-1: dev tokens under `ENVIRONMENT`-only production; public demo token on a
  destructive route; JWT-shape check gaps);
* 40 undispositioned release blockers;
* zero independent reviews;
* zero signed governance decisions;
* PA-1 open (High);
* historical access not investigated.

RB-T32 no longer fails, but its conversion is author-only.

**PR #181 stays DRAFT; P472-03 stays OPEN. No merge, no deploy.**
