# P4.1 — Critical Security Findings Register (SEC-176)

**Scope:** Independent triage of the automated-review (Codex) findings raised against the
research-image security controls (PRs #171–#174 chain), plus controlled remediation of the
findings CONFIRMED against the *current* integration head.

**Status:** Remediation implemented on a dedicated branch. **No merge. No deployment. No
production migration. HOLD INTEGRATION recommended** (see §5).

---

## 1. Integration topology (recorded at triage time)

| Item | Value |
|---|---|
| `origin/main` | `0f2ec588d24b7c64ccacd84adf67e89cb1ec1676` |
| Security-chain integration head (base for remediation) | `c111d93e11feea2ee6a2c6ab17277218c78ba3da` (`origin/security/sec-173-01-centralized-image-egress`) |
| Remediation branch | `security/p4-1-critical-findings-remediation` (from `c111d93`) |
| Security code on `main`? | **NO** — `research_image_authorization_service.py` absent on `origin/main`; base is **53 commits ahead** of `main`, none merged. |
| Stacked chain | Linear: #166 → #167 → #168 → #169 → #170 → #171 → #172 → #173 → #174 (research + security), plus merged-doc #175 work. |

**Consequence:** Because the confirmed P1 defects are in code that is **not yet on `main`**,
no integration target currently ships them — HOLD INTEGRATION is *precautionary*, not a
response to a live exposure. Integrating the chain as-is would be a clean fast-forward but
would bundle unmerged Stage-6 research PRs; that is a governance decision, not an automatic
step.

---

## 2. Finding triage (verified against current head `c111d93`, not the reviewed commits)

Codex reviewed **older** commits (#171 @ `117e083`, #173 @ `cc8a56b`). Each finding was
re-verified against the *current* code before any change. Findings already fixed in the
current head are recorded as such and **not** silently discarded.

| ID | Severity | Title | Verified vs current head | Disposition |
|---|---|---|---|---|
| **A** | P1 | Unknown-ownership research row deleted on another owner's withdrawal (data loss) | **CONFIRMED** | Fixed |
| **B** | P1 | `research_image_authorizations` not registered before `create_all` → table missing on fresh deploy | **CONFIRMED** | Fixed |
| **C** | P2 | Retrieval discloses image provenance-stamp dataset id instead of caller's authorized dataset | **CONFIRMED** | Fixed |
| **#7** | P1 | Verified-but-malformed OIDC claim → unhandled 500 instead of fail-closed 401 | **CONFIRMED** | Fixed |
| **#1** | P2 | Migrations import `app.db.migration_guards` at module top → `alembic history/heads` break where `app` is not importable | **CONFIRMED** | Fixed |
| **#3** | P2 | Association table absent from `alembic/env.py` autogenerate metadata → autogenerate could propose dropping it | **CONFIRMED** | Fixed |
| **D** | P1 | Intake-vs-withdrawal race | **ALREADY MITIGATED** in current head (dual `with_for_update()` on approval + association). Added a PG16 regression test; no code change required. |
| **#8** | P2 | Cross-owner attestation selection in `resolve_owner_attestation` | **NOT REPRODUCIBLE vs current head** — already owner-scoped (`requested_by == actor`, `reviewed_by == actor`) + `.with_for_update().all()`. No change. |

No finding was dismissed without reproduction against the current code.

---

## 3. Root-cause analysis (confirmed findings)

- **A — Incomplete retention basis.** `delete_images_without_basis` retained an image only
  when it had an active authorization, an independent (non-research) basis, or *another*
  owner's stamped legacy claim. A research row whose `research_owner_subject` is **blank**
  (unknown provenance) matched none of these and was deleted on a different owner's
  withdrawal. Deleting data of indeterminate ownership is unsafe; the fail-safe is to
  preserve it (while granting no access).

- **B — Registration gap between test and runtime.** The association model was imported only
  in the test `conftest`, never in the startup path. `Base.metadata.create_all()` creates
  only tables present in `Base.metadata` at call time, so a fresh deployment that bootstraps
  via `create_all` (rather than Alembic) never created `research_image_authorizations`.

- **C — Denormalized hint leaked as authority.** Retrieval returned
  `image.research_dataset_id` (a provenance stamp on the image row) rather than the dataset
  the *caller's* association actually authorizes. These can differ, disclosing a dataset id
  outside the caller's grant.

- **#7 — Validation outside the guard.** `map_claims_to_auth_context_payload` can raise
  `JWTValidationError` (e.g. missing tenant claim) but was called *after* the try/except that
  translates validation errors to 401, so a verified-but-malformed token produced an
  unhandled 500 (fail-open error signal rather than fail-closed denial).

- **#1 — Eager package import in revision modules.** `from app.db.migration_guards import …`
  at module top forces importing the `app` package merely to *parse* a revision, breaking
  offline Alembic introspection (`history`/`heads`) wherever `app` is not importable.

- **#3 — Autogenerate blind spot.** The association model was absent from `alembic/env.py`'s
  import list, so autogenerate did not see the table and could emit a spurious `DROP`.

---

## 4. Remediation summary (see `P4_1_SECURITY_REMEDIATION_EVIDENCE.md` for diffs + tests)

| ID | Change | Preserves |
|---|---|---|
| A | Add `_has_unknown_ownership_provenance`; include in `delete_images_without_basis` retain condition (strictly additive — preserves more, deletes less; grants **no** access) | unknown-owner data preservation; per-owner authz; revocation semantics |
| B | Register `app.models.research_image_authorization` (and `retained_image`, `capture_device`) in the startup lifespan **before** `create_all` | durable schema on fresh deploy |
| C | Add `authorized_dataset_ids_for_owner`; retrieval returns caller-authorized dataset(s), not the stamp | dataset-specific access; no cross-scope disclosure |
| #7 | Move `map_claims_to_auth_context_payload` inside the try/except → 401 | fail-closed OIDC-only access |
| #1 | Make `migration_guards` import lazy inside `upgrade()`/`downgrade()` in both revisions | migration integrity; run-time guards intact |
| #3 | Import the association model in `alembic/env.py` | autogenerate correctness |

**Invariants explicitly preserved (no weakening):** tenant data isolation; OIDC-only
per-owner authorization; durable hash-chained denial audit (SEC-174-01); revocation leaves
no stale authorization; `human_review_required` / non-causation language unchanged; secret
API-key hashing unchanged; no hardcoded `dev-token`. No retention-policy or research-
governance *semantics* were changed — Fix A only widens preservation (fail-safe) and never
grants access, so no authorized policy decision was required.

---

## 5. Recommendation

**HOLD INTEGRATION → remediate on branch → independent review gate.**

- The confirmed P1s are not on `main`; remediation lands on the chain head, not on `main`.
- A green CI result is **necessary but not sufficient** — it does not constitute security
  approval. SEC-174-02 and SEC-175-01 remain OPEN pending an authorized, independent
  (non-author) decision.
- Recommended disposition: **HOLD** until (a) this remediation PR passes all CI checks
  including Backend tests (PostgreSQL 16), and (b) a verified non-author reviewer signs off.

---

*Synthetic data only. No real TRC-001 research images were ingested. No FDA/regulatory
clearance is claimed anywhere. This document records a technical triage; it is not a security
approval.*
