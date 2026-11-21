# P472-03 — Independent assurance review (v1)

| | |
|---|---|
| Program | P472-03 Enterprise Tenant Isolation |
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft) |
| Branch | `engineering/render-local-inference-p47` |
| Reviewed commit | **`1ff863d`** |
| Release disposition | **HOLD / NO-GO** · P472-03 **OPEN** |
| Prepared by | The remediation author |

> **This is not an independent review.** It is an assurance **package** prepared
> by the author of the remediation, to be used by non-author reviewers and policy
> owners. Wherever a judgement requires independence it is recorded as **AWAITING
> NON-AUTHOR REVIEW** or **UNASSIGNED — APPROVAL REQUIRED**, never as approved.
> Passing CI and passing author tests are engineering evidence, not security or
> governance approval.

## 1. Baseline (Phase 1)

- Branch and head verified: `engineering/render-local-inference-p47` @ `1ff863d`.
- PR #181 is **draft, open, not merged**.
- The remediation and documentation commits are present on the branch:
  `78426ce` (GD-3 floor), `5d3ec59` (Batch 2 review request), `38d1222` (GD-3
  dedup scoping), `c9a0f73` (GD-3 ownership ADR + review request), `1ff863d`
  (GD-3 governance handoff), on top of the Batch 2 stack `cf0eda2`…`728b587`.
- CI for `1ff863d` (run `44431365412`): **13 of 13 checks `success`**. Backend
  tests (SQLite) `8505 passed / 3 skipped / 15 xfailed / 0 failed`; Backend tests
  (PostgreSQL 16) conclusion `success` (full suite passed, 0 failed; the Alembic
  chain incl. GD-3 `d8f3a6b914c7` applies on PG16). Details and the note on the
  obscured PG16 integer line: `p472-03-release-gate-evidence-index-v1.md` §1.
  **Passing CI is engineering evidence, not security or governance approval.**

## 2. Scope of this package

| Phase | Deliverable | Status |
|---|---|---|
| 2 — Batch 2 independent review | `p472-03-batch2-independent-review-matrix-v1.md` | Review structure + routing prepared; **AWAITING NON-AUTHOR REVIEW** |
| 3 — GD-3 security assessment | `gd3-independent-security-assessment-v1.md` | Control checks + DB assurance + coverage gaps documented; **AWAITING NON-AUTHOR REVIEW** |
| 4 — Clinical-workflow safety | `gd3-clinical-workflow-approval-checklist-v1.md` | Impact + attribution-readiness checklist; **PENDING OWNER APPROVAL** |
| 5 — Governance GD-1…GD-4 | `gd1-gd4-governance-decision-register-v1.md` | Decision records; **all Sign-off PENDING** |
| 6 — Review assignments | §4 below + routing in `p472-03-residual-risk-register-v1.md` | **UNASSIGNED — APPROVAL REQUIRED** |
| 7 — Residual risk & release gate | `p472-03-residual-risk-register-v1.md`, `p472-03-release-gate-evidence-index-v1.md` | Reconciled against `1ff863d` |

Authoritative source documents (not duplicated here): Batch 2 evidence
`p472-03-batch2-remediation-review.md`; the per-endpoint matrix
`p472-03-application-wide-authorization-matrix.{md,csv}`; GD-3 design
`gd3-vendor-baseline-architecture-decision.md`; GD-3 review request
`gd3-vendor-baseline-independent-review-request.md`; the governance register
`p472-03-security-governance-decisions.md`.

## 3. What the implementation evidence shows (author verification)

- **Batch 2:** the shared resolver `app.auth.tenant_scope.principal_tenant`
  returns the membership-verified tenant for the affected routes; AW-01, AW-02,
  AW-05 no longer observed by the adversarial sweep; across all 1,912 routes the
  post-GD-3 sweep observes **zero** foreign-tenant writes.
- **GD-3 floor:** vendor-baseline reads/approvals/matching/scoring/audit/packets/
  counts are tenant-scoped; the migration preserves and quarantines pre-GD-3 rows
  (NULL owner → visible to no tenant), reversibly; cross-tenant list/approve/
  audit/scoring are refused; author tests pass.
- **Design only:** the ownership/sharing model, manufacturer-managed category and
  access-grant mechanism are **not built**.

These are necessary but **not sufficient** for release: they are the author's own
evidence, the full PostgreSQL 16 CI suite is PENDING, and no independent review
or governance sign-off has occurred.

## 4. Independent-review assignments (Phase 6) — none assigned

| Review area | Required reviewer | Status |
|---|---|---|
| Batch 2 authorization | Non-author application-security reviewer | **UNASSIGNED — APPROVAL REQUIRED** |
| GD-3 tenant isolation | Non-author security reviewer | **UNASSIGNED — APPROVAL REQUIRED** |
| Database migration `d8f3a6b914c7` | Database / platform-engineering reviewer | **UNASSIGNED — APPROVAL REQUIRED** |
| Clinical-workflow impact | Clinical operations / instrument-inspection workflow owner | **UNASSIGNED — APPROVAL REQUIRED** |
| Manufacturer identity / AW-07 | Identity & access-management owner | **UNASSIGNED — APPROVAL REQUIRED** |
| GD-1…GD-4 policies | Designated governance decision owners | **UNASSIGNED — APPROVAL REQUIRED** |
| Enterprise release gate | Authorized release / security-governance authority | **UNASSIGNED — APPROVAL REQUIRED** |

The repository does not identify who holds these roles; this document does not
guess, impersonate a reviewer, or record a self-generated approval.

## 5. Disposition

**PR #181 DRAFT — HOLD / NO-GO — P472-03 OPEN.** No merge, deploy, production-data
change, finding closure, or governance approval is made or implied by this package.
