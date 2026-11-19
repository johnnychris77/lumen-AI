# P472-03 B5.2 — Manufacturer Membership Lifecycle (AW-07) — Design and Decision Packet (v1)

**Issue #187 · PR #181 (DRAFT) · Routing #6 (IAM reviewer) — UNASSIGNED.** Nothing here is approved.
Implemented: policy-independent, fail-closed plumbing only. **Decision GD-9 (IAM owner): PENDING.**

## 1. State before Batch 5 (`7cead8a`)
* Enforcement (`require_manufacturer_auth`, Batch 3 `e615afd`) binds the manufacturer identity to an enabled
  `ManufacturerMembership`; forged / wrong / absent / multiple-unselected → 403.
* **No code path created, revoked or audited a membership.** Grants and revocations could only be direct
  database edits with no record of who, when or why. Memberships never expired.

## 2. Implemented (commit in this batch; migration `b5a2c7e19d40`)
| Control | Behaviour | Policy-independent because |
|---|---|---|
| Expiry | nullable `expires_at`; in the past → membership counts as none (named or sole-selection) | can only remove access; NULL = unchanged behaviour |
| Revocation | `revoke_manufacturer_membership(db, membership_id, revoked_by, reason)`: disables, records `revoked_at/by/reason`, writes hash-chained audit event `manufacturer_membership.revoked`; idempotent; requires actor + reason; unknown id → error | only reduces access |
| Revocation propagation | enforcement reads the table on every request (no cache) → effective on the next request | — |
| Grant | `grant_manufacturer_membership(...)` **gated closed** (`GRANTS_APPROVED = False`): refuses before validating or writing | — |
| Grant validation (runs only once opened) | role ∈ {`manufacturer_viewer`}; accountable `granted_by`; `grant_reference` required; no self-grant; well-formed ids/email; future expiry; never re-enables or alters an existing row; audit event `manufacturer_membership.granted` | least privilege |
| Audit integrity | ORM refuses to modify an audit row (`AuditImmutabilityError`); a direct DB edit of `revoked_by` is detected by `verify_audit_chain` | — |
| Migration downgrade | refused while any lifecycle column holds data (dropping `expires_at` would re-activate expired memberships); explicit operator override only | prevents fail-open |
| HTTP surface | **none** — no route calls grant/revoke (asserted) | who may call them is GD-9 |

**No backfill / no attribution.** Existing memberships keep NULL provenance; no historical grantor is
inferred (there is no reliable source; guessing would fabricate an audit trail).

## 3. Evidence
`tests/test_p472_03_batch5_manufacturer_iam.py` (24 tests) + existing AW-07 suite (7):
* before: the module failed to collect (no lifecycle service, no expiry/revocation columns);
* after: **31/31 on SQLite and on PostgreSQL 16.15**; Alembic on PG16: single head `b5a2c7e19d40`,
  upgrade/downgrade/upgrade OK, guarded downgrade refused with an expired row present.

## 4. Decisions required — GD-9 (IAM owner; none taken here)
1. **Authority:** which role may grant and which may revoke (platform IAM operator? manufacturer admin for
   its own organization? both with dual control?). Is revocation by the manufacturer itself allowed?
2. **Identity proofing:** how a manufacturer user's identity and organization affiliation are verified before
   a grant (contract record, domain verification, sponsor attestation).
3. **Role catalogue:** whether roles beyond `manufacturer_viewer` exist and what each may do; today the role
   column is **not consulted** by any portal route (all portal routes are read-only).
4. **Tenant/manufacturer linkage:** `require_manufacturer_auth` first runs `require_enterprise_auth`, so a
   manufacturer user also needs a hospital-tenant membership to pass. Should manufacturer principals be a
   separate identity class (no hospital tenant), and which hospital data may a manufacturer see?
5. **Expiry policy:** mandatory maximum lifetime? periodic re-certification?
6. **Approval workflow:** what `grant_reference` must point to (change ticket, signed approval) and who
   verifies it; dual control.
7. **API exposure:** whether grant/revoke get HTTP routes, and with which permission.
8. **Existing memberships:** whether rows inserted before Batch 5 must be re-certified or disabled.

Opening the grant gate is a reviewed code change that cites the signed GD-9 decision.
