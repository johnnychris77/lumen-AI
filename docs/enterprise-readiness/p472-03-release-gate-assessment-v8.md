# P472-03 — Enterprise Release-Gate Assessment and Evidence Index (v8 — PA-1 remediation)

**PR #181 (DRAFT) · Issue #190 · P472-03 OPEN · PA-1 governance OPEN (unsigned)** · supersedes v7 (preserved).

**Recommendation to the release authority: NO-GO / HOLD.** This is a recommendation, not a release decision. No
reviewer, signatory or release authority has acted on anything in this document.

## 0. Evidence classes

| Class | Meaning | Count |
|---|---|---|
| CI | GitHub Actions on author-pushed commits | §3a |
| LOCAL-AUTHOR | runs by the change author in the development container | §3b |
| INDEPENDENT | reviews or runs by a non-author | **0 — none performed** |
| GOVERNANCE | signed decisions or release authorizations | **0 — none signed** |

"Remediated" means only that an author fix exists and its reproduction now passes.

## 1. Commits (baseline `8bfcc9a`)

| SHA | Content | Application code? |
|---|---|---|
| `c2014ff` | PA-1 reproduction on SQLite + PostgreSQL (script, optional PG set-up); RB-T38…T40 still strict-xfail and **failing** | no |
| `829f36a` | **Canonical production determination + fail-closed gates**; RB-T38…T40 converted; layer tests; documented test amendments; config/docs | **yes — final application code** |
| this commit | registers (risk v8, tripwire v6, ledger v3, governance v8), PA-1 doc v2, assertion change log, packets, evidence, records, manifest, this assessment, kit and manifest-script updates | no |

## 2. PA-1 remediation (RB-T38, RB-T39, RB-T40)

Design: `p472-03-batch8-pa1-privileged-access-investigation-v2.md` §5. Test changes:
`p472-03-pa1-remediation-assertion-change-log-v1.md`.

| Configuration | At `8bfcc9a` (fresh SQLite and PostgreSQL 16.15, identical) | At `829f36a` (identical on both) |
|---|---|---|
| RB-T38: `ENVIRONMENT=production` only, `ENABLE_DEV_AUTH=true` | starts; dev token = **admin** | **refuses to start**; even without `app.main` the dev-token map is empty |
| RB-T39: production + `DEMO_MODE=1` | starts; `/api/demo/reset` with public `Bearer dev-token` → **200, seeded row deleted** | **refuses to start**; demo router alone → **403, row kept** |
| RB-T40: `APP_ENV=production` only; `Production` capitalised | JWT-shape check **off** | starts; check **on** |
| `AUTH_MODE=dev` + `ALLOW_DEV_AUTH_IN_PROD=true` in production | starts; dev token + header **admin role, any tenant** accepted | **refuses to start**; static token refused at request time too |
| `APP_ENV=development`, `ENVIRONMENT=production` (conflict) | starts | **refuses to start** |
| `render.yaml` (both production, oidc, dev auth off) | starts, closed | starts, closed (control unchanged) |
| development, `ENABLE_DEV_AUTH=true` / `DEMO_MODE=1` | dev token admin / demo reset 200 | **unchanged** (authorised development workflows preserved) |

Classification: **RB-T38, RB-T39, RB-T40 author-converted; assertion lines unchanged.** RB-T38/RB-T39 use an
**amended probe helper (A-1)** that a reviewer must judge. **PA-1 governance stays OPEN:** the floor was implemented
under the user's explicit direction. It is not a signed decision, and it removes the `ALLOW_DEV_AUTH_IN_PROD`
exception (contract change R-PA1-CONTRACT). No portfolio-wide access was activated, no administrator bootstrapped
and no role provisioned (PA1-04, PA1-07 unchanged; directive 6).

## 3. Verification record (exact counts)

### 3a. CI on `829f36a`

| Job | Result |
|---|---|
| Pilot Zero Gate — Backend tests (SQLite), job `136627844743` | **9317 passed, 3 skipped, 0 xfailed, 0 failed** |
| Pilot Zero Gate — Backend tests (PostgreSQL 16), job `136627844401` | **9318 passed, 2 skipped, 0 xfailed, 0 failed** (Alembic chain step: success) |
| Secret scan, Ruff, frontend build, dependency audit (report-only) | success |
| Core CI, Backend Compliance Tests, Security Baseline Scan, Security Hardening Validation, Enterprise Quality Gate | success |

The 3 SQLite skips match v7 (itemised below). Compared with `6b2a8d6` (9258 passed + 3 xfailed), the count rises by
3 conversions and 56 new tests (53 layer tests + 3 startup tests): 9261 + 56 = 9317.

Skips:
- `test_benchmarking.py:83` (no hospitals);
- `test_p10_digital_twin.py:317` (no open alerts);
- SQLite only: `test_p472_trusted_inference_provenance.py:788` (PostgreSQL-only Alembic chain).

### 3b. LOCAL-AUTHOR on `829f36a`

| Check | Command / source | Result |
|---|---|---|
| Reproduction before (`8bfcc9a`) | `scripts/p472_03_pa1_remediation_repro.py --db sqlite / postgres` | all three findings + the AUTH_MODE=dev path reproduced; identical on both DBs (`db_dialect` recorded per configuration) |
| Tripwires before (`--runxfail`) | `test_p472_03_batch8_pa1_env_gates.py`, SQLite and `PA1_PG_ADMIN_URL` | 3 failed / 2 passed on each DB; strict: 3 xfailed |
| Reproduction after | same script at `829f36a` | every production row closed; dev controls unchanged; identical on both DBs |
| Tripwire file after | SQLite / PostgreSQL | **8 passed / 8 passed** |
| Layer tests | `test_p472_03_pa1_remediation.py`, fresh SQLite / fresh PostgreSQL | **53 passed / 53 passed** |
| Full suite, SQLite (isolated worktree) | `pytest tests -q -rfEsxX --junitxml` | **9317 passed, 3 skipped, 0 xfailed, 0 failed** (28 m 18 s), identical to CI |
| Full suite, PostgreSQL 16.15, CI-faithful | `ci_pg_repro.sh`: fresh DB, Alembic up/down/up, full suite | Alembic up/down/up exit 0; **9318 passed, 2 skipped, 0 xfailed, 0 failed** (45 m 26 s), identical to CI |
| Review kit RB-T38…T40 | `p472_03_tripwire_review_kit.py run --ids RB-T38,RB-T39,RB-T40 --after 829f36a` | **12/12 variants matched expectation on SQLite; 12/12 on PG16.15** (`after/original` for RB-T38/T39 fails by design: A-1) |
| Sweep, SQLite | `tenant_isolation_matrix.py --sweep sqlite` | 1,913 routes, **0 findings**, 0 foreign-write routes; role-gated 164; partly exercised 735; unscoped leads 353 (identical to `6b2a8d6`) |
| Sweep, PostgreSQL 16.15 | `--sweep postgres` | 1,913 routes, **0 findings**, 0 foreign-write routes; role-gated 164; partly exercised 729; unscoped leads 353 (identical to `6b2a8d6`) |
| Register / isolation | register regenerated from both sweeps; register-driven isolation tests | register regenerated (empty; baseline relabelled); register-driven isolation **17/17** |
| Browser E2E | Chromium, real login, real backend (`APP_ENV=development`) | **6/6, twice**. A first attempt failed 0/6 because the backend was started without the documented `CORS_ORIGINS=http://127.0.0.1:5173` (login preflight 400). That was a set-up error, rerun with the documented set-up and recorded as R-E2E-CORS-SETUP |
| Frontend | `npm test`; `npm run build` | 48/48; built (frontend unchanged) |
| Ruff | `ruff check backend/app backend/tests` | All checks passed |
| Alembic | manifest check | single head `b5a2c7e19d40` (no schema change) |

Evidence: `evidence/p472-03-pa1-remediation/`:
- `before-8bfcc9a/`;
- `after-829f36a/`;
- `kit/`;
- `final-829f36a/`.

**Failing security checks on the final code: 0. Strict xfails: 0. Reviewer decisions: 0. Signed governance
decisions: 0.**

## 4. Gate matrix

| Gate | Status | Evidence class | What closes it |
|---|---|---|---|
| G1 tenant isolation (resolvers) | technically remediated; **PENDING** review | CI + LOCAL | non-author review |
| G2 residual register / sweep | sweeps 0 findings on both DBs; oracle blind spots (R-SWEEP-BLINDSPOTS, High) | LOCAL | review of leads, role-gated, partly-exercised routes |
| G3 AW-07 manufacturer identity | partly remediated; **OPEN** | — | GD-9 |
| G4 replay / object scope | remediated; **PENDING** review | LOCAL | review |
| G5 GD-3 | **PENDING** | — | review + decision |
| **G6 PA-1** | **environment gates author-remediated (RB-T38…T40 converted, was FAIL in v7); PA-1 governance OPEN** — standing global-admin rule, break-glass, portfolio access (PA1-04), non-production dev auth (PA1-05), bootstrap admin (PA1-07) unchanged | CI + LOCAL | PA-1 decision (ratify/replace the floor + decide the rest), second approver, non-author review |
| G7 GD-5…GD-9, AUTH-1/2, CLIN-1 | **PENDING — none signed** | — | signatures per the Batch 8 workflow |
| G7a GuardianX write authorization | fail-closed floor, **not complete**; review pending | LOCAL + CI | GD-7 |
| G7b GuardianX explanation disclosure | author-remediated; review pending | LOCAL + CI | review of RB-T32, T34…T37 |
| G8 clinical workflow | **PENDING** | — | clinical owner |
| G9 frontend contract | browser E2E 6/6 ×2; **PENDING** owner review | LOCAL | frontend/API owner |
| G10 CI security/lint/quality | PASS on `829f36a` | CI | — |
| G11 CI backend suites | **green with 0 xfails on `829f36a`** (SQLite 9317/3, PG16 9318/2) | CI | not a release pass while tripwires are undispositioned |
| G12 historical access | **BLOCKED** — forensic plan ready; production-access request **unsigned**. Fixed-in-code for PA1-01/02 is now `829f36a`; whether the defects were used in production is unknown | — | authorization (workflows doc Part B) |
| G13 independent review | **PENDING — 0 reviewers assigned** | — | release authority appoints reviewers |
| G14 tripwires | **40 release blockers: 40 author-converted, 0 failing; 0 dispositioned** | CI + LOCAL | ledger v3 rows signed by non-authors |
| G15 release decision | **PENDING** | — | release authority |
| G16 deployment contract (new) | `render.yaml` closed; the **deployed** environment's variables are **not verified** (no production access) | — | operations confirms deployed variables against the refusal list before any deploy (R-PA1-CONTRACT) |

## 5. Remaining vulnerabilities and risks (this remediation's scope)

- **R-PA1** (High, OPEN): standing global-`admin` cross-tenant rule; no break-glass or purpose binding; bootstrap
  administrator in deployment config (PA1-07).
- **R-PA1-NONPROD** (Medium): outside production the public literals and header-trusting `AUTH_MODE=dev` (default)
  still authenticate. Any shared staging environment not marked production is exposed.
- **R-PORTFOLIO-LATENT** (Medium): dead role/email grants, deliberately unchanged.
- **R-PA1-ENV-VALUES** (Low–Medium): only `production`/`prod` count as production.
- **R-PA1-CONTRACT** (Medium, availability): deployments relying on the removed exception, `DEMO_MODE`,
  `ENABLE_DEV_AUTH` or conflicting signals will refuse to start.
- **R-HIST**: whether PA1-01/02 or the AUTH_MODE=dev path were ever used in production is **not investigated**.

Full list: `p472-03-residual-risk-register-v8.md`.

## 6. Required human decisions (none made)

1. **PA-1** (owner + second approver):
   - ratify or replace the fail-closed floor, including the removed `ALLOW_DEV_AUTH_IN_PROD` exception;
   - environment vocabulary;
   - staging policy;
   - demo-route future;
   - platform-admin break-glass;
   - bootstrap administrators.
2. **PA-1 + GD-8**: portfolio access (PA1-04).
3. Appoint non-author reviewers for the 40 tripwire packets. RB-T38…T40: `p472-03-pa1-remediation-review-packets-v1.md`,
   including judgement of amendment A-1.
4. Operations: confirm deployed environment variables against the refusal list before any deploy.
5. GD-5, GD-6, GD-7, GD-9, AUTH-1, AUTH-2, CLIN-1; HIST authorization; the release decision.

## 7. Independent-review requirements

A reviewer who did not author `c2014ff` or `829f36a`:
1. Re-runs the kit for RB-T38…T40 on SQLite and PostgreSQL and compares with
   `evidence/p472-03-pa1-remediation/kit/`.
2. Judges A-1…A-4 in the assertion change log.
3. Confirms by code reading that every production-signal reader goes through `app/core/environment.py`, and that
   no new grant exists:
   - `portfolio_authz` keys untouched;
   - no membership, role or administrator creation.
4. Confirms OIDC and per-user JWT authentication still work in production.
5. Records a disposition in ledger v3 under their own identity. Self-approval by the author is not a disposition.

## 8. Recommendation

**NO-GO / HOLD.** Reasons:
- 40 undispositioned release blockers;
- zero independent reviews;
- zero signed governance decisions (PA-1 included);
- the standing privileged-access items above;
- historical access not investigated;
- the deployed configuration not verified against the new refusal list.

The three PA-1 tripwires no longer fail, but their conversion is author-only.

**PR #181 stays DRAFT; P472-03 stays OPEN; PA-1 stays OPEN. No merge, no deploy.**
