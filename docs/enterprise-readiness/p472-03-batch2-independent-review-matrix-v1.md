# P472-03 — Batch 2 independent review matrix (v1)

| | |
|---|---|
| Reviewed commit | `1ff863d` (Batch 2 fixes `cf0eda2`…`63bc840`) |
| Priorities | **AW-01** analytics tenant isolation · **AW-02** audit-log tenant substitution · **AW-05** device registration & tenant membership |
| Reviewer | **UNASSIGNED — non-author application-security reviewer required** |
| Status | Review **structure and evidence** prepared by the author; **AWAITING NON-AUTHOR REVIEW** |

The exhaustive per-endpoint data lives in the authoritative matrix
`p472-03-application-wide-authorization-matrix.{md,csv}` (regenerated after each
batch) and the Batch 2 evidence `p472-03-batch2-remediation-review.md` §7. This
document is the **review instrument**: the ten assurance criteria applied to the
priority findings with representative routes, plus the attack paths a reviewer
must still probe. It does not restate the CSV.

## Ten assurance criteria

1. Authentication required · 2. Verified tenant resolution · 3. Object-level
authorization · 4. Cross-tenant read protection · 5. Cross-tenant write
protection · 6. List/aggregate isolation · 7. Background processing & exports ·
8. Audit-event correctness · 9. Error-response information disclosure ·
10. Compatibility with authorized workflows.

## AW-01 — Analytics tenant isolation (`cf0eda2` analytics; `48183fa` ML images, operations)

Representative routes: `GET /api/tenant-analytics/summary`,
`/tenant-analytics/export.{json,csv,xlsx,bundle.zip}`; `GET /api/ml/images`,
`/api/ml/retention/status`; the `p22_operations` routes.

| Criterion | Author-verified state | Reviewer action |
|---|---|---|
| 1 Authn | Bearer required; anonymous → 401 | Confirm on each route |
| 2 Verified tenant | Tenant from `principal_tenant` (membership-verified), not the header | Confirm no header re-read remains |
| 3 Object-level | Analytics are tenant-aggregate; ML image objects scoped by tenant | Probe foreign image id → not-found |
| 4 Cross-tenant read | A naming B → 403; member naming none → own tenant (was `default-tenant`) | Probe all header channels |
| 5 Cross-tenant write | ML image create bound to verified tenant; sweep foreign-writes = 0 | Probe write under B |
| 6 List/aggregate | Analytics summary/exports scoped to caller's tenant | Confirm export bundles carry no foreign rows |
| 7 Background/exports | Export routes synchronous; no background analytics job reads another tenant | Confirm no async export path |
| 8 Audit | Operations audit actor/role from the authenticated user (was `system`/`admin`) | Confirm |
| 9 Error disclosure | Foreign tenant → 403/404, no data in body | Confirm bodies reveal nothing |
| 10 Compatibility | Member selecting one of several memberships served normally | Confirm web client flows |

**Test evidence:** `test_p472_03_batch2_remediation.py` (per-route unauthenticated
+ 8 unverified-claim cases), `test_tenant_analytics*`, `test_ml_images*`. Mutation
check: ML/operations handlers reading the header again fails 32 tests.

## AW-02 — Audit-log tenant substitution (`cf0eda2`)

`resolve_tenant` returned the `X-Tenant-Id` header unverified and stored
`X-Tenant-Name` in audit rows (181 routes). Now it returns the verified tenant and
ignores `X-Tenant-Name`.

| Criterion | Author-verified state | Reviewer action |
|---|---|---|
| 2 Verified tenant | Header no longer trusted; two disagreeing headers → 403 | Confirm across the 181 routes (sample) |
| 5 Cross-tenant write | No audit row written under a foreign/forged tenant | Probe audit writes under B |
| 8 Audit correctness | Audit rows carry the verified tenant and authenticated actor | **Primary**: confirm no header-derived tenant/actor/role remains |
| 9 Error disclosure | Foreign header → 403 | Confirm |

**Known residual (open):** actor/role labels on 11 enterprise audit writes still
come from headers (recorded in the Batch 2 remaining-findings register) — reviewer
must treat these as **not** closed.

## AW-05 — Device registration & tenant membership (`6b20bb9`)

`current_user.tenant_id or <header>` fallback removed in 57 places across 43
modules, including device/capture registration (`capture.py`, `mobile.py`). A
verified member with no tenant header now acts in their own tenant, not
`default-tenant`; a user with no membership is refused.

| Criterion | Author-verified state | Reviewer action |
|---|---|---|
| 1 Authn | Bearer required | Confirm |
| 2 Verified tenant | Principal's tenant via membership; no header fallback | Confirm on device-registration routes |
| 5 Cross-tenant write | A device registered under B → refused | **Primary**: probe device registration under a foreign tenant |
| 6 List/aggregate | Device/station lists scoped to the caller's tenant | Probe cross-tenant device listing |
| 10 Compatibility | Single-membership users unaffected | Confirm capture-station flow |

**Known residual (open):** `require_tenant_roles` still treats "no header" as
`default-tenant` on 176 routes, so the web client cannot use those routes for a
normal tenant (recorded as open). AW-06M/AW-06N strict xfails cover the pooling
patterns that remain.

## Missing / still-required attack paths (for the reviewer)

The adversarial sweep sees only SQL bound through the application engine and only
what a request binds; it does **not** see leaks via response content, other
stores, background jobs, or correctly-scoped-but-over-returning handlers (that is
how AW-12 and AW-13 were found). A non-author reviewer must additionally probe:

- Response-content leaks on 2xx routes that correctly ignore a foreign header but
  may still emit another tenant's identifiers (the AW-13 pattern) — not covered by
  the SQL oracle.
- Tenant-triggered background jobs / scheduled scans beyond the SLA scan (AW-12
  pattern).
- The 731 partly-exercised and 164 role-gated routes the sweep could not fully
  drive.
- The open AW-03/AW-04/AW-06M/AW-06N/AW-07/AW-08 routes (strict xfails) — these are
  **not** part of Batch 2 and remain open.
- Refused requests are not audited — confirm whether that is acceptable.

## Disposition

Batch 2 fixes are **implemented and author-tested**, **not independently
reviewed**. Status: **AWAITING NON-AUTHOR REVIEW**. No finding is closed. HOLD /
NO-GO.
