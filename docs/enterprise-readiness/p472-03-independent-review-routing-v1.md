# P472-03 — Independent Review Routing (v1)

**Program:** P472-03 Enterprise Tenant Isolation · **PR #181 (DRAFT)**
Purpose: route each open item to an authorized, **non-author** reviewer. This agent is the author of
the code under review and therefore **cannot** review or approve any of it; no reviewer below may be
this agent. No self-review, no simulated approval.

## Assignment status

No authorized human reviewer identities or GitHub review permissions were provided to this agent, and
none may be invented. A formal GitHub review request is **not** submitted here, because guessing a
reviewer handle would misroute the request. Each slot is therefore **UNASSIGNED — HUMAN ACTION
REQUIRED**: a program owner with repository admin rights must assign the named role to a qualified
non-author and request the review on PR #181.

| # | Scope | Reviewer role required | Review package / entry point | Status |
|---|-------|------------------------|------------------------------|--------|
| 1 | Batch 2 (AW-01/02/05) | Independent application-security reviewer | `p472-03-batch2-independent-review-request.md`, `p472-03-batch2-independent-review-matrix-v1.md`; start at `app/auth/tenant_scope.py`, `app/tenant.py` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 2 | GD-3 tenant isolation | Independent tenant-isolation / security reviewer | `gd3-independent-security-assessment-v1.md`, `gd3-vendor-baseline-independent-review-request.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 3 | GD-3 migration (`d8f3a6b914c7`) | Database / platform-engineering reviewer | Day-3 remediation report §5 (PG16 NULL-quarantine, up/down) | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 4 | **AW-07 manufacturer identity (Batch 3)** | Identity & access management (IAM) reviewer | `p472-03-batch3-remediation-review-v1.md` §2; `app/enterprise_auth.py::require_manufacturer_auth`, `ManufacturerMembership`, migration `e7c2a9f04b18`, `test_p472_03_aw07_manufacturer_identity.py` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 5 | Clinical workflow (legacy quarantine / attribution) | Clinical operations & inspection-workflow owner | `gd3-clinical-workflow-approval-checklist-v2.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 6 | GD-1 … GD-4 | Authorized governance decision owners (one per decision) | `gd1-gd4-governance-decision-register-v2.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |
| 7 | Final release | Independent security / release authority | `p472-03-release-gate-evidence-index-v2.md` | **UNASSIGNED — HUMAN ACTION REQUIRED** |

## Rules
- Each reviewer must be independent of the author of the code/decision under review.
- A reviewer records their identity, timestamp and decision in the corresponding register only when
  they personally make it; unsigned items stay **PENDING**.
- No finding is closed, and no release criterion is marked satisfied, until the matching independent
  review is recorded.
