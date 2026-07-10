# Project Genesis — Identity

LumenAI OS v4.0 — Section 1 (Identity, RBAC)

## Four parallel authz systems, unified read-only

Before this sprint, this codebase had four independent role/permission
systems, each declaring its own ad hoc role strings with no shared enum
(confirmed explicitly in `app/services/atlas_rbac_service.py`'s own
header comment):

| System | Role source |
|---|---|
| `app/authz.py::require_roles` | Dev bearer-token map (`app/deps.py::_DEV_ROLE_MAP`) — `admin`, `spd_manager`, `operator`, `vendor_user`, `viewer` |
| `app/enterprise_auth.py` | `require_enterprise_role`, `require_vendor`, etc. |
| `app/auth/context.py::role_to_permissions` | `enterprise_admin`, `hospital_admin`, `vendor`, `viewer` → permission tuples |
| Atlas RBAC (`app/services/atlas_rbac_service.py`) | `EnterpriseRoleAssignment.ENTERPRISE_ROLES` — `regional_administrator`, `market_director`, `facility_director`, `spd_manager`, `supervisor`, `technician`, `viewer` |

`platform_identity_service.py` does not replace any of these — every
existing `require_roles(...)`/`require_enterprise_role(...)` call site in
this codebase keeps working exactly as it did before this sprint. It adds
a read-only **union**: `CANONICAL_ROLE_CATALOG` is the sorted set of
every role string across all four systems, and `resolve_permissions(role)`
delegates directly to the existing `role_to_permissions()` — Genesis
introduces no second permission table.

## Endpoints

```
GET /api/platform/identity/me     — the caller's own identity summary (actor, role, tenant, known-role flag, permissions)
GET /api/platform/identity/roles  — the full canonical role catalog
```

## Where this is used

`platform_navigation_service.visible_modules` intersects a module's
`PlatformModule.permissions_json` against the caller's role from this
same identity surface — "Users see only applications licensed and
permitted for their role" (Section 4) is enforced by combining licensing
(Section 1) and this identity resolution, not by either alone.
