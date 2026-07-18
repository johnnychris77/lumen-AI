# Tenant Security Model (LPZ-DIR-002, Phase 3)

## Trust boundaries

1. **Network → app:** a bearer token. Verified by signature (JWT) or the
   server-side dev-token map (dev only). Nothing else authenticates.
2. **Token → identity:** the typed `AuthenticatedPrincipal`. Role from a
   server-side table; tenant memberships from the `tenant_memberships`
   table. Client identity/tenant headers carry **no** authority.
3. **Identity → tenant scope:** `resolve_verified_tenant(principal,
   requested_tenant_id=...)` → `TenantScope(all_tenants, tenant_id)`.
4. **Scope → data:** repositories/queries receive a `TenantScope`; a
   non-admin scope always carries a concrete `tenant_id`.

## Tenant-selection rules (all fail closed)

* Platform admin (`role == "admin"`): `all_tenants=True` by default; may
  target one tenant explicitly via `requested_tenant_id`.
* Non-admin: confined to `active_tenant_id` when it is a verified
  membership. A `requested_tenant_id` is honored **only** if it is in the
  principal's verified memberships, else **403**.
* No verified tenant → **403**. Never an unfiltered ("all tenants")
  query for a non-admin. `TenantScope.__post_init__` refuses to even
  represent "not all tenants AND no tenant id".

## Membership validation

`tenant_memberships` rows with `is_enabled=True`, matched on the
authenticated `user_email`. Disabled or absent membership = not a member.

## Administrator / portfolio / service-account behavior

* **Administrator** cross-tenant access is **explicit** (`role=="admin"`
  → `all_tenants`), never inferred from missing scope.
* **Portfolio** (multi-tenant non-admin) access is out of scope for this
  increment; such a principal has `active_tenant_id=None` and must select
  a verified tenant per request. No implicit portfolio breadth.
* **Service accounts:** none are introduced here; if added later they
  must carry explicit tenant grants through the same membership model.

## Object-by-ID access

Ownership validation for object-by-ID reads (e.g. a single inspection by
id) is required by the directive and is **not** part of the history
increment (history is a list/export path). It is inventoried per route in
`TENANT_MIGRATION_INVENTORY.md` and DEFERRED.

## Exports

Exports enforce the **same** boundary as interactive views: all
`/history/export.*` endpoints route through `resolve_verified_tenant`,
so an export can never exceed the caller's verified tenant scope. Proven
by `test_directive_002_tenant_context.py`.

## Migration plan

Increment 1 (this PR): principal + resolver + history/exports.
Increment 2+: migrate the ~10 header-fallback routes (see inventory) to
`resolve_verified_tenant`; add object-ownership checks; unify the two
auth paths.

## Security assumptions

* The `tenant_memberships` table is authoritative and admin-managed.
* App JWTs are signed with a secret not shared with clients.
* `role=="admin"` is a genuine platform-admin grant (not tenant-scoped).
