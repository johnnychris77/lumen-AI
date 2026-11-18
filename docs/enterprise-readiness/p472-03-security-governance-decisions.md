# P472-03 — Security Governance Decision Register

| | |
|---|---|
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft) |
| Baseline | `48ef45f` (remediation batch 1) |
| Release status | **HOLD / NO-GO** |
| P472-03 status | **Open** |
| Approval status of this register | **Not approved.** Every decision below is recorded as instructed by the workstream owner and is awaiting sign-off by the responsible owner named in it. No signature has been collected. |

This register records four security policies that came out of remediation
batch 1 as open questions, the enforcement each one requires, what was
implemented in batch 2, and what a responsible owner needs to see before
signing. A policy being implemented in code does **not** mean it is approved:
the code takes the fail-closed side of each question so that nothing depends
on a decision that has not been made.

Roles are named, not people. The repository does not say who holds them, and
this document does not guess.

---

## Summary

| ID | Policy | Responsible owner (role) | Enforced in code | Sign-off |
|---|---|---|---|---|
| GD-1 | Public operational counters require authentication unless specifically approved for public release | Product owner, with the security lead | Yes, batch 2 | Pending |
| GD-2 | Cross-tenant audit verification requires an explicitly authorized platform-security role, a justified purpose and tamper-evident access logging | Security lead, with the compliance / privacy officer | Fail-closed half only: verification is limited to the caller's own tenant. The authorized cross-tenant path is **not built** | Pending |
| GD-3 | Vendor baselines are tenant-private unless an approved sharing policy explicitly permits access | Product owner, with the clinical quality lead and the data-governance owner | **Private default enforced** in the draft PR (schema + all reads/approvals/scoring scoped; pre-GD-3 rows quarantined). The sharing-grant mechanism is **not** built (undecided). Deployment precondition: existing baselines are attributed first | Pending |
| GD-4 | Ownerless CAPAs remain quarantined until ownership can be established through verifiable records | Quality / regulatory lead, with the data-governance owner | Yes, since batch 1; pinned by tests | Pending |

---

## GD-1 — Public operational counters

**Policy.** An endpoint that reports operational figures (counts of
participants, signals, instruments, events) requires an authenticated caller.
An endpoint may be public only if it is named in the list of approved public
endpoints with a recorded approval.

**Why it was open.** Batch 1 left three routes unauthenticated because their
own code calls them public: `GET /api/network/participants/count`,
`GET /api/global-intelligence/network-stats` and
`GET /api/infrastructure/platform-stats`. The only recorded policy
(`docs/security/lumenai-protected-endpoint-authentication-test-baseline-v1.md`)
allows six public endpoints and these are not among them.

**Enforcement requirements**

1. The three routes require a verified caller (valid token and an enabled
   tenant membership). They report network-wide totals, so they are not
   partitioned by tenant; authentication is the control.
2. Any route added to the public list needs: the approver's role and date, a
   statement of what the response may contain, and a test that pins the
   response to that content.
3. The application-wide sweep keeps failing the build for any new route that
   answers an anonymous caller and touches tenant tables (already in place).

**Implemented in batch 2.** Requirement 1. After the change the sweep reports
no route under AW-09.

**API contract implications**

| Request | Before | Now |
|---|---|---|
| Any of the three routes, no credentials | 200 with figures | 401 |
| Signed-in user with no tenant membership | 200 | 403 |
| Signed-in member | 200 | 200, same body |

No frontend code calls these routes. An external site or dashboard that reads
them without credentials will stop working; none could be identified from the
repository.

**Exceptions.** None approved. `/api/health` and the five
`/api/public/module-status/*` routes remain public under the existing baseline
document.

**Not decided by this policy.** Two of the three routes return invented
figures when their tables are empty (`participant_count or 47`,
`published_signals or 128`, `registered_instruments or 4800`,
`passport_events_recorded or 142000`). That is a data-integrity defect, not an
access-control one. It is unchanged and is listed in the remaining findings.

**Evidence needed for sign-off**

- The owner's decision on whether any of the three should be public, and if
  so the approved response content.
- CI result for the tests in
  `backend/tests/test_p472_03_governance_policies.py` (GD-1 class).
- Confirmation from whoever operates marketing or partner pages that nothing
  external depends on anonymous access.

---

## GD-2 — Cross-tenant audit verification

**Policy.** Verifying or inspecting audit records of a tenant other than the
caller's own is a platform-security function. It requires all three of: a role
granted explicitly for that purpose, a stated purpose recorded with each use,
and an access log that cannot be altered without detection.

**Why it was open.** Five verification routes in the enterprise quality module
required a hospital or enterprise administrator but were not limited to that
administrator's tenant (batch 1, item R1):

- `GET /api/enterprise/audit/verify-chain` (by resource type and id)
- `GET /api/enterprise/audit/events/export/verify` (by export hash)
- `GET /api/enterprise/audit/events/export/manifest/verify` (by manifest hash)
- `GET /api/enterprise/audit/evidence-bundle/verify` (by bundle hash)
- `GET /api/enterprise/audit/evidence-bundle/verification-summary`

An administrator of one tenant could learn whether another tenant's resource
had audit events, how many, and whether its chain was intact, and could
confirm the existence of another tenant's exports by hash.

**Enforcement requirements**

1. By default every verification route considers only records of the caller's
   verified tenant. Another tenant's record is indistinguishable from one that
   does not exist.
2. A hash chain is verified in full or not at all: a chain that contains
   events outside the caller's tenant is not verified for that caller and the
   refusal says so without revealing the other events.
3. Cross-tenant verification is available only through a separate path that
   (a) requires a role assigned for platform security, not inferred from an
   existing administrator role; (b) refuses a request without a purpose;
   (c) writes a hash-chained audit event naming the actor, the target tenant,
   the purpose and the result **before** returning; and (d) is itself covered
   by negative tests.
4. Requirement 3 must not be built until this policy, the role definition and
   the logging design have been reviewed by someone other than the author.

**Implemented in batch 2.** Requirements 1 and 2. Two audit writers in the
same module were found to leave the tenant unset, which put a `default-tenant`
event into chains and bundles that otherwise belonged to one tenant; both now
record the caller's verified tenant (the second governance-packet export event
and the evidence-bundle generation event). Requirement 3 is **not
implemented, by design**: there is no cross-tenant verification path in the
application after this change. A standing restriction on this workstream
forbids introducing a privileged cross-tenant bypass without a separately
reviewed authorization policy, and this register is that policy in draft, not
its review.

**API contract implications**

| Request | Before | Now |
|---|---|---|
| Verify a chain whose events all belong to the caller's tenant | 200 | 200, same body |
| Verify a chain of another tenant's resource | 200 with `event_count`, `verified`, `broken_event_id` | 200 with the "no audit events found" body (`event_count: 0`), exactly as for a resource that does not exist |
| Verify a chain that mixes the caller's events with events of another or of no tenant | 200 | 403, "requires a platform-security review" |
| Verify an export, manifest or bundle hash recorded by another tenant | 200, found | the route's existing "not found" response |
| Any cross-tenant verification | possible for any administrator | not possible for anyone |

**Exceptions.** None. In particular the platform administrator (global role
`admin`) gets no cross-tenant verification from this change.

**Consequence the owner must accept or change.** Audit events written before
batch 1 by code that did not pass a tenant carry the column default
`default-tenant` or an empty tenant. A resource whose chain contains such
events can no longer be verified by its tenant's administrator (it answers
403). Making those chains verifiable again needs either an attribution
exercise on the old rows (see GD-4 for the same question on CAPAs) or the
platform-security path of requirement 3.

**Evidence needed for sign-off**

- The definition of the platform-security role: who may hold it, who grants
  it, how it is revoked.
- The list of acceptable purposes and where the purpose is recorded.
- The logging design for requirement 3(c) and where the log is retained.
- CI result for the GD-2 tests
  (`backend/tests/test_p472_03_governance_policies.py`).
- A count, from production, of chains that contain events outside their
  owner's tenant (part of the investigation plan,
  `p472-03-historical-access-investigation-plan.md`).

---

## GD-3 — Vendor baselines are tenant-private

**Policy.** A vendor baseline (the reference description and image of an
instrument submitted by a vendor and approved by a hospital) belongs to the
tenant it was submitted to. Another tenant can see or use it only under an
approved sharing policy that names what is shared and with whom.

**Why it was open.** The vendor baseline library
(`enterprise_vendor_baseline_subscriptions`, with its audit table
`vendor_baseline_audit_events`) has no tenant column. It is one library for
every tenant: any authenticated tenant lists it, one hospital administrator's
approval makes a baseline "approved" for all, and baseline comparison scores
one tenant's findings against a baseline another tenant approved (batch 1,
item R2).

**Status: private default enforced in the draft PR; the sharing-grant
mechanism is not built; sign-off and the data-attribution precondition are
pending.** The private-by-default half of the policy is now in code (see the
commit below). The `TestGd3VendorBaselinesAreTenantPrivate` suite in
`test_p472_03_governance_policies.py` replaces the former strict expected
failure and pins the enforced behaviour: a baseline owned by one tenant is not
listed, read, approved, audited or scored by another, and an unattributed
(pre-GD-3) row is visible to none. What is implemented and what is deliberately
deferred:

- **Implemented.** A `tenant_id` column on both tables (one Alembic migration,
  verified up and down on PostgreSQL 16), stamped from the verified tenant of
  the submitting request and never from the body. Every list, approval, match,
  audit-trail read, governance-packet trail, count and the two baseline
  resolution services (`baseline_comparison_scoring_service`,
  `veritas_baseline_resolution_service`) are scoped to the caller's tenant;
  another tenant's baseline id answers exactly as a missing one does. The demo
  seed attributes its rows to `demo-tenant`.
- **Deferred (undecided policy).** The sharing-grant mechanism (requirement 4)
  is **not** built. Until it is, there is no cross-tenant access at all — a
  manufacturer-published baseline meant for every customer cannot yet be shared
  and must be submitted per tenant. Building the grant needs the sharing policy
  decided first.
- **Deployment precondition (fail-closed consequence).** Rows written before
  GD-3 have `tenant_id IS NULL` and are quarantined — visible to no tenant and
  usable by no tenant's scoring, exactly as ownerless CAPAs are under GD-4.
  Shipping this removes every existing baseline from every tenant at once, and
  baseline comparison then reports "no manufacturer baseline" for every finding
  until rows are attributed. That is a change to clinical-quality workflow
  output and **must not ship** before the owner of that workflow has agreed how
  existing rows are attributed (from the submission audit event, the approving
  administrator's membership at the time, or a signed statement from the data
  owner). The PR stays in draft under HOLD / NO-GO for this reason among others.

**Enforcement requirements (for the batch that implements it)**

1. `tenant_id` on `enterprise_vendor_baseline_subscriptions` and
   `vendor_baseline_audit_events`, set from the verified tenant of the
   submitting request; never from the body.
2. Every read, approval, audit-trail and scoring lookup limited to the
   caller's tenant; another tenant's baseline id answers 404.
3. Existing rows quarantined (visible to no tenant) until attributed from
   verifiable records: the submission audit event, the approving
   administrator's membership at the time, or a signed statement from the
   data owner.
4. Sharing, if approved, as an explicit grant (owner tenant, grantee tenant or
   "all", scope, approver, date, revocation) checked on every read, with an
   audit event for each grant, revocation and cross-tenant read.
5. Migration verified up and down on PostgreSQL; tests for every route with
   two tenants that own real baselines.

**API contract implications (when implemented)**

| Request | Now | After |
|---|---|---|
| List the library | every tenant's baselines | the caller's, plus any shared to it |
| Read, approve or audit another tenant's baseline by id | served | 404 |
| Baseline comparison for a finding | may use a baseline approved by another tenant | uses only the caller's or a shared baseline |
| Existing baselines | visible to all | visible to none until attributed |

**Exceptions.** None approved. A manufacturer-published baseline that is meant
to be available to every customer is the obvious candidate for a sharing
grant; that is the policy decision in requirement 4, not an exception to it.

**Evidence needed for sign-off**

- The owner's rule for attributing existing rows, and the count of rows it
  leaves unattributed.
- Whether manufacturer-published baselines are shared to all tenants and who
  approves that.
- Clinical quality lead's acceptance of the effect on baseline comparison
  during the transition.
- For the implementing batch: migration evidence and test results.

---

## GD-4 — Ownerless CAPAs stay quarantined

**Policy.** A corrective and preventive action record with no established
owner tenant is visible to no tenant and cannot be changed through the API. It
is released to a tenant only when ownership is established from records that
can be checked.

**Why it was open.** Before batch 1 the CAPA register had no tenant column.
Batch 1 added one and made every operation require a tenant; rows written
before that have no owner (item R4).

**Enforcement requirements**

1. No API route and no service function returns, counts, exports, advances or
   modifies a CAPA whose tenant is empty.
2. There is no "all tenants" mode in the CAPA services.
3. Attribution is a controlled data operation, not an API feature: performed
   by an authorized operator against a reviewed list, each row justified by a
   verifiable record, with the before and after state retained.
4. Quarantined rows are never deleted by this policy.

**Implemented.** Requirements 1, 2 and 4, since batch 1 (`48ef45f`); batch 2
adds tests that pin them. Requirement 3 is a procedure and is described in the
investigation plan; no attribution has been performed.

**API contract implications.** As recorded for batch 1: CAPAs stored before
`48ef45f` are visible to no tenant. Nothing further changes in batch 2.

**What counts as a verifiable record** (proposed; the owner decides)

- An audit event for the CAPA's creation that names a tenant and an actor who
  was a member of that tenant at the time.
- A link from the CAPA to an inspection, finding or vendor event that itself
  has an owner tenant.
- For a deployment that only ever had one tenant: a signed statement from the
  data owner that all rows belong to it.

A title, a site name or an owner name typed into the record is **not**
sufficient: all three are free text.

**Exceptions.** None.

**Evidence needed for sign-off**

- Count of quarantined rows per deployment (investigation plan, step 6).
- The owner's choice of acceptable records and the name of the role that
  performs attribution.
- CI result for the GD-4 tests.

---

## What signing means

A responsible owner signs a decision by recording, in the change-control
system the organisation uses (not in this file by an automated author): their
name and role, the date, the commit they reviewed, the decision (approve,
approve with changes, reject) and any conditions. Until that exists for a
decision, its status in this register stays "Pending", the related findings
stay open, and the release status stays HOLD / NO-GO.
