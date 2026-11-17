# P4.5 — Independent Security Review Package

**For:** a qualified, **authorized, non-author** security reviewer. **Automated review (Codex)
and green CI do NOT substitute for independent human approval.** This package organizes the
evidence; the reviewer records the decision. Reviewed combined content: `7c0f679` (via #178
`8574a2a`); PR #176 `fdaee8e`, #177 `b35e552`.

Independence precondition (SEC-175-01): the reviewer must **not** have authored PRs #171–#178 or
the prior review documents, and must declare this. If you authored any of it, **stop.**

## 1. Control checklist

Legend: **Evidence** = test/CI proof; **Residual** = risk if the control is wrong; **Verify** =
what the independent reviewer must independently confirm.

| # | Control | Code location | Evidence | Residual | Independent verification |
|---|---------|---------------|----------|----------|--------------------------|
| C-01 | Authentication (OIDC-only research) | `app/routes/trc001_research.py::require_verified_oidc_context` (map-claims inside try → 401, SEC-176 #7) | `test_trc001_research_oidc.py`, `test_sec176_*::finding_7` | Fail-open 500 / dev-token | Re-run OIDC negative tests; confirm malformed token → 401 not 500 |
| C-02 | Per-owner authorization (object-level) | `research_image_authorization_service.py::authorize_image_access` / `assert_image_bytes_readable` | `test_sec17104_image_authorization.py`, `test_trc001_research_api.py` | Matching bytes grant access | Confirm per-(tenant,image,subject) + valid attestation required |
| C-03 | Tenant isolation | `assert_image_bytes_readable` tenant check; cohort/query scoping; artifact store | `test_sec17301_centralized_image_egress.py`, `test_p4_3_*::rgi04` | Cross-tenant read/write | Attempt cross-tenant resolve → denied |
| C-04 | Research-image ingestion + withdrawal | `research/lens_vision/trc001_intake.py::run_trc001_intake`; `withdraw_owner_authorizations`; `delete_images_without_basis` | `test_trc001_ingestion.py` | Stale authorization after withdrawal | Confirm withdrawal leaves no active authorization |
| C-05 | Legacy ownership preservation | `_has_unknown_ownership_provenance` (SEC-176 Fix A) in `delete_images_without_basis` | `test_sec176_*::finding_a*` | Data loss of unknown-owner rows; or over-grant | Confirm unknown-owner rows preserved AND still unreadable |
| C-06 | Authorization association integrity | `upsert_active_authorization`; model registered at startup (Fix B, `app/main.py`); migration `f1a2b3c4d5e6` | `test_sec176_*::finding_b`, `test_trc001_provenance_migration.py` | Missing table on fresh deploy | Confirm `create_all` creates `research_image_authorizations` |
| C-07 | PostgreSQL concurrency (Finding D / SEC-174-01) | `with_for_update()` on approval + association; `pg_blocking_pids()` tests | `test_trc001_ingestion.py::test_sec17102_postgres_*`, `test_sec17401_pg16_concurrency.py`, `test_sec176_*::finding_d` | Intake-vs-withdrawal race | **Run PG16 job**; confirm real lock-wait, no stale authz |
| C-08 | Denied-access audit durability | `audit_research_access_decision` → hash-chained append-only `audit_logs` (SEC-174-01) | `test_sec17401_denied_access_audit.py` | Audit lost on denial/rollback | Confirm denial event survives request teardown |
| C-09 | Research artifact storage (tenant-scoped, atomic) | `research/lens_vision/artifact_store.py::_encode/_path_enc/store_heatmap` (hex, atomic) | `test_p4_3_*::rgi04_*`, `test_stage5c/5d` | Cross-tenant overwrite/read | Exercise collision (`a/b` vs `ab`), atomicity |
| C-10 | Path traversal prevention | `artifact_store.py::_is_hex_component`, hex encoding | `test_p4_3_*::rgi04_path_traversal` | Escape `base_dir` via `..` | Craft `artifact://../..` ref → rejected |
| C-11 | Secret handling | API keys via `secrets.token_urlsafe(40)`, SHA-256 hash only, never retrievable | CI **Secret scan** (green); code read | Plaintext secret leak | Confirm no plaintext secret; secret-scan green |
| C-12 | Migration integrity | single head `f1a2b3c4d5e6`; lazy `migration_guards` import (SEC-176 #1) | `alembic heads`/`history` (19-edge linear); `test_trc001_provenance_migration.py` | Multiple heads / unimportable `alembic history` | `alembic heads` single; confirm fresh-DB upgrade on **PG16** (SQLite PG-only DDL is pre-existing) |
| C-13 | Scientific-use restrictions | `checkpoint.py::assert_scientific_checkpoint` wired into metric path (RGI-03); execution-only forced non-scientific; `anomaly_contract` init=False (RGI-13) | `test_p4_3_*::rgi03_*`, `test_stage6b_corrections.py` | Non-scientific weights back real metrics | Confirm `require_scientific=True` refuses ineligible checkpoint |
| C-14 | Authorization / approval value enforcement | `cohort_readiness.py` value validation (RGI-01); `valid_statistical_signoff` (RGI-02) | `test_p4_3_*::rgi01/rgi02` | Presence/truthiness accepted as authority | Confirm `denied`/`purged`/`{"approved":false}` rejected |
| C-15 | Security regression coverage | `test_sec176_*`, `test_p4_3_*`, stage suites | Full suite **4131 passed / 19 skipped**; combined PG16 green (CI) | Coverage gaps | Re-run full suite + PG16 on the combined head |

**Residual within scope:** C-09/C-10 carry the **legacy-reference** compatibility caveat (see
`P4_5_... ` legacy section of the risk register) — security-correct, backward-incompatible for
any pre-existing artifacts (none today).

## 2. SEC-174-02 — disposition form (latent out-of-gate byte reads)

**Finding (from `SEC-174-02_DISPOSITION.md`, re-verified):** `training_eligibility_service.compute_training_eligibility`
(no tenant filter, no `source` exclusion) and `research/lens_vision/data_loader.load_research_samples`
read `image_bytes` **without** the central `assert_image_bytes_readable` gate. **Latent** — no
HTTP route reaches either today. Severity **Low**.

**Precise acceptance criteria (verbatim from the disposition template — do NOT infer from the ID):**
- **Option A (gate — recommended):** route both byte reads through `assert_image_bytes_readable`
  (or the `source`-exclusion pattern) **and** add a tenant filter to
  `compute_training_eligibility`. *Acceptance:* a regression test shows (a) research-source rows
  excluded from both functions, and (b) cross-tenant rows unreadable via `compute_training_eligibility`.
- **Option B (quarantine):** guard that raises if either is called in a request context.
  *Acceptance:* a test shows the guard raises for a request-scoped caller.
- **Option C (formal risk acceptance):** written acceptance that both remain unexposed + a
  tracked action to gate before any future exposure. *Acceptance:* signed acceptance + tracking issue.

**Disposition (DO NOT prepopulate):**
| Field | Value |
|---|---|
| Reviewer name / org / role | |
| Independence declaration (non-author) | |
| Decision (A / B / C / Other) | |
| Rationale | |
| Follow-up actions + owner | |
| Review date | |
| Disposition status (Open / Accepted / Closed) | |
| Signature / approved review-record reference | |

## 3. SEC-175-01 — disposition form (independent-review closure)

**Closure procedure (from `INDEPENDENT_SECURITY_REVIEW_INSTRUCTIONS.md`, re-verified):** a
**verified non-author** reviewer reviews PRs #171–#175 (and now #176–#178) at their exact heads,
executes the synthetic + PG16 tests, assesses SEC-174-02, and records the decision + independence
declaration in the **Reviewer decision** section of `P3_SECURITY_REVIEW_HANDOFF.md`. **An AI
workflow's self-review does NOT close it.** Automated review and green CI are necessary, not
sufficient.

**Disposition (DO NOT prepopulate):**
| Field | Value |
|---|---|
| Reviewer name / org / role | |
| Independence declaration (did NOT author #171–#178 or prior reviews) | |
| Reviewed SHAs (#176 / #177 / #178) | |
| Checks executed (synthetic + **PG16**) | |
| Per-control findings (C-01..C-15) | |
| SEC-174-02 disposition referenced | |
| Decision (PASS / CONDITIONAL PASS / FAIL / INSUFFICIENT EVIDENCE) | |
| Conditions | |
| Date | |
| Signature / approved review-record reference | |

*No disposition is issued here. SEC-174-02 and SEC-175-01 remain OPEN until a qualified
non-author reviewer records decisions above.*
