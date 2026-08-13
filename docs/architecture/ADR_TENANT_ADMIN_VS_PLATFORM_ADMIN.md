# ADR: Platform Admin vs Tenant Admin

**Status:** Accepted (documents current contract; role separation deferred).
**Context:** Tenant Resolution Hardening.

## Current contract

`AuthenticatedPrincipal.is_platform_admin` is defined as:

```python
@property
def is_platform_admin(self) -> bool:
    return self.role == "admin"
```

`self.role` is the user's **global** role (from the role-assignment table via
`_user_role`), independent of any per-tenant `TenantMembership.role`. Consequences:

- A user with global role `admin` is a **platform superadmin**: `resolve_verified_tenant`
  grants them all tenants (or any requested tenant), and `require_roles("admin")`
  endpoints (including `POST /api/tenant-admin/memberships` and
  `POST /api/admin/tenants`) accept them and let them target **any** tenant.
- The per-tenant `TenantMembership.role` (e.g. `tenant_admin`) is used for
  tenant-scoped display/authorization but **does not** confer platform scope. A
  `tenant_admin` membership does not make someone a platform admin.

This is **intended** for the current single-operator pilot: the pilot admin
manages everything. It is documented here so it is a deliberate contract, not an
accident.

## Problem with conflation

There is no identity for a **tenant administrator confined to their own tenant** —
someone who can manage users/config within Hospital A but must never reach
Hospital B. Today the only way to grant membership-management ability is the global
`admin` role, which is cross-tenant. For a multi-hospital deployment this is too
coarse.

## Target contract (deferred)

Introduce an explicit **platform admin** signal distinct from the global `admin`
role, e.g. one of:

1. A reserved `platform` tenant membership (member of `platform` ⇒ platform admin), or
2. An env allow-list (`PLATFORM_ADMIN_EMAILS`), or
3. A dedicated `platform_admin` global role.

Then:

- **Platform admin:** administer multiple tenants, provision tenants, view
  platform-wide operational state where authorized.
- **Tenant admin** (`TenantMembership.role == "tenant_admin"`): administer
  users/config **within their verified tenant(s) only**; cannot cross tenant
  boundaries, provision unrelated organizations, or gain global access. The
  tenant-admin management endpoints would scope grants/toggles to the caller's
  `verified_tenant_ids()` (a `_require_manage_scope` guard) — the code is already
  shaped for this in `tenant_admin.py`'s verified-tenant-scoped `list`.

## Decision

Defer the role separation. It requires a schema/identity decision (which of the
three mechanisms) plus a migration and a coordinated update of the
`require_roles("admin")` endpoints, and is **not** required to fix tenant
resolution. Documented here with a concrete design so it can be implemented as a
focused follow-up without re-discovery.

## Consequences

- Short term: global `admin` remains cross-tenant; safe for the single-tenant
  pilot; the tenant-admin API is gated to `admin` and is therefore a
  platform-admin capability (not an escalation for non-admins).
- Do **not** hand the global `admin` role to per-hospital staff in a multi-tenant
  deployment until this ADR is implemented.
