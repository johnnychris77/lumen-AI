# LumenAI — Research-Image Security Review Handoff (PR #171–#175)

**Purpose:** package the completed engineering security work for a **qualified, non-author human security reviewer**. This document is prepared by the implementing workflow for handoff only. **It is not an approval and issues no sign-off.**

**Baseline at handoff:**
- Repository: `johnnychris77/lumen-AI`
- PR: **#175** (draft, unmerged, undeployed) — branch `security/sec-174-01-audit-pg16-concurrency`
- Head SHA at handoff: **`d88c01a`** (local == remote; verified). A later documentation commit (this handoff) advances the head — see the Final Report / PR for the new SHA and its CI.
- Stack: #171 → #172 → #173 → #174 (`f9b8ff0`) → #175 (`d88c01a`)
- Data: synthetic images only.

> The CI evidence cited below for the research-image controls is CI run **`44021220045`** (head `4bc024b`, identical code to `d88c01a`): all 7 checks green, including **Backend tests (PostgreSQL 16)** (job `133830902180`), which ran the full suite at **4118 passed / 9 skipped**. The documentation commit that adds this file re-triggers CI; **its checks must be confirmed independently before relying on them** (see restriction: do not claim green until checks finish).

---

## 1. Executive summary

The research-image feature lets a verified research owner attest ownership of specific image bytes and ingest them into a per-tenant research dataset, with withdrawal, retention controls, and audit. The security work across PRs #171–#175 established:

- **Verified, per-owner ownership** bound to an OIDC subject (never inferred from matching bytes).
- **Centralized, fail-closed authorization** for every path that returns or consumes retained research-image bytes (closing a cross-endpoint disclosure found in audit).
- **Withdrawal and attestation revocation** honored, with PostgreSQL-16 concurrency evidence.
- **Durable, non-sensitive audit** of both granted and denied access.
- **Migration integrity** guards for the schema changes.

**Engineering validation completed:** full backend suite green on a fresh DB (local 4109 passed / 18 skipped; CI PostgreSQL 16 4118 passed / 9 skipped), Ruff clean, all 7 CI checks green on the reviewed code.

**Not completed (requires a human):** an **independent (non-author) security review (SEC-175-01)** and a **written disposition of SEC-174-02**. Every PR and every prior "independent" review in this chain was produced by the **same AI workflow**; that is a genuine assurance gap, not a formality. **Enterprise pilot authorization must not be granted on this package alone.**

---

## 2. Architecture and controls

**Authentication.** Research intake/attestation/withdrawal/retrieval require a cryptographically verified OIDC bearer token (`require_verified_oidc_context`): issuer/audience/exp/signature validated via JWKS, non-empty `sub`, enabled tenant membership. Dev/app-local JWTs are rejected on these routes. Generic endpoints (ml-images, dataset-registry, inspections) authenticate via `get_current_user`, which never yields an OIDC-verified principal — so they can never satisfy the research-owner branch of the gate.

**Tenant isolation.** All research queries are tenant-scoped; the central gate re-checks `image.tenant_id == caller tenant`; cross-tenant retrieval returns 404 with no existence disclosure.

**Ownership associations.** Ownership is an explicit per-owner row (`research_image_authorizations`): `(tenant_id, retained_image_id, research_dataset_id, owner_subject)` unique, bound to the verified `sub`, carrying the governance `attestation_id`. Two owners can authorize identical bytes (two rows, one shared `retained_images` row). Matching bytes grant nothing.

**Authorization (centralized, fail-closed).** `research_image_authorization_service.assert_image_bytes_readable` is the single policy for byte egress: non-research images keep their route authorization; research images require an OIDC-verified caller + an ACTIVE authorization for `(tenant, image, subject)` + a still-valid attestation (`GovernanceApproval.status == "approved"`). `may_read_image_bytes` is the non-raising form for internal consumers that degrade gracefully. Every egress routes through it (bytes endpoint, list/export exclusion, dataset quality/training, inspection report/analysis, baseline comparison).

**Withdrawal & revocation.** `withdraw_owner_authorizations` (actor+subject-bound, `FOR UPDATE`) withdraws only the requesting owner's associations; `delete_images_without_basis` deletes bytes only when no active auth (any owner) + no independent lawful basis (`source != trc001_research_intake`) + no other owner's legacy claim, verified by re-query. Attestation revocation invalidates access even while the association row is still ACTIVE.

**Audit persistence.** `audit_research_access_decision` writes granted/denied decisions through the single append-only, hash-chained enterprise audit writer and **commits before the authorization exception is raised** (survives request rollback); records tenant, actor, verified subject, resource id, decision, reason category, endpoint, request method/path, hash-chain, correlation id; **never** image bytes, tokens, or JWTs; **fail-closed** (audit failure still denies, no 500). `audit_logs` is immutable at the ORM layer (bulk UPDATE/DELETE blocked).

**Migration integrity.** `app/db/migration_guards.py` fails explicitly on missing prerequisite tables, verifies post-conditions (columns/index/nullability), refuses data-losing downgrades unless explicitly overridden; migrations add provenance columns + the association table with FKs/indexes. Revision chain: `c3e7a9b14d20 → e8b2c6d49f10 → f1a2b3c4d5e6`.

**Governance boundary (important).** Intake stamps `research_training_eligible=False`, keeps images `ground_truth_status=unknown`, and records `independent_ownership_verified=False` / `institutional_approved=False`. **Owner self-attestation is a technical ownership assertion only — not institutional/IRB approval and not verified scientific ground truth.** Those remain organizational controls outside this codebase.

---

## 3. Verification matrix (requirement → test → CI)

| Requirement | Test(s) | CI evidence |
|---|---|---|
| Hashes never establish ownership; two owners share bytes | `test_sec17104_image_authorization.py::test_two_owners_same_tenant_share_bytes` | SQLite + PG16 green |
| Ownership bound to verified OIDC subject | `test_trc001_research_oidc.py` (real JWKS chain) | SQLite + PG16 green |
| Tenant isolation / no cross-tenant disclosure | `test_sec17104…::test_same_bytes_different_tenants_isolated`; `test_sec17301…::test_cross_tenant_denied` | green |
| No cross-endpoint byte disclosure (research) | `test_sec17301_centralized_image_egress.py` (16) | green |
| Withdrawn owner denied; other owner retained | `test_sec17104…::test_one_owner_withdraws_other_retained` | green |
| Revoked attestation denies | `test_sec17301…::test_revoked_attestation_fails_closed`; `test_sec17401_pg16_concurrency.py::test_pg16_revoked_attestation_denies_after_commit` | PG16 green |
| Final-owner withdrawal deletes + verifies | `test_sec17104…::test_final_owner_withdraws_deletes_bytes` | green |
| Durable denied-access audit (10 properties) | `test_sec17401_denied_access_audit.py` (10) | SQLite green |
| Withdrawal concurrency (FOR UPDATE, pg_blocking_pids) | `test_trc001_ingestion.py::test_sec17102_*`; `test_sec17401_pg16_concurrency.py` (5) | **PG16 green** |
| Migration guards (missing table / post-condition / downgrade) | `test_trc001_provenance_migration.py` | green |
| Research images never training-eligible | `test_sec17301…::test_eligible_entries_excludes_research_source` | green |

PG16-execution proof: the PostgreSQL-16 job ran 4118 passed vs the SQLite job's 4109; the +9-passed / −9-skipped delta is the PG16-gated set (incl. the 5 concurrency tests) actually executing on PostgreSQL 16.

---

## 4. Per-finding evidence register

| Finding | Original concern | Remediation | Files / tests | PR / commit | CI | Limitations | Status |
|---|---|---|---|---|---|---|---|
| **SEC-171-01** Owner attestation | Attestation must bind to the verified session, not request body; not be treated as institutional approval | `resolve_owner_attestation` binds `declarant_subject`==verified `sub`; `independent_ownership_verified=False`, `institutional_approved=False` | `research/lens_vision/scientific_authorization.py`; `app/routes/trc001_research.py`; `test_trc001_research_oidc.py` | #171/#172 | green | attestation validity = approval status, no expiry | Remediated (pending independent review) |
| **SEC-171-02** Withdrawal concurrency | Withdrawal vs ingestion/retrieval races | per-row `FOR UPDATE`; serialized withdrawal | `research_image_authorization_service.py`; `trc001_intake.py`; `test_trc001_ingestion.py::test_sec17102_*` | #172 | PG16 green | — | Remediated (pending independent review) |
| **SEC-171-03** Migration integrity | Silent partial migration / unsafe downgrade | op-free guards; explicit failures; post-condition verify | `app/db/migration_guards.py`; migrations `e8b2c6d49f10`,`f1a2b3c4d5e6`; `test_trc001_provenance_migration.py` | #173 | green | no fault-injected end-to-end `alembic upgrade` test (SEC-175-03) | Remediated with limitation |
| **SEC-171-04** Ownership association | Ownership inferred from matching bytes | explicit per-owner association model + service | `app/models/research_image_authorization.py`; `research_image_authorization_service.py`; `test_sec17104_image_authorization.py` | #173 | SQLite+PG16 green | — | Remediated (pending independent review) |
| **SEC-173-01** Centralized image-byte authz | Research bytes reachable via generic endpoints w/o owner authz | single fail-closed gate at every egress | `assert_image_bytes_readable` + callers; `test_sec17301_centralized_image_egress.py` | #174 | green | — | Remediated (pending independent review) |
| **SEC-174-01** Durable denied-access audit | Denials not audited | `audit_research_access_decision` (committed, fail-closed, non-sensitive) at deny sites | `research_image_authorization_service.py`; routes; `test_sec17401_denied_access_audit.py` | #175 | SQLite green (CI) | bulk pipeline filtering not individually audited | Remediated (pending independent review) |
| **SEC-174-02** Ungated internal byte-readers | `compute_training_eligibility`, `load_research_samples` read bytes w/o central gate | none yet — **unreachable from any route** (verified) | `app/services/ml/training_eligibility_service.py:106`; `research/lens_vision/data_loader.py:26` | identified #174 review | n/a | latent; `compute_training_eligibility` lacks tenant filter | **OPEN** — see `SEC-174-02_DISPOSITION.md` |
| **SEC-175-01** Independent human review | Implement+review by one AI workflow | n/a — process control | this handoff package | — | n/a | requires a non-author human | **OPEN** — pending human reviewer |

---

## 5. Open findings

- **SEC-174-02 (Low, OPEN):** two services read `RetainedImage.image_bytes` outside the central gate; **not reachable from any HTTP route today**, so latent, not a live bypass. Requires a written disposition (gate vs formally accept). See `SEC-174-02_DISPOSITION.md`.
- **SEC-175-01 (High/assurance, OPEN):** no independent (non-author) security review exists. **This is the decisive gate to enterprise pilot authorization.** See `INDEPENDENT_SECURITY_REVIEW_INSTRUCTIONS.md`.

(Also tracked, Low: SEC-175-03 no fault-injected migration test; SEC-174-03 read-path is lock-free by design; local test-suite shared-DB isolation.)

---

## 6. Reviewer checklist (summary — full version in the instructions doc)

- **Authorization bypass:** attempt to retrieve a research image's bytes as (a) a same-tenant non-owner, (b) a cross-tenant user, (c) a withdrawn owner, (d) an owner whose attestation was revoked — through **every** byte-returning path (ml-images bytes/list/export, dataset quality/training, inspection report/analysis, baseline comparison, research retrieval). Expect denial everywhere; confirm the generic endpoints cannot present an OIDC identity.
- **Transaction races:** confirm the PG16 concurrency tests assert real blocking via `pg_blocking_pids()` (not timing); confirm no stale authorization after a committed withdrawal/revocation.
- **Migration safety:** confirm revision ordering, FK/index correctness, and that guards fail on missing prerequisites; note the absent fault-injected end-to-end test.
- **Audit durability:** confirm denial events persist after the request's error path, carry no bytes/tokens/JWTs, and that an audit-write failure still denies; confirm `audit_logs` immutability.
- **Residual risk:** evaluate SEC-174-02 reachability independently; assess attestation-validity (no expiry) and the organizational/technical boundary (attestation ≠ IRB/ground truth).

---

## 7. Reviewer decision (to be completed by the independent human reviewer — DO NOT prepopulate)

| Field | Value |
|---|---|
| Reviewer name | |
| Organization | |
| Role | |
| Independence declaration (not an author of the implementation) | |
| Review date | |
| Findings disposition | |
| Approval decision (PASS / CONDITIONAL / FAIL) | |
| Signature or approved review-record reference | |

*Prepared for handoff by the implementing workflow. No approval is issued or implied by this document.*
