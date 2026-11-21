# GD-1 … GD-4 Governance Decision Register (v2 — Batch 3 update)

**Program:** P472-03 · **PR #181 (DRAFT)** · supersedes `gd1-gd4-governance-decision-register-v1.md`
(preserved). This version adds Batch 3 status. **No decision below is signed.** An authorized,
accountable owner records their identity, timestamp and decision only when they personally make it;
until then every decision is **PENDING**. This agent cannot sign any of them.

| ID | Policy (decision text) | Accountable role | In code | Implementation evidence | Unresolved dependencies | Approver / timestamp / decision |
|----|------------------------|------------------|---------|-------------------------|-------------------------|---------------------------------|
| GD-1 | Operational counters require authentication unless explicitly approved for public release | Platform-security owner | Enforced (`440c0a1`) | 3 counters now 401 without credentials | Confirm which (if any) counters are approved-public | **PENDING** |
| GD-2 | Cross-tenant audit verification needs an authorized platform-security role, a stated purpose and tamper-evident logging | Platform-security owner | Fail-closed half only (verification limited to caller's tenant, `63bc840`); the authorized cross-tenant path is **not built** | Day-3 / Batch-2 evidence | Build + govern the authorized cross-tenant path | **PENDING** |
| GD-3 | Vendor baselines are tenant-private unless a sharing policy permits | Clinical + security governance | Tenant-private floor enforced + migration `d8f3a6b914c7` (NULL-quarantine); **category B (cross-tenant sharing) not implemented / design-only, blocked on AW-07 + governance** | GD-3 assessment + Day-3 §5 | Approve category B; AW-07 (now technically remediated — IAM review pending) | **PENDING** |
| GD-4 | Ownerless CAPAs stay quarantined until ownership is established | Quality governance | Enforced since Batch 1; pinned by tests | Batch-1 evidence | — | **PENDING** |

## Open governance items carried forward (not GD decisions, require owner direction)
- **PA-1 — platform-administrator cross-tenant access.** Access decision is governance-owned and
  **unchanged**; Day 3 added a structured security log of privileged cross-tenant resolution
  (`b7b2295`). Decisions required: (a) whether the privilege should exist and under what break-glass
  control; (b) a tamper-evident audit sink. **PENDING.**
- **AW-07 — manufacturer identity (new, Batch 3).** Technically remediated (`ManufacturerMembership`
  + verified `require_manufacturer_auth`, `e615afd`). Governance items: the manufacturer-onboarding /
  attribution workflow (who grants `ManufacturerMembership`), and keeping manufacturer-managed GD-3
  baselines disabled until approved. Independent **IAM** review PENDING.

**No release-governance decision is recorded. Disposition: HOLD / NO-GO.**
