# P3 Enterprise Security Closure — Evidence Package

**Scope:** SEC-174-01 (durable denied-access audit evidence) and the PostgreSQL 16 concurrency gate for the research-image authorization controls.
**Branch:** `security/sec-174-01-audit-pg16-concurrency` · **PR:** #175 (draft, base = PR #174 branch `security/sec-173-01-centralized-image-egress`).
**Head commit:** `71aa579`.
**Stack:** PR #171 → #172 → #173 → #174 → **#175 (P3)**.
**Environment:** development/test only; synthetic images only; no production migrations; no real-image ingestion; no fabricated governance approvals.

> **This document is evidence for independent review. It does not grant security approval.** No status below is marked "Formally approved"; that column is the enterprise reviewer's to complete.

---

## 1. Status legend (evidence maturity)

| Maturity | Meaning |
|---|---|
| **Implemented** | Code/tests exist in the branch. |
| **Tested locally** | Executed on the dev machine (SQLite; no local PostgreSQL). |
| **Verified in CI** | Executed by GitHub Actions on a fresh per-run DB (incl. PostgreSQL 16). |
| **Independently reviewed** | Reviewed by someone who did not author the change. **Not yet.** |
| **Formally approved** | Enterprise security sign-off. **Not yet — out of this engineer's authority.** |

---

## 2. Security findings register (P3)

| ID | Severity | Status | Resolution | Blocks closure |
|---|---|---|---|---|
| SEC-174-01 | Low | Implemented + Tested locally + Verified in CI (pending) | Durable, non-sensitive denial auditing added at every user-facing deny site; fail-closed | Was the open item for SEC-173-01 clean closure |
| SEC-174-03 / SEC-173-04 | Low | Addressed by PG16 tests (Verified in CI, pending) | Real two-session PG16 lock-contention + no-stale-decision tests | Concurrency evidence for SEC-171-04 closure |
| SEC-174-02 | Low / architectural | Open (out of P3 scope) | Unexposed byte-readers (`compute_training_eligibility`, `load_research_samples`) not gated; **not reachable from any route** | No (latent, tracked) |

No new vulnerability was introduced by P3. No same-tenant non-owner research-byte egress path exists.

---

## 3. Image-byte egress inventory (carried from PR #174, re-confirmed)

| Path | Research bytes served to non-owner? | Denial audited (new) |
|---|---|---|
| `GET /api/ml/images/{id}/bytes` | No — 404 | **Yes** (`ml_images.get_image_bytes`) |
| `GET /api/ml/images`, `/api/ml/dataset/export` | No — research rows excluded | n/a (not a per-request image access) |
| `dataset_registry` quality assessment | No — 403 | **Yes** (`dataset_registry.assess_quality`) |
| `dataset_registry` candidate training / `eligible_entries` | No — research skipped/ineligible | n/a (bulk pipeline filtering) |
| inspection clinical report PDF / analysis reload | No — bytes omitted on deny | n/a (internal consumer, graceful degrade) |
| baseline comparison byte load | No — research source refused | n/a |
| research retrieval API (metadata only) | No raw bytes ever | success audited (pre-existing) + **denial audited (new)** |
| `load_processing_bytes` | n/a — separate temp table, no research bytes | n/a |
| `compute_training_eligibility`, `load_research_samples` | Not reachable from any route (SEC-174-02) | n/a |

---

## 4. Audit event evidence matrix (SEC-174-01)

Single writer: `app.services.enterprise_audit_service.record_enterprise_audit_event` — append-only, hash-chained per `(resource_type, resource_id)`, `_safe_details` sanitization. Immutability enforced by the `audit_logs` ORM guard (bulk UPDATE/DELETE on `AuditLog` raises `AuditImmutabilityError`).

| Property (Task 1) | How met | Test |
|---|---|---|
| 1. Authorized access auditable | research retrieval success audit (`trc001_research_image_access`) | `test_authorized_access_is_audited` |
| 2. Same-tenant non-owner denial audited | `research_image_access_denied`, reason `no_active_attested_authorization` | `test_same_tenant_non_owner_denial_audited` |
| 3. Withdrawn-owner denial audited | denial event, subject bound | `test_withdrawn_owner_denial_audited` |
| 4. Revoked-attestation denial audited | denial event after attestation revoked | `test_revoked_attestation_denial_audited` |
| 5. Missing-association denial audited | denial via ml bytes endpoint | `test_missing_association_denial_audited` |
| 6. Cross-tenant: no existence disclosure | response 404 unchanged; denial audited under caller tenant, reason `cross_tenant_or_missing` | `test_cross_tenant_denial_audited_without_disclosure` |
| 7. Not lost on authorization-exception rollback | audit committed before the HTTP error is raised; read back in a fresh session | `test_denial_audit_survives_request_rollback` |
| 8. Fail-closed on audit persistence failure | audit-writer exception → still denies, no 500 | `test_audit_write_failure_fails_closed` |
| 9. Not modifiable by ordinary users | `audit_logs` ORM immutability guard (bulk UPDATE/DELETE blocked) | relied upon (observed during test teardown) |
| 10. No new disclosure (no bytes/tokens/JWTs) | details carry only ids/categories; asserted no JWT/bearer/image-magic/size | `_assert_clean_audit`, `test_denial_audit_identity_and_no_sensitive_payload` |

Recorded fields: event type, timestamp, tenant, actor (email) + verified subject, resource id, decision, reason category, endpoint, request method/path, hash-chain (`event_hash`/`previous_event_hash`), correlation `request_id`. **Never:** image bytes, tokens, full JWTs, request payloads.

---

## 5. PostgreSQL 16 concurrency test matrix

`backend/tests/test_sec17401_pg16_concurrency.py` — PostgreSQL 16-gated (`pytest.mark.skipif` on dialect); real two-session transactions; lock contention proved with `pg_blocking_pids()` from a third observer connection. **Executed in CI only** (no local PostgreSQL).

| Scenario (Task 3) | Invariant | Test | Evidence type |
|---|---|---|---|
| 2. Withdrawal commits before retrieval authz | no stale decision; fresh check denies | `test_pg16_no_stale_authorization_after_committed_withdrawal` | committed-state |
| 5. Attestation revocation vs retrieval | denied after revoke; association still ACTIVE | `test_pg16_revoked_attestation_denies_after_commit` | committed-state |
| 3. Two owners share image, one withdraws | shared bytes retained; other authorized, withdrawn denied | `test_pg16_shared_bytes_retained_while_other_owner_active` | committed-state |
| 7. Concurrent association creation vs withdrawal | association `FOR UPDATE` serializes; consistent final state | `test_pg16_withdraw_locks_association_blocks_concurrent_reactivation` | `pg_blocking_pids` |
| 4. Final-owner withdrawal races retrieval/lock | retained-row `FOR UPDATE` blocks concurrent lock; row deleted after commit, no stale bytes | `test_pg16_final_owner_delete_locks_retained_row` | `pg_blocking_pids` |
| 1 & 6. Retrieval-before-withdrawal; concurrent ingestion/withdrawal | already covered | `test_trc001_ingestion.py::test_sec17102_*` (PR #172) | `pg_blocking_pids` |

Invariants asserted: no unauthorized bytes returned; withdrawal cannot silently restore revoked authorization; shared bytes retained while a valid basis remains; no stale ORM decision after committed withdrawal; consistent association/retention state; `lock_timeout` guards against unhandled deadlock; audit reflects the actual decision.

> **Note (SEC-174-03):** the read-only access authorization does not itself take a row lock — scenario 1 ("retrieval begins before withdrawal commits") resolves by READ COMMITTED snapshot (grant-then-withdraw or deny), serving no raw bytes either way. The security-relevant post-commit case ("no stale decision") is asserted directly.

---

## 6. Test execution results

| Suite | Where | Result |
|---|---|---|
| `test_sec17401_denied_access_audit.py` (10) | local SQLite | **10 passed** |
| `test_sec17401_pg16_concurrency.py` (5) | local SQLite | **5 skipped** (PG16-gated); **CI PG16: see run 44020997927 / job 133830202868** |
| `test_sec17301_centralized_image_egress.py` (16) | local SQLite | passed |
| `test_sec17104_image_authorization.py` | local SQLite | passed (PG16 subset skipped locally) |
| SEC-171-03 migration guards | local SQLite | passed |
| TRC research/oidc/ingestion | local SQLite | passed |
| **Combined (fresh DB)** | local SQLite | **94 passed, 9 skipped** |
| Ruff (`app` + `tests`) | local | **clean** |
| Full backend suite | CI (fresh DB) | **authoritative — see CI below** |

Local full-suite caveat: the dev suite shares a persistent SQLite file (`backend/test.db`) with no per-test truncation, so running many data-heavy suites in one process produces ordering/uniqueness artifacts (e.g. leftover `user_role_assignments` rows) unrelated to any code change; base commits reproduce them. Resetting the DB and running the security suites yields the 94/9 result above. CI runs each job on a fresh DB.

---

## 7. CI status (PR #175, head `71aa579`)

- Main workflow run: **`44020997927`** — Ruff, Secret scan, Backend tests (SQLite), **Backend tests (PostgreSQL 16)** (job `133830202868`), Dependency audit, Frontend build.
- enterprise-quality-gate run: **`44020998356`**.

At time of writing these runs are **in progress** (Secret scan already ✅). The **Backend tests (PostgreSQL 16)** job is the authoritative execution record for §5. This document should be read alongside the final CI conclusions on PR #175; green CI is necessary but, per the acceptance criteria, **not sufficient** for closure.

---

## 8. Migration compatibility

P3 changes **4 route/service files + 2 test files only**. No alembic/migration, model, or schema changes. Revision chain intact: `c3e7a9b14d20 → e8b2c6d49f10 (provenance) → f1a2b3c4d5e6 (associations)`. FK integrity, legacy retained-image behavior, association enforcement, withdrawal semantics, cross-endpoint authorization, and baseline-reference functionality are unchanged by P3 and are covered by the suites in §6.

---

## 9. Known limitations

- **No local PostgreSQL** in the dev environment: the PG16 concurrency tests are gated and run only in CI. Their pass/fail must be read from CI run `44020997927`, not claimed locally.
- **SEC-174-02** (unexposed byte-readers not gated) remains open; latent, not reachable from any route.
- **Attestation validity** = `GovernanceApproval.status == "approved"`; no expiry/time-box check beyond approval status.
- **Denial auditing scope:** user-facing per-request denials (ml bytes, research retrieval, dataset quality) are audited; bulk pipeline filtering (training eligibility, inspection byte omission) is not individually audited by design.
- **Local full suite** is order-fragile (shared DB); not a reliable local signal — a separate hardening task (per-test isolation) is recommended.

---

## 10. Residual risk assessment

| Risk | Level | Mitigation / status |
|---|---|---|
| Unauthorized research-byte egress via an app route | **Low** | No path found; gated + audited; 16+10 tests + PG16 gate |
| Stale authorization after withdrawal/revocation | **Low** | Fresh per-request checks; PG16 no-stale-decision test |
| Tamper/loss of denial evidence | **Low** | Committed before raise; append-only hash-chained; ORM immutability |
| Concurrency corruption of association/retention state | **Low** (pending CI) | `FOR UPDATE` serialization; PG16 `pg_blocking_pids` tests |
| Latent exposure of ungated internal readers | **Low** | SEC-174-02 tracked; not reachable today |

---

## 11. Recommended closure decisions

| Item | Recommendation |
|---|---|
| **SEC-174-01** | Eligible for independent closure review once CI run `44020997927` is green (durable, correctly-scoped, non-sensitive denial evidence demonstrated). |
| **SEC-173-01** | Resolved pending SEC-174-01 closure (its only open item). |
| **SEC-171-04** | Concurrency evidence now present (PG16 gate); eligible for independent closure review subject to CI PG16 green. |
| **SEC-171-03** | Unchanged by P3; prior CONDITIONAL PASS stands. |
| **PR #175 integration** | Ready to integrate onto the stack after CI green and independent review; no migration/model/locking regressions. |
| **Enterprise pilot authorization** | Not yet. Recommended gates: independent review of PR #174 + #175 by a non-author; CI PG16 green; close or formally accept SEC-174-02. |

---

## 12. Independent reviewer requirements

1. Confirm CI run `44020997927` (esp. **Backend tests (PostgreSQL 16)**) and `44020998356` are green on `71aa579`.
2. Re-verify no same-tenant non-owner path to research bytes across all egress (independent of this author's tests).
3. Inspect a sample of denial audit rows for correct scoping and absence of sensitive content.
4. Confirm the PG16 lock-contention tests assert real blocking (`pg_blocking_pids`), not timing.
5. Decide SEC-174-02 (gate now, or accept as tracked).
6. Record the **Independently reviewed** and **Formally approved** status — not done here.

*Prepared as evidence by the implementing engineer. Self-review is not independent approval.*
