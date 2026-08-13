# Tenant Membership Model

The single authoritative model for tenant membership in LumenAI.

## Location

`app/db/models.py` → `class TenantMembership(Base)` — table `tenant_memberships`.

> A divergent duplicate (`app/models/tenant_membership.py`, columns
> `tenant_name`/`role_name`) was **deleted** in the preceding fix. It was never
> imported and mapped a *different* schema onto the same table name; code written
> against its phantom columns silently broke `_load_tenant_memberships` and 500'd
> the tenant-admin API. There must be **exactly one** membership model.

## Columns

| Column | Type | Notes |
|--------|------|-------|
| `id` | int PK | |
| `tenant_id` | `String(255)`, indexed, not null | The tenant. Not a display name; use as the tenant key. |
| `user_email` | `String(255)`, indexed, not null | The member (lowercased at write time). |
| `role` | `String(100)`, not null, default `viewer` | Per-tenant role (`tenant_admin`, `spd_manager`, `operator`, `viewer`, …). **Not** the platform-admin signal. |
| `is_enabled` | `Boolean`, not null, default `true` | Disabled memberships are treated as absent (fail closed). |
| `created_at` | `DateTime(tz)`, server default now | |
| `tenant_region` | `String(50)`, nullable, default `north_america` | Data-region tag. |

There is **no** `tenant_name` and **no** `role_name` column — code must read
`tenant_id` and `role`.

## Semantics

- **Tenant authority:** an *enabled* row for `(user_email, tenant_id)` authorizes
  that user to act within `tenant_id`. This is the only source of tenant authority
  for a principal (`_load_tenant_memberships` → `verified_tenant_ids()`).
- **Role:** `role` is scoped to the tenant. Global platform-admin is a separate
  concept (`AuthenticatedPrincipal.is_platform_admin == (principal.role == "admin")`,
  where `principal.role` comes from the user's global role assignment, not this
  column).
- **Lifecycle:** created via the startup bootstrap (`ensure_bootstrap_admins`,
  env `BOOTSTRAP_TENANT_ADMINS`), the tenant-admin API
  (`POST /api/tenant-admin/memberships`), tenant provisioning
  (`POST /api/admin/tenants`), and `bootstrap_tenant`. Disabled via the toggle
  endpoint; disabling is the revocation mechanism (no hard delete required).

## Relationships & integrity (observed / recommended)

- Indexed on `tenant_id` and `user_email` individually. **Recommendation:** add a
  composite unique constraint on `(user_email, tenant_id)` to prevent duplicate
  memberships (today `ensure_bootstrap_admins` and the API guard against
  duplicates in code, not at the DB level). See the migration report.
- No FK to a `tenants` table (tenants are string ids, provisioned via
  `TenantOnboarding`). Orphan/duplicate handling is application-level.

## Reading it correctly

```python
rows = (db.query(models.TenantMembership)
          .filter(models.TenantMembership.user_email == email,
                  models.TenantMembership.is_enabled.is_(True))
          .all())
# tenant_id, role  — NOT tenant_name / role_name
```
