# GD-1 … GD-4 — Governance decision register (v1)

| | |
|---|---|
| Reviewed commit | `1ff863d` |
| Status | Decision records prepared for the responsible owners. **No approval field is filled.** Every policy is **PENDING**. |

Authoritative narrative: `p472-03-security-governance-decisions.md`. This
document is the **per-policy decision record** the owners complete. An approval
field is populated **only** by an actual authorized decision — never by the
author, and never because a technical control is enforced in code. "Enforced in
code" is engineering evidence; "Approval status" is a policy decision.

---

## GD-1 — Public operational counters require authentication

- **Responsible owner (role):** Product owner, with the security lead.
- **Proposed policy:** operational counters require authentication unless a named
  counter is explicitly approved for public release.
- **Evidence:** enforced in code (`440c0a1`); three counters now 401 to anonymous
  callers; batch-2 tests pin it.
- **Unresolved questions:** are any of the three counters intended to be public?
  If so, which, and under what rate/limit?
- **Conditions:** any public exposure requires explicit written approval naming the
  counter.
- **Decision date:** —  **Approval status:** **PENDING**.

## GD-2 — Privileged cross-tenant audit verification

- **Responsible owner (role):** Security lead, with the compliance / privacy officer.
- **Proposed policy:** cross-tenant audit verification requires an explicitly
  authorized platform-security role, a justified purpose, and tamper-evident
  access logging.
- **Evidence:** fail-closed half enforced (`63bc840`) — verification limited to the
  caller's own tenant; the **authorized cross-tenant path is not built**.
- **Unresolved questions:** who holds the platform-security role? what purpose
  record and log retention are required? Confirm ordinary tenant admins cannot
  obtain unrestricted cross-tenant audit access (currently they cannot — there is
  no cross-tenant path).
- **Conditions:** the authorized path must not ship without the role, purpose and
  immutable logging defined.
- **Decision date:** —  **Approval status:** **PENDING**.

## GD-3 — Vendor / manufacturer baseline ownership

- **Responsible owner (role):** Product owner, with the clinical quality lead and
  the data-governance owner (and IAM owner for the manufacturer category).
- **Proposed policy:** baselines are tenant-private unless an approved sharing
  policy permits access; three categories — (1) tenant-private, (2)
  manufacturer-managed, (3) platform-governed shared.
- **Evidence:** tenant-private **technical control implemented** (`78426ce`,
  `38d1222`); migration validated against representative legacy records (preserved
  + quarantined + reversible). The ownership/sharing model, manufacturer category,
  access-grant table and revocation are **design only**
  (`gd3-vendor-baseline-architecture-decision.md`).
- **Unresolved questions / decisions sought:** ownership model; licensing;
  access-grant mechanism (separate grant table proposed); versioning; revocation;
  legacy attribution procedure (`gd3-quarantine-impact-and-attribution-proposal.md`).
- **Dependency:** the **manufacturer-managed category is BLOCKED by AW-07** —
  `require_manufacturer_auth` accepts any `X-Manufacturer-ID` (confirmed by a
  strict xfail); it is not a verified manufacturer identity.
- **Conditions:** do not implement sharing until (a) the policy is approved and
  (b) AW-07 is remediated; do not deploy the quarantine until the attribution
  procedure is owner-approved.
- **Decision date:** —  **Approval status:** **PENDING** (control implemented;
  policy unapproved).

## GD-4 — Ownerless CAPA records

- **Responsible owner (role):** Quality / regulatory lead, with the data-governance
  owner.
- **Proposed policy:** ownerless CAPAs remain quarantined and non-disclosed until
  ownership is established through verifiable records.
- **Evidence:** enforced since batch 1; pinned by tests (no tenant sees, reads or
  changes an ownerless CAPA; the service has no all-tenants mode).
- **Unresolved questions:** the procedure and evidence standard for attributing a
  legacy CAPA to a tenant (parallels GD-3 §2).
- **Conditions:** no legacy CAPA attribution without verifiable ownership and
  documented approval; ownership never inferred from untrusted metadata.
- **Decision date:** —  **Approval status:** **PENDING**.

---

**No policy above is approved.** Technical controls being enforced in code does
not constitute governance approval or authorize release. HOLD / NO-GO, P472-03
OPEN.
