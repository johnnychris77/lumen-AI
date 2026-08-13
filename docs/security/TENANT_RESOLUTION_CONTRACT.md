# Tenant Resolution Contract

The authoritative contract for how LumenAI resolves the tenant a request may act
within. Tenant resolution is a **security boundary** — treat it like authN/authZ.
Executable specification: `backend/tests/test_tenant_resolution_contract.py`.

## Principles

1. **Membership is the only authority.** A request's tenant is authorized solely
   by an enabled `TenantMembership` row for the authenticated user, or by the
   platform-admin flag. Client input (header, query, body, localStorage) may
   *request* a tenant but never *proves* authorization.
2. **Fail closed.** When authorization for a tenant cannot be established, deny
   (`403`) — never fall through to an unscoped query or an assumed tenant.
3. **Errors are visible.** A schema/programming error in membership loading fails
   closed **and is logged** — it must not masquerade as "user has no tenants."

## Cases

Let `verified = principal.verified_tenant_ids()` (enabled memberships) and
`requested` = an optional client-supplied tenant.

| Case | Condition | Expected behavior | HTTP |
|------|-----------|-------------------|------|
| **A** | `is_platform_admin` (`role == "admin"`) | `requested` present → scope to it; else all tenants | 200 |
| **B** | 1 verified tenant, no `requested` | resolve to that tenant | 200 |
| **C** | ≥2 verified tenants, no `requested` | **require explicit selection** — fail closed until one is chosen | 403 |
| **C'** | ≥2 verified, `requested ∈ verified` | scope to `requested` | 200 |
| **D** | 0 verified tenants (non-platform) | fail closed | 403 |
| **E** | `requested ∉ verified` (non-platform) | fail closed | 403 |
| **F** | membership exists but `is_enabled = false` | not loaded → treated as no membership → fail closed | 403 |
| **G** | forged header/query/body tenant | ignored unless it equals a verified membership; otherwise 403 | 403 |

Error body: `{"detail": "No verified tenant membership for this request."}` (Case
C/D) or `"Not a member of the requested tenant."` (Case C'/E/G), per
`resolve_verified_tenant`.

## Platform admin vs tenant admin (current state)

`is_platform_admin == (role == "admin")`. A **global `admin` is a cross-tenant
superadmin** — this is intended for platform operators and is what makes the pilot
admin able to see all tenants. There is currently **no** distinct "tenant admin
who is confined to their own tenant" identity at the role level; the membership
`role` column (`tenant_admin`, `spd_manager`, …) is per-tenant but does not grant
platform scope. Separating these is a documented follow-up — see
`docs/architecture/ADR_TENANT_ADMIN_VS_PLATFORM_ADMIN.md`.

## Client tenant input

- `X-Tenant-Id` / `X-LumenAI-Tenant-Id` headers and any tenant query/body value
  are **requests, not grants**. They are only honored when they match a verified
  membership (Case C'/E/G).
- The enterprise auth path calls `require_enabled_tenant_membership` against the
  header-derived tenant, and `require_enterprise_auth` opens its own DB session so
  the check cannot be skipped by a caller that forgot to thread `db`.

## Non-negotiables

Never, to make a test or route pass: widen access, convert a 403 into a
cross-tenant success, trust a client tenant header, bypass membership
verification, grant tenant admins global access, turn an application error into a
permissive fallback, or treat missing membership as platform access. **When
uncertain, fail closed.**
