# P472-03 — Independent Review Routing (v2 — Batch 4)

**PR #181 (DRAFT)** · **Issue #186** · supersedes `p472-03-independent-review-routing-v1.md` (preserved).
This agent authored the code under review and **cannot** review, approve or close any of it. No reviewer
identity was provided and none is invented: every slot is **UNASSIGNED — HUMAN ACTION REQUIRED** until a
program owner with repository rights assigns a qualified non-author and requests the review on PR #181.

| # | Scope | Reviewer role required | Entry point | Status |
|---|---|---|---|---|
| 1 | Batch 2 (AW-01/02/05) | Independent application-security reviewer | `p472-03-batch2-independent-review-request.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 2 | **Batch 4 tenant resolution** (AW-03/04/06M/06N, `require_tenant_roles`) | Independent application-security reviewer | `p472-03-batch4-remediation-review-v1.md`; `app/auth/tenant_scope.py`, `app/enterprise_auth.py::_verified_user_tenant`, `app/tenant_authz.py::_membership_tenant`; `tests/test_p472_03_batch4_remediation.py` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 3 | **Batch 4 contract changes** (§4 of the review) | Product / API owner + frontend owner | review §4; matrix `p472-03-batch4-authorization-matrix-v1.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 4 | AW-08 re-verification (Day-3 fixes) | Independent application-security reviewer | review §2.5; `fbd2581`, `137e9b1`, `ae54f5e` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 5 | GD-3 tenant isolation + migration `d8f3a6b914c7` | Security reviewer + database reviewer | `gd3-independent-security-assessment-v1.md`; Day-3 report §5 | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 6 | **AW-07 manufacturer identity** — provisioning, revocation, authorization, migration | Identity & access management (IAM) reviewer | packet A below | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 7 | **PA-1 platform-administrator / development-token exception** | Platform-security owner | packet B below | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 8 | Remaining register entry + GD-6 / GD-7 leads | Governance owners + security reviewer | review §5; `gd1-gd4-governance-decision-register-v3.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 9 | Clinical workflow (legacy quarantine / attribution) | Clinical operations owner | `gd3-clinical-workflow-approval-checklist-v2.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 10 | Final release | Independent security / release authority | `p472-03-release-gate-evidence-index-v3.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |

## Packet A — AW-07 facts for the IAM reviewer (author-assembled; not an assessment)
* **Authorization.** `require_manufacturer_auth` resolves the manufacturer from an enabled
  `ManufacturerMembership` of the authenticated principal; a claimed `X-Manufacturer-ID` not in the
  caller's memberships → 403; several memberships and none claimed → 403 (`e615afd`; 7 adversarial tests).
* **Provisioning.** **No code path creates a `ManufacturerMembership`.** There is no API, admin screen or
  service function; rows can only be inserted directly in the database. Consequently there is no audit
  trail of who granted a membership.
* **Revocation.** `is_enabled = false` is honoured by the check, but **no code path sets it**; revocation
  is likewise database-only and unaudited.
* **Migration.** `e7c2a9f04b18` creates the table with no backfill (fail-closed: every manufacturer portal
  returns 403 until rows exist). Verified on PG16 in Batch 4: single head; base → head; −1 → head.
* **Questions for the reviewer.** Who may grant/revoke; required approval and audit event for both;
  whether the "sole membership" implicit selection is acceptable; whether manufacturer-managed GD-3
  baselines stay disabled (they do).

## Packet B — PA-1 facts for the platform-security owner
* `principal_tenant` keeps the pre-P472-03 rule for the platform administrator (global role `admin`) and
  for development tokens (accepted only outside production): own tenant, else the named header, else
  `default-tenant`. Access decision **unchanged** in Batch 4.
* Logged (structured security log, not a tamper-evident sink) at two sites: privileged resolution to a
  tenant the principal is not a member of (Day 3), and the commercial platform-wide view (Batch 4).
* Batch 4 narrowed one use: analytics keeps requiring membership for a non-admin naming a tenant even with
  a development token (PR #81 rule), rather than adopting the looser exception.
* Admin-only routes that accept a body `tenant_id` (e.g. p20 sharing agreements) are unchanged.
* Decisions required: whether the privilege should exist, break-glass controls, tamper-evident sink.

## Rules
Reviewers record identity, timestamp and decision only when they personally make it; unsigned items stay
**PENDING**. No finding is closed and no release criterion is satisfied without the matching review.
