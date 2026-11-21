# Governance Decision Register (v3 — Batch 4)

**PR #181 (DRAFT)** · **Issue #186** · supersedes `gd1-gd4-governance-decision-register-v2.md`
(preserved). **No decision below is signed.** Only an authorized, accountable owner records an identity,
timestamp and decision, and only when they personally make it. This agent cannot sign any of them.

## GD-1 … GD-4 — unchanged from v2
GD-1 (operational counters need authentication), GD-2 (cross-tenant audit verification), GD-3 (vendor
baselines tenant-private unless a sharing policy permits) and GD-4 (ownerless CAPAs quarantined): status,
evidence and dependencies as recorded in v2. **All PENDING.**

## New items raised by Batch 4 (decisions required; nothing implemented beyond the safe default)
| ID | Question | Current behaviour (safe default) | Evidence | Accountable role | Decision |
|---|---|---|---|---|---|
| GD-5 | May a client select its tenant by repeating a `tenant_id` in query/path/body, or only via `X-Tenant-Id`? | Claims must equal the verified tenant; selection only via header (Batch 4 contract) | review §4 | API / product owner | **PENDING** |
| GD-6 | Network knowledge feed (genesis manufacturer updates): may other tenants see unpublished (draft / pending-review) updates, and who may publish/reject another manufacturer's update? | Unchanged: all statuses listed to any member; any tenant's leadership role may review. The publisher filter remains the one open register entry | review §5 | Network / clinical governance | **PENDING** |
| GD-7 | Is the GuardianX evidence ledger platform-wide or tenant-owned? | Ledger rows have no tenant column; reads by id/source unscoped. Audit events now attributed to the verified tenant (`4308443`) | review §5 | Platform-security owner | **PENDING** |
| GD-8 | Should the commercial customer-success / business-case "platform-wide" view exist, and for whom? | Platform administrator / dev token only, logged; everyone else sees their own tenant | `76d7fc3` | Commercial + security owner | **PENDING** |

## Carried forward
* **PA-1** — platform-administrator / development-token cross-tenant exception. Unchanged, logged.
  Routing packet B. **PENDING.**
* **AW-07** — manufacturer-membership provisioning and revocation have no workflow or audit trail.
  Routing packet A. **PENDING.**

**No release-governance decision is recorded. Disposition: HOLD / NO-GO.**
