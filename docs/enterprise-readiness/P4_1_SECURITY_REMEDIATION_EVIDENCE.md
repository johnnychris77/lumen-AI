# P4.1 — Security Remediation Evidence (SEC-176)

Companion to `P4_1_SECURITY_FINDINGS_REGISTER.md`. Records the exact changes, the regression
tests, and the verification results for the CONFIRMED findings.

**Branch:** `security/p4-1-critical-findings-remediation` (from `c111d93`,
`origin/security/sec-173-01-centralized-image-egress`).
**Remediation is NOT merged and NOT deployed.** No production migration was run. Synthetic
data only.

---

## 1. Changes by file

| File | Finding | Change |
|---|---|---|
| `backend/app/services/research_image_authorization_service.py` | A, C | Added `_has_unknown_ownership_provenance(image)`; added it to the `delete_images_without_basis` retain condition (strictly additive). Added `authorized_dataset_ids_for_owner(...)` (caller-scoped, attestation-validated). |
| `backend/app/routes/trc001_research.py` | #7, C | Moved `map_claims_to_auth_context_payload(validated)` inside the `try/except (JWKSSignatureValidationError, JWTValidationError)` → 401 on malformed claims. Retrieval now returns `authorized_dataset_ids` / caller-scoped `research_dataset_id` instead of `image.research_dataset_id`. |
| `backend/app/main.py` | B | Startup lifespan now `import_module(...)` for `app.models.research_image_authorization` (and `retained_image`, `capture_device`) **before** `Base.metadata.create_all(bind=engine)`. |
| `backend/alembic/env.py` | #3 | Imports `app.models.research_image_authorization` so autogenerate metadata includes the association table. |
| `backend/alembic/versions/e8b2c6d49f10_trc001_research_image_provenance.py` | #1 | `from app.db.migration_guards import …` moved from module top into `upgrade()`/`downgrade()`. |
| `backend/alembic/versions/f1a2b3c4d5e6_research_image_authorizations.py` | #1 | Same lazy-import treatment. |
| `backend/tests/test_sec176_critical_findings_remediation.py` | A,B,C,#7,D | New regression suite (8 SQLite tests + 1 PG16-gated). |

### Behavioural contract notes
- **Fix A** only widens preservation. It never deletes more and never grants access: an
  unknown-ownership row has no `ResearchImageAuthorization`, so every read path
  (`assert_image_bytes_readable`, `authorize_image_access`) still denies it. No retention
  *policy* semantics changed, so no authorized policy decision was required.
- **Fix C** response adds `authorized_dataset_ids` (list) and sets `research_dataset_id` to
  the single authorized dataset when exactly one, else `null`. Existing tests assert dataset
  id on the `RetainedImage` row, not on this response, so the contract change is compatible.
- **Fix #7** converts a fail-open 500 into a fail-closed 401; it cannot grant access.

---

## 2. Regression tests → findings

| Test | Guards |
|---|---|
| `test_finding_a_unknown_ownership_row_is_preserved_on_withdrawal` | A — preserve + still unreadable |
| `test_finding_a_own_known_owner_research_row_still_deletes` | A — control: normal reclamation intact |
| `test_finding_a_non_research_unknown_row_uses_independent_basis` | A — bases stay distinct |
| `test_finding_b_table_registered_in_metadata_and_created_by_create_all` | B — `create_all` creates the table |
| `test_finding_b_startup_imports_model_before_create_all` | B — startup registers model before `create_all` |
| `test_finding_c_retrieval_returns_caller_dataset_not_stamp` | C — caller scope, not provenance stamp |
| `test_finding_c_helper_excludes_unattested_rows` | C — fail-closed on unapproved attestation |
| `test_finding_7_malformed_claim_returns_401_not_500` | #7 — fail-closed 401 |
| `test_finding_d_pg16_authorization_row_lock_serializes_withdrawal_vs_reattest` | D — PG16 row-lock serialization (gated) |

### Pre-fix verification (tests are genuine guards, not fabricated)
Running the new suite against the **pre-fix** source (fixes `git stash`-ed, test file kept):

```
6 failed, 2 passed, 1 skipped
FAILED ... test_finding_a_unknown_ownership_row_is_preserved_on_withdrawal
FAILED ... test_finding_a_non_research_unknown_row_uses_independent_basis
FAILED ... test_finding_b_startup_imports_model_before_create_all
FAILED ... test_finding_c_retrieval_returns_caller_dataset_not_stamp
FAILED ... test_finding_c_helper_excludes_unattested_rows
FAILED ... test_finding_7_malformed_claim_returns_401_not_500
```
The 2 pre-fix passes are the deletion **control** (deletes with or without the fix) and the
metadata check (the test `conftest` force-imports the model regardless of startup wiring);
the latter is why the **source-guard** test is the authoritative Finding-B regression.

---

## 3. Verification results (current head + fixes)

| Check | Result |
|---|---|
| SEC-176 regression suite (SQLite) | **8 passed, 1 skipped** (PG16 D test skips without PostgreSQL) |
| Related security suites (`test_trc001_research_api`, `test_trc001_research_oidc`, `test_sec17104_image_authorization`, `test_sec17301_centralized_image_egress`, `test_trc001_provenance_migration`) | **60 passed, 2 skipped** |
| **Full backend suite** (fresh `test.db`) | **4117 passed, 19 skipped** (exit 0, 453s) — baseline 4109/18 + 8 new tests (+1 PG16-skipped) |
| Ruff (`ruff check app tests`) | **All checks passed** |
| Alembic head | **single head `f1a2b3c4d5e6`**; `alembic heads` / `alembic history` exit 0 (previously broke on eager `app` import) |
| Frontend build (`npm run build`) | **✓ built** |
| PostgreSQL 16 concurrency (Finding D) | Runs under CI **Backend tests (PostgreSQL 16)**; asserts real `pg_blocking_pids` waits. Not executed locally (no PG16 instance). |

> PostgreSQL 16 note: Finding D's serialization is additionally covered by the pre-existing
> `test_sec17102_postgres_*` two-session tests; the new PG16 test adds the association-row
> lock case. These execute only in the CI PG16 job.

---

## 4. Preserved security invariants (no weakening)

- Tenant data isolation — unchanged; all new queries are tenant-scoped.
- OIDC-only, per-owner authorization — unchanged; Fix #7 strengthens fail-closed behaviour.
- Durable hash-chained denial audit (SEC-174-01) — unchanged.
- Revocation leaves no stale authorization — unchanged; Fix A does not alter withdrawal.
- No hardcoded `dev-token`; secret API keys remain SHA-256-hash-only.
- No causation language introduced; `human_review_required` semantics untouched.
- No FDA/regulatory clearance claimed.

---

## 5. Gate

Per P4.1, work **STOPS at the remediation review gate**. A green CI result is necessary but
**does not** constitute security approval. SEC-174-02 and SEC-175-01 remain OPEN pending an
authorized, independent (non-author) decision. Recommended disposition: **HOLD INTEGRATION**
until CI (incl. PostgreSQL 16) is green on the remediation PR head **and** a verified
non-author reviewer signs off. No merge, no deployment, no production migration performed.
