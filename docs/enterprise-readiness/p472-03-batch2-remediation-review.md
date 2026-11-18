# P472-03 — Remediation Batch 2: verified tenant membership (AW-01, AW-02, AW-05)

| | |
|---|---|
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft) |
| Branch | `engineering/render-local-inference-p47` |
| Baseline | `48ef45f` (remediation batch 1) |
| Release status | **HOLD / NO-GO** |
| P472-03 status | **Open.** Batch 2 closes nothing; it submits fixes for review. Section 9 lists what remains. |
| Independent review | **Not performed.** Every test here was written by the author of the fixes. |
| Governance decisions | Recorded in `p472-03-security-governance-decisions.md`. **None is signed off.** |

This document is the contract-impact assessment, the adversarial evidence, the
authorization matrix, the remaining-findings register and the review package
for batch 2. The historical access investigation plan is a separate document
(`p472-03-historical-access-investigation-plan.md`).

It does **not** claim tenant isolation for the application.

---

## 1. What batch 2 contains

Seven commits, one per root cause, in this order:

| Commit | Root cause | Finding |
|---|---|---|
| `cf0eda2` | `resolve_tenant` returned the `X-Tenant-Id` header unverified (181 routes) | AW-02, and the tenant-analytics part of AW-01 |
| `e59cd26` | A tenant administrator's "run SLA scan" ran the scan for every tenant | **AW-12 (new)** |
| `48183fa` | ML image and operations handlers read the tenant header behind a global role | AW-01 |
| `3dfd953` | Cross-hospital trend alerts returned the tenant ids of other organisations | **AW-13 (new)** |
| `6b20bb9` | `current_user.tenant_id or <header>` in 57 places | AW-05 |
| `440c0a1` | Three operational counters were public | Governance decision GD-1 (the three remaining AW-09 routes) |
| `63bc840` | Five audit verification routes were not limited to the caller's tenant | Governance decision GD-2 (batch 1 item R1) |

AW-12 and AW-13 were not in the application-wide review. Both were found by
the per-route test written for this batch (section 6.3) and are fixed here.
A third defect found on the way is **not** fixed and is recorded as open
(section 9, AW-08).

The findings you named as "cross-tenant analytics exposure", "audit-log tenant
substitution" and "device registration and membership enforcement" are the
exploit tests of AW-01, AW-02 and AW-05. Each of those findings is a shared
mechanism, so the fixes reach much further than the three examples: 678 routes
in 88 modules now resolve their tenant through one verified function.

---

## 2. Contracts before the change

| | AW-02 (and AW-01 tenant analytics) | AW-01 (ML images, operations) | AW-05 |
|---|---|---|---|
| Routes | 181 that declare `Depends(resolve_tenant)` | 28 handlers in two modules | 469 handlers that reach 57 call sites in 43 modules |
| Who is the actor | The bearer token, checked by `require_tenant_roles` (176 routes) or `require_roles` (5) | The bearer token, checked by `require_roles` or `require_inspection_runner` | The bearer token, checked by `require_roles` or `get_current_user` |
| What was verified | 176: an enabled membership for the tenant in `X-LumenAI-Tenant-Id`, else `X-Tenant-Id`, else `default-tenant`. 5: a global role only | A global role only | A global role only |
| Where the data tenant came from | `X-Tenant-Id`, else `default-tenant`. **A different header from the one verified** | `X-LumenAI-Tenant-Id`, else `X-Tenant-Id`, else `default-tenant` | The user's sole membership; **if the user had none or several, the header**, else `default-tenant` |
| Exploit | Send `X-LumenAI-Tenant-Id: <own>` and `X-Tenant-Id: <other>` | Name any tenant in the header | Hold a role with no membership (or two memberships) and name any tenant |
| Reproduced by | `test_aw02_split_tenant_headers_cannot_read_tenant_b_audit_logs`, `test_aw01_a_member_of_a_cannot_read_tenant_b_analytics_by_header` | 14 tests in `TestMlImagesAreTenantScoped`, `TestOperationsAreTenantScoped` | `test_aw05_a_user_with_no_membership_cannot_register_a_device_in_tenant_b`, `test_aw05_a_user_with_two_memberships_cannot_list_a_third_tenants_devices` |

All 181 `resolve_tenant` routes already required a token, so nothing in this
batch turns a public route into a protected one except the three counters of
GD-1.

---

## 3. The rule now enforced

One function, `app.auth.tenant_scope.principal_tenant(principal, request)`,
used by all three fixes:

- Two tenant headers that disagree are refused (403) for every caller. No code
  can then verify one header and act on the other.
- For a signed user token, which is the only kind accepted in production:
  - a tenant named in a header is honoured only if the user is an enabled
    member of it; any other named tenant is refused (403) and never replaced by
    the user's own tenant;
  - with no tenant named, the user acts in their sole membership;
  - a user with no membership, or with several and none selected, is refused
    (403). Nothing is served from a header alone and nobody is placed in a
    shared `default-tenant`.
- Anything that is not a verified principal object is refused.

**Two caller classes keep their previous behaviour**, which is "own sole
membership, else the named header, else `default-tenant`". Both are pinned by
tests so that a change to either is a visible decision:

| Class | Why unchanged | Status |
|---|---|---|
| Development tokens (`authentication_method == "development"`) | Issued only when dev auth is enabled and the environment is not production. The existing test suites rely on them | Known item (batch 1, R8) |
| Platform administrator (global role `admin`) | An existing, documented cross-tenant rule (`app/security/tenant_context.py`). Removing it would lock platform administration out of every tenant; widening it would be a new bypass | **Open governance item, section 9 (PA-1).** It has no stated purpose and leaves no access log |

No privileged cross-tenant path was added anywhere in this batch.

---

## 4. API contract-impact assessment

### 4.1 Changes

| # | Request | Before | Now | Kind |
|---|---|---|---|---|
| 1 | Any of the 678 routes: `X-LumenAI-Tenant-Id` and `X-Tenant-Id` with different values | Served; on 176 routes this read or wrote the second tenant | 403 | **Fix** |
| 2 | Any of the 678 routes: a tenant header naming a tenant the user is not a member of | 200 with that tenant's data on 209 routes; ignored silently on the rest when the user had one membership; 200 with that tenant's data when the user had none or several | 403 | **Fix / change** |
| 3 | 502 routes (AW-01, AW-05, tenant analytics): signed-in user with **no** tenant membership | 200 in `default-tenant` or in the header's tenant | 403 | **Change** |
| 4 | The same routes: user with several memberships and no tenant named | 200 in `default-tenant` | 403; naming one of their memberships works | **Change** |
| 5 | Tenant analytics, ML images, operations: member who names no tenant | Data of `default-tenant` | Data of the member's own tenant | **Change** (fixes the web client's normal path) |
| 6 | `resolve_tenant` routes: `X-Tenant-Name` header | Stored as the tenant's display name in audit rows and records | Ignored; the name is derived from the verified tenant id | **Change** |
| 7 | Operations routes: audit rows | Actor `system`, role `admin` for every request | The authenticated user and their role | **Change** |
| 8 | The three "run SLA scan" routes | Results of every tenant; SLA events written in every tenant | The caller's tenant only (`tenant_count: 1`) | **Fix (AW-12)** |
| 9 | `GET /api/governance-sla-scanner/status` | `last_run` of every tenant | The caller's own results | **Fix (AW-12)** |
| 10 | The three Horizon emerging-trend routes | `notified_tenant_ids_json`, `acknowledged_tenant_ids_json` | Removed. Added: `notified_organization_count`, `acknowledged_organization_count`, and the caller's own `notified` / `acknowledged` | **Fix (AW-13)** |
| 11 | Horizon contribution approval: audit row | Tenant copied from the request header | The approver's verified tenant, or `unassigned` | **Change** |
| 12 | The three operational counters, no credentials | 200 | 401 (403 with no membership) | **GD-1** |
| 13 | Audit chain verification of another tenant's resource | 200 with `event_count`, `verified`, `broken_event_id` | 200 with the "no events" body | **GD-2** |
| 14 | Audit chain that mixes the caller's events with another tenant's or with ownerless events | 200 | 403 | **GD-2** |
| 15 | Export, manifest or evidence-bundle hash of another tenant | Found, with filters, file name and count | Not found | **GD-2** |
| 16 | Any request by a member of exactly one tenant who names no tenant, or names their own | 200 | 200, same response | Compatible |

Response schemas are unchanged except rows 8 to 10.

### 4.2 Compatibility and migration requirements

1. **Every production account needs a tenant membership before this is
   deployed.** Row 3 is the change most likely to be noticed: an account that
   works today only because it has no membership (and therefore lands in
   `default-tenant`) will be refused on 502 routes. How many such accounts
   exist can only be read from production (`users` and `user_role_assignments`
   left-joined to `tenant_memberships`); that count is step 7 of the investigation
   plan. This is a deployment precondition, not something the code can decide.
2. **Data in `default-tenant`.** Rows written by membership-less users sit in
   `default-tenant`. After deployment they are reachable only by members of a
   tenant literally named `default-tenant` (and by the platform
   administrator). Whether that data is re-attributed is a data decision of the
   same kind as GD-4.
3. **Users with several memberships** must send `X-Tenant-Id`. The web client
   sends no tenant header and has no tenant switcher, so such a user is refused
   on these routes until the client gains one. None of the frontend's 12
   hard-coded tenant headers remain (removed in batch 1); no frontend change is
   needed for single-membership users, and none was made in this batch.
4. **External API clients** that send a fixed `X-Tenant-Id` for a tenant their
   account is not a member of will receive 403. They could not be surveyed
   from the repository.
5. **Anything that reads the three counters anonymously** stops working (GD-1).
6. **Audit chains containing ownerless events** stop verifying for their
   tenant (row 14) until those events are attributed or the platform-security
   path of GD-2 exists.
7. **No database migration.** No schema changed in batch 2.

---

## 5. What the fixes do not rely on

- Not on the client: the tenant is never taken from a header, query, path or
  body on its own.
- Not on object ids being hard to guess: object routes filter by the verified
  tenant, so another tenant's id reads as not found.
- Not on the frontend: no fix depends on a frontend change.

---

## 6. Adversarial evidence, before and after

### 6.1 Application-wide sweep

Every mounted route (1,912), each sent as an anonymous caller, with invalid
and expired tokens, as a member of tenant A naming tenant B in every header,
query, path and body channel, as a user with no membership, and as a user with
two memberships naming a third tenant. A hit is SQL executed for the request
that binds the foreign tenant.

| | Batch 1 (`48ef45f`) | after `cf0eda2` | after `48183fa` | after `6b20bb9` | after `440c0a1` (final) |
|---|---|---|---|---|---|
| Routes with a finding | 641 | 576 | 562 | 189 | **186** |
| AW-01 | 19 | 14 | **0** | 0 | 0 |
| AW-02 | 60 | **0** | 0 | 0 | 0 |
| AW-05 | 373 | 373 | 373 | **0** | 0 |
| AW-09 | 3 | 3 | 3 | 3 | **0** |
| AW-06N | 420 | 415 | 401 | 28 | 28 |
| AW-06M | 141 | 136 | 122 | 122 | 122 |
| AW-03 | 132 | 132 | 118 | 118 | 118 |
| AW-04 | 38 | 38 | 38 | 38 | 38 |
| Routes answering an anonymous caller with 2xx | 48 | 48 | 48 | 48 | 45 |
| Routes that wrote under a foreign tenant | 87 | 83 | 83 | 34 | 34 |
| New findings | — | 0 | 0 | 0 | 0 |

The intermediate columns are single SQLite runs made for each commit. The
final column is confirmed by two SQLite runs and one PostgreSQL 16 run; see the
PR description for whether they agree. AW-06N fell from 420 to 28 as a side
effect of the AW-05 fix (same line of code). AW-03 and AW-06M fell by 14 and 19
because the same routes carried several classes.

### 6.2 Exploit tests with stored data

`backend/tests/test_p472_03_application_wide_findings.py`. Each states the
secure behaviour and was a strict expected failure while the finding was open.

| Finding | Tests | Before | After |
|---|---|---|---|
| AW-01 | 1 | xfail: tenant A read tenant B's analytics by header | pass |
| AW-02 | 1 | xfail: split headers returned tenant B's audit log | pass |
| AW-05 | 2 | xfail: device registered in, and devices listed from, tenant B | pass |
| AW-06N (capture devices) | 1 | xfail: users with no membership shared a tenant | pass |
| AW-06N (literal `default-tenant`) | 1, new | — | **xfail: still open** |
| AW-08 (GuardianX replay) | 1, new | — | **xfail: still open** |

Only the markers were removed from the five converted tests; no assertion
changed. Eleven strict expected failures remain in that file, one for each
open finding or sub-finding, and one more in the governance tests for GD-3.

### 6.3 Dedicated tests

`backend/tests/test_p472_03_batch2_remediation.py`:

| Area | Tests | What is asserted |
|---|---|---|
| The rule | 28 | `principal_tenant` and `named_tenant` for every caller class and header combination, including the two unchanged classes |
| Route table | 1 | The routes are discovered from the mounted application: 181 through `resolve_tenant`, 497 that call the resolver in the handler. A route added or converted changes the count |
| Refusal, per route | 678 | An unauthenticated call and eight unverified tenant claims (B in either header, both split-header orders, no membership with and without naming B, two memberships with none selected and with a third tenant named). Each must be refused, must execute no SQL bound to the other tenant or to `default-tenant`, must write nothing, and must not name tenant B in the response |
| Owner, per route | 678 | The owner is served; a member who names no tenant is served (handler routes); a user with two memberships who selects one is served in that tenant, and the request touches neither of the other tenants |
| Coverage | 1 | At least 90% of the routes are reachable by one of eight role profiles; the rest are role-gated and were only shown to refuse |
| Audit logs | 25 | Owner reads only their own log in all five formats (including inside ZIP and XLSX); four header attacks on each are refused |
| Tenant analytics | 20 | A member sees their own tenant without naming it; naming B is refused; a manager with no membership is refused |
| Audit attribution | 2 | A write is recorded under the verified tenant, user and membership role; spoofed `X-Tenant-Name`, actor and role headers do not reach the row; a refused write stores nothing |
| SLA scan (AW-12) | 5 | Result, SQL and SLA events limited to the caller; the status route after a platform run and after another tenant's manual run |
| ML images | 6 | Listing, bytes by id, labelling by id, dataset export |
| Operations | 7 | Listing, steps and execution approval by id, a manager with no membership, attribution |
| Trend alerts (AW-13) | 5 | No response names another organisation; counts and the caller's own status are returned; the stored record is intact |

`backend/tests/test_p472_03_governance_policies.py`: 28 tests for GD-1, GD-2
and GD-4 and one strict expected failure for GD-3.

The per-route requests are built from the OpenAPI description by the same
builder the sweep uses. A route whose own request fails for every caller (a
missing object, an invalid body) is accepted only if it fails in exactly the
same way for the owner; it is still checked for SQL bound to another tenant.

### 6.4 Mutation checks

| Mutation | Tests that fail |
|---|---|
| `resolve_tenant` returns the header again | 210 |
| ML image and operations handlers use the header again | 32 |
| The shared resolver gives every caller the old rule | 437 |

### 6.5 What the tests found that the review had not

- AW-12 and AW-13 (fixed).
- An audit writer in the batch 1 module that stamped `default-tenant` on a
  governance-packet event, and the evidence-bundle event likewise (fixed with
  GD-2).
- The GuardianX replay routes load their subject by id with no tenant check
  (open, AW-08).

The first two classes were invisible to the sweep's oracle: the route was
correctly scoped at the edge and the defect was in what the action did or
returned. That is a limit of the sweep, and a reason not to read "none
observed" as "none".

---

## 7. Authorization matrix

The endpoint-by-endpoint matrix for the whole application is regenerated in
`p472-03-application-wide-authorization-matrix.md` (section 10) and the CSV
beside it. For batch 2 the per-endpoint list is also the parametrisation of
the two per-route tests (678 ids). By module:

| | Before | Now |
|---|---|---|
| Authentication | Bearer token (unchanged) | Bearer token (unchanged) |
| Role | `require_tenant_roles`, `require_roles` or `require_inspection_runner` (unchanged) | Unchanged, still applied |
| Tenant | Unverified header, or header fallback | `principal_tenant`: verified membership |
| Object level | Filtered by the tenant above | Filtered by the verified tenant |

"Resolved in" is `dependency` for `Depends(resolve_tenant)` and `handler` when
the handler calls the resolver. Findings are the sweep's, at `48ef45f` and at
the final commit.

<!-- BEGIN BATCH2 MODULES -->
| Module | Routes | Resolved in | Routes with a finding before | Classes before | Routes with a finding after | Classes after |
|---|---|---|---|---|---|---|
| `account_review_exports` | 6 | dependency | 0 | none | 0 | none |
| `advisory_pilot` | 13 | handler | 11 | AW-05 11, AW-06N 11 | 0 | none |
| `ai_clinical_review` | 2 | handler | 1 | AW-05 1, AW-06N 1 | 0 | none |
| `alerts` | 2 | handler | 2 | AW-05 2, AW-06N 2 | 0 | none |
| `anatomy_intelligence` | 1 | handler | 1 | AW-05 1, AW-06N 1 | 0 | none |
| `annotation_database` | 12 | handler | 8 | AW-05 8, AW-06N 8 | 0 | none |
| `apollo_quality` | 32 | handler | 25 | AW-05 25, AW-06N 25 | 0 | none |
| `approval_notifications` | 3 | dependency | 1 | AW-02 1 | 0 | none |
| `atlas_enterprise` | 2 | handler | 0 | none | 0 | none |
| `audit_logs` | 5 | dependency | 5 | AW-02 5 | 0 | none |
| `automation_studio` | 4 | dependency | 0 | none | 0 | none |
| `baseline_image_library` | 15 | handler | 11 | AW-05 11, AW-06N 11 | 0 | none |
| `billing` | 4 | dependency | 0 | none | 0 | none |
| `branding` | 4 | dependency | 0 | none | 0 | none |
| `briefings` | 5 | dependency | 0 | none | 0 | none |
| `capture` | 3 | handler | 3 | AW-05 3, AW-06N 3 | 0 | none |
| `catalyst_copilot` | 12 | handler | 7 | AW-05 7, AW-06N 7 | 0 | none |
| `clinical_readiness` | 10 | handler | 9 | AW-05 9, AW-06N 9 | 0 | none |
| `compliance_exports` | 5 | dependency | 2 | AW-02 2 | 0 | none |
| `customer_health` | 4 | dependency | 0 | none | 0 | none |
| `customer_operations_hub` | 6 | dependency | 2 | AW-02 2 | 0 | none |
| `customer_success` | 5 | dependency | 0 | none | 0 | none |
| `dataset_eligibility` | 1 | handler | 1 | AW-05 1, AW-06N 1 | 0 | none |
| `dataset_ingestion` | 2 | handler | 0 | none | 0 | none |
| `dataset_registry` | 16 | handler | 13 | AW-05 13, AW-06N 13 | 0 | none |
| `dataset_release` | 2 | handler | 0 | none | 0 | none |
| `distribution_lists` | 5 | dependency | 0 | none | 0 | none |
| `dunning` | 4 | dependency | 0 | none | 0 | none |
| `dunning_automation` | 3 | dependency | 0 | none | 0 | none |
| `entitlements` | 5 | dependency | 0 | none | 0 | none |
| `executive_scorecards` | 3 | dependency | 1 | AW-02 1 | 0 | none |
| `federated_horizon` | 13 | handler | 0 | none | 0 | none |
| `finance_console` | 1 | dependency | 0 | none | 0 | none |
| `finance_exports` | 3 | dependency | 0 | none | 0 | none |
| `governance_approvals` | 5 | dependency | 5 | AW-02 5 | 0 | none |
| `governance_command_center` | 7 | dependency | 7 | AW-02 7 | 0 | none |
| `governance_console` | 1 | dependency | 1 | AW-02 1 | 0 | none |
| `governance_reconciliation` | 3 | dependency | 1 | AW-02 1 | 0 | none |
| `governance_sla` | 5 | dependency | 5 | AW-02 5 | 0 | none |
| `governance_sla_scanner` | 3 | dependency | 2 | AW-02 2 | 0 | none |
| `guided_capture` | 1 | handler | 1 | AW-05 1, AW-06N 1 | 0 | none |
| `implementation_readiness` | 8 | dependency | 0 | none | 0 | none |
| `industry_collaboration` | 10 | handler | 3 | AW-05 3, AW-06N 3 | 0 | none |
| `inspections` | 6 | handler | 2 | AW-05 2, AW-06N 2 | 0 | none |
| `instrument_intelligence` | 1 | handler | 1 | AW-05 1, AW-06N 1 | 0 | none |
| `instrument_intelligence_admin` | 4 | handler | 4 | AW-05 4, AW-06N 4 | 0 | none |
| `knowledge` | 21 | handler | 18 | AW-05 18, AW-06N 18 | 0 | none |
| `leadership_packets` | 6 | dependency | 5 | AW-02 5 | 0 | none |
| `legal_hold_admin` | 1 | dependency | 1 | AW-02 1 | 0 | none |
| `ml_images` | 7 | handler | 6 | AW-01 6, AW-03 6, AW-06M 6, AW-06N 6 | 0 | none |
| `model_pipeline` | 15 | handler | 14 | AW-05 14, AW-06N 14 | 0 | none |
| `nexus_integration` | 25 | handler | 20 | AW-05 20, AW-06N 20 | 0 | none |
| `notification_templates` | 4 | dependency | 0 | none | 0 | none |
| `or_connect` | 18 | handler | 16 | AW-05 16, AW-06N 16 | 0 | none |
| `orbit_readiness` | 26 | handler | 22 | AW-05 22, AW-06N 22 | 0 | none |
| `p22_operations` | 21 | handler | 8 | AW-01 8, AW-03 8, AW-06M 8, AW-06N 8 | 0 | none |
| `packet_release_holds` | 6 | dependency | 5 | AW-02 5 | 0 | none |
| `packet_releases` | 6 | dependency | 5 | AW-02 5 | 0 | none |
| `pilot_deployment` | 5 | handler | 3 | AW-05 3, AW-06N 3 | 0 | none |
| `pilot_validation` | 4 | handler | 4 | AW-05 4, AW-06N 4 | 0 | none |
| `platform` | 18 | handler | 7 | AW-05 7, AW-06N 7 | 0 | none |
| `predictive_insight` | 20 | handler | 19 | AW-05 19, AW-06N 19 | 0 | none |
| `pulse_operations` | 18 | handler | 16 | AW-05 16, AW-06N 16 | 0 | none |
| `quality_dashboard` | 15 | handler | 13 | AW-05 13, AW-06N 13 | 0 | none |
| `quality_guardian` | 30 | handler | 26 | AW-05 26, AW-06N 26 | 0 | none |
| `release_governance_dashboard` | 4 | dependency | 4 | AW-02 4 | 0 | none |
| `reports` | 6 | dependency | 0 | none | 0 | none |
| `retention_admin` | 4 | dependency | 4 | AW-02 4 | 0 | none |
| `retention_enforcement` | 4 | dependency | 1 | AW-02 1 | 0 | none |
| `retention_scheduler` | 1 | dependency | 0 | none | 0 | none |
| `review_workspace` | 2 | handler | 2 | AW-05 2, AW-06N 2 | 0 | none |
| `reviewer_queues` | 1 | handler | 1 | AW-05 1, AW-06N 1 | 0 | none |
| `scenario_analysis` | 7 | handler | 6 | AW-05 6, AW-06N 6 | 0 | none |
| `scheduled_account_reviews` | 5 | dependency | 0 | none | 0 | none |
| `scheduled_leadership_packets` | 5 | dependency | 1 | AW-02 1 | 0 | none |
| `sentinel_orchestration` | 21 | handler | 21 | AW-05 21, AW-06N 21 | 0 | none |
| `shadow_validation` | 16 | handler | 15 | AW-05 15, AW-06N 15 | 0 | none |
| `spd_mentor` | 3 | handler | 2 | AW-05 2, AW-06N 2 | 0 | none |
| `subscription_lifecycle` | 6 | dependency | 0 | none | 0 | none |
| `tenant_analytics` | 5 | dependency | 5 | AW-01 5, AW-06M 5, AW-06N 5 | 0 | none |
| `tenant_scoped_subscriptions` | 3 | dependency | 0 | none | 0 | none |
| `tenant_setup` | 1 | dependency | 1 | AW-02 1 | 0 | none |
| `trust_center` | 1 | dependency | 1 | AW-02 1 | 0 | none |
| `trust_center_exports` | 2 | dependency | 0 | none | 0 | none |
| `usage_metering` | 4 | dependency | 0 | none | 0 | none |
| `vanguard_intelligence` | 17 | handler | 11 | AW-05 11, AW-06N 11 | 0 | none |
| `workflow` | 15 | handler | 15 | AW-05 15, AW-06N 15 | 0 | none |
| `workflow_forge` | 12 | handler | 6 | AW-05 6, AW-06N 6 | 0 | none |
| **Total (88 modules)** | **678** | | **439** | | **0** | |
<!-- END BATCH2 MODULES -->

239 of the 678 routes showed no sweep finding before. Most of those are
`resolve_tenant` routes whose legitimate request the sweep could not complete;
they had the same defect by construction and are covered by the per-route
tests.

---

## 8. Existing tests changed

| Tests | What they did | Change |
|---|---|---|
| `test_tenant_api_boundaries` (3 tests) | Replaced one of two identity lookups with a patch and sent no token | Send a real signed token for the same user. Assertions unchanged |
| `test_baseline_image_comparison_operational::test_upload_and_create_resolve_same_tenant_for_jwt_user` | Overrode the current user with a bare object carrying a `tenant_id` attribute | Uses a real principal with that membership. Assertions unchanged |
| `test_federated_horizon::test_acknowledge_trend` | Asserted the caller's tenant id appeared in `acknowledged_tenant_ids_json` | **Assertion changed.** The field is removed (AW-13); the test asserts the caller's `acknowledged` flag, the count, and that the lists are absent |
| `test_p15_network`, `test_p25_infrastructure`, `test_p23_global_intelligence` (3 tests) | Asserted the three counters are public | **Assertions reversed** (GD-1): 401 without a token, 200 with one. Tests renamed. Five more tests of these routes now send a token; their assertions are unchanged |
| `test_p472_03_application_wide_findings` | Strict expected failures | Five markers removed, two new expected failures added |
| `test_p472_03_application_wide_isolation` | Counted routes of pinned remediated groups | Count extended by the five batch 2 modules |
| `test_p472_03_batch1_remediation` | Excepted five verification routes from the tenant-filter check | Four of them are no longer excepted (GD-2) |

Four assertions about behaviour changed, all listed above, and each asserted
the behaviour that was the defect or the policy being replaced. The commit
message of `3dfd953` says its change was "the one existing assertion changed
in batch 2"; that was true when it was written and is superseded by this
table.

---

## 9. Remaining findings register

### 9.1 From the application-wide review, still open

| ID | Risk | Routes | Notes |
|---|---|---|---|
| AW-03 | High | 118 | Handler re-reads the raw tenant header after `require_enterprise_auth` |
| AW-06M | High | 122 | Verified members who send no header act in `default-tenant` on those routes |
| AW-04 | High | 38 | Tenant from a query, path or body parameter |
| AW-07 | High | 20 by pattern | Manufacturer identity from a client header |
| AW-08 | High | **4 confirmed** (was 3), 927 leads | SQL on tenant tables with no tenant predicate. New: `GET /api/guardianx/audit-replay/inspections/{id}` serves another tenant's inspection to any tenant member; the sibling replay routes use the same pattern and were not individually confirmed |
| AW-06N | Medium | 28 | Literal `default-tenant` fallback (16 places in 6 modules: `cios`, `knowledge_graph`, `agents_pipeline`, `pre_sterilization_command_center`, `lumen_decision_engine`, `spd_mentor`) and other routes that pool users with no membership |

### 9.2 Opened or left open by batch 2

| ID | Item | Risk |
|---|---|---|
| PA-1 | The platform administrator (global role `admin`) reaches any tenant by naming it, on every route that uses the resolver. Existing behaviour, deliberately unchanged, pinned by a test. It has no stated purpose and no access log, which is what GD-2 requires for audit verification | Governance decision needed |
| GD-3 | Vendor baselines are one library for all tenants. Decided, **not implemented** (schema change; existing rows need an attribution rule) | Open |
| GD-2 (part) | The authorized cross-tenant verification path is not built. Chains with ownerless events cannot be verified by their tenant | Open, by design |
| GD-1 (part) | Two counters return invented figures when their tables are empty | Data integrity |
| B2-1 | Client-supplied name fields on operations routes (`approved_by`, `claimed_by`, `completed_by`, `escalated_by`, `reviewed_by`, `created_by`) are stored as sent. The audit row carries the verified user; the business record does not | Low |
| B2-2 | Enterprise quality routes still take the actor and role label of 11 audit writes from `X-LumenAI-Actor` / `X-LumenAI-Role` (batch 1, R7). The tenant of those rows is verified | Low |
| B2-3 | `require_tenant_roles` itself still treats "no tenant header" as `default-tenant`. With the resolver fixed this is fail-closed (a member of one tenant who sends no header is refused on those 176 routes unless they are also a member of `default-tenant`), but it means the web client, which sends no header, cannot use those routes for a normal tenant. Functional, part of AW-06M | Functional |
| B2-4 | The other cross-hospital sharing responses were not reviewed for the AW-13 pattern (identity lists returned with a shared record) | Not reviewed |
| B2-5 | Other tenant-triggered actions were not reviewed for the AW-12 pattern (a tenant's request starting a platform-wide job). The per-route test would catch one that touches another tenant's rows for a route in its table; routes outside the table are not covered | Not reviewed |
| B2-6 | Refused requests are still not audited | Low |
| B2-7 | The development tokens trust the tenant header (rejected in production) | Known |

### 9.3 Unchanged from batch 1

R2 (now GD-3), R3 (vendor governance events in process memory), R4 (now
GD-4), R5 (audit rows written without a tenant by other modules land in
`default-tenant`), R6 (CAPAs created by workflow engines: the calling routes
now resolve a verified tenant, so this is reduced but was not re-tested per
engine), R9 (three POST routes answer 422 before 401).

### 9.4 Not conclusive, as in the review

731 routes were only partly exercised by the sweep (their legitimate request
failed) and 164 are role-gated beyond the sweep's identities; both figures are
unchanged by batch 2. 927 routes with no finding show SQL on a tenant table
without a tenant predicate and are unconfirmed leads. That figure was 473
before batch 2: it rose because routes that left the findings register are now
counted in this bucket, not because any SQL changed (1,111 routes execute such
a statement, before and after). Production was not examined.

---

## 10. Independent security-review package

**What is submitted.** Commits `cf0eda2` to `63bc840` and the commit that
contains this document. Start with `backend/app/auth/tenant_scope.py`
(the rule, about 60 lines) and `backend/app/tenant.py`.

**How to reproduce.** From `backend/`:

```bash
ruff check app tests scripts/tenant_isolation_matrix.py
python -m pytest tests/test_p472_03_batch2_remediation.py tests/test_p472_03_governance_policies.py \
    tests/test_p472_03_application_wide_findings.py -q
python -m pytest tests/ -q                      # full suite; runs the sweep as well
python scripts/tenant_isolation_matrix.py --sweep sqlite --out /tmp/sweep.json
```

Each fix can be reverted on its own (`git revert <sha>`) to see its tests
fail; the mutation checks in section 6.4 were done that way.

**Questions for the reviewer**

1. Is the rule right? In particular: refusing a named foreign tenant instead
   of ignoring it, and refusing a user with several memberships who names none.
2. Are the two unchanged caller classes acceptable until PA-1 is decided? The
   platform administrator can still read and write any tenant by header.
3. `resolve_tenant` now authenticates the caller itself. Is there any caller
   that relied on it not doing so? None was found among the 181 routes.
4. Search for the patterns this batch did **not** remove:
   `get_request_tenant_id(request)` (AW-03),
   `or "default-tenant"` (AW-06N), and any handler that calls a function
   operating on all tenants (AW-12 pattern).
5. For AW-13: are counts of participating organisations acceptable to return,
   given the network's minimum group size?
6. Confirm the four governance decisions with their owners, or change them.
7. Carry out, or commission, the historical access investigation.

**What a reviewer should not conclude from this package.** That the 186
remaining routes are the only ones with a finding; that the dedicated tests
are independent evidence; or that any of this has been exercised against a
deployed system. Nothing was deployed.

---

## 11. Verification

Recorded in the PR description for the commit that contains this document,
because a document cannot name its own commit.
