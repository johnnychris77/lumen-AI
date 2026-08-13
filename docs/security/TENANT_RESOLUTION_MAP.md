# Tenant Resolution Map

Inventory of every tenant-resolution mechanism in LumenAI and how each behaves,
produced for the Tenant Resolution Hardening effort. Verified against HEAD.

## The two resolution paths

LumenAI has **two** authenticated-request auth surfaces, and they resolve tenant
differently. This is the "implicit behavioral coupling" the migration addresses.

| Path | Entry point | Tenant source | Membership check |
|------|-------------|---------------|------------------|
| **Principal path** | `app.deps.get_current_user` → `AuthenticatedPrincipal` | `resolve_verified_tenant(principal, requested_tenant_id)` in `app/security/tenant_context.py` | From `principal.verified_tenant_ids()` (membership-derived). Fails closed. |
| **Enterprise path** | `app.enterprise_auth.get_auth_context` / `require_enterprise_auth` | `get_request_tenant_id(request)` (header `X-Tenant-Id` / `X-LumenAI-Tenant-Id`, default `default-tenant`) | `require_enabled_tenant_membership(db, tenant_id, user_email)` — verifies the header tenant against a real membership row. |

Both ultimately gate on a **real, enabled `TenantMembership` row**. The enterprise
path already forces a DB session (`require_enterprise_auth`, lines ~314–330) so the
membership check *always* runs — the client header cannot be trusted on its own.

## Core building blocks

| Symbol | Location | Role |
|--------|----------|------|
| `TenantMembership` | `app/db/models.py` | **The** live model. Columns: `id, tenant_id, user_email, role, is_enabled, created_at, tenant_region`. |
| `_load_tenant_memberships` | `app/deps.py` | Loads a principal's enabled memberships. **Was broken** (read phantom `tenant_name`/`role_name` → `except: return ()` → empty for everyone). Now reads the live model. |
| `TenantMembershipView` | `app/security/principal.py` | Frozen view (`tenant_id`, `tenant_name`, `role_name`) carried on the principal. |
| `AuthenticatedPrincipal.is_platform_admin` | `app/security/principal.py` | `== (role == "admin")`. Platform admin ⇒ cross-tenant by design. |
| `AuthenticatedPrincipal.verified_tenant_ids()` | `app/security/principal.py` | `frozenset` from memberships — the only tenant authority. |
| `resolve_verified_tenant` | `app/security/tenant_context.py` | The Principal-path policy. Fails closed on empty/mismatch. |
| `get_request_tenant_id` | `app/enterprise_auth.py` | Reads the client tenant header (default `default-tenant`). Never authoritative alone. |
| `require_enabled_tenant_membership` | `app/auth/tenant_membership.py` | Column query on the live model → 403 if no enabled row. |

## Route families (representative)

`get_request_tenant_id` appears in ~118 route modules; `require_enterprise_auth`
in ~186; `get_current_user` directly in ~3. Representative behavior:

| Family | Module(s) | Tenant source | Platform admin | Failure |
|--------|-----------|---------------|----------------|---------|
| Inspection history | `routes/history.py` | Principal path (`_scoped_rows` → `resolve_verified_tenant`) | all tenants | 403 fail-closed (Directive 002) |
| Inspections | `routes/inspections.py` | `get_current_user` + `get_request_tenant_id` for write-stamp | n/a | 403 viewer / 422 validation |
| Alerts | `routes/alerts.py` | Enterprise/tenant-scoped (see `test_alerts_tenant_isolation`) | all tenants | 403/empty |
| Simulation / scenario | `routes/scenario_analysis.py` | `get_request_tenant_id` (header/default) | header-driven | 404 not-found within tenant |
| Workflow / sentinel / reviewer queues | `routes/workflow_*`, `routes/sentinel_*`, `routes/reviewer_queues.py` | mixed (service-level tenant arg) | header/service | 404 / empty |
| Enterprise (baselines, audit, KPIs) | `routes/atlas_enterprise.py`, `enterprise_*` | Enterprise path + membership check | all tenants | **403 "Enabled tenant membership required"** |
| Tenant administration | `routes/tenant_admin.py` | `require_roles("admin")` + verified-tenant scoping on list | is_platform_admin | 403 |

## Key finding

The routes were **not** the defect. Once `_load_tenant_memberships` reads the live
model, they resolve tenant correctly. The prior 62-test regression came from **test
state pollution** (shared SQLite file DB, dev-email membership rows leaking across
tests), not route logic — see `TENANT_RESOLUTION_MIGRATION_REPORT.md`.
