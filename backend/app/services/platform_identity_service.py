"""v4.0 — LumenAI OS (Project Genesis), Section 1: Platform Core — Identity.

Composes the four pre-existing, independent authz systems this codebase
already has (`app/authz.py::require_roles`, `app/enterprise_auth.py`,
`app/auth/context.py::role_to_permissions`,
`app/services/atlas_rbac_service.py`/`EnterpriseRoleAssignment`'s
`ENTERPRISE_ROLES`) into one read-only canonical role catalog. This
module never replaces any of them — every existing `require_roles(...)`
call site and `role_to_permissions()` caller keeps working exactly as
before; this is a read-only union for the Platform Core's own identity
surface (`GET /api/platform/identity/*`).
"""
from __future__ import annotations

from app.auth.context import role_to_permissions

# Roles seen across the app's four parallel authz systems (dev role map,
# enterprise auth, Atlas RBAC's ENTERPRISE_ROLES) — a read-only union, not
# a new source of truth. Any one of these strings already works with the
# existing `require_roles`/`require_enterprise_role` dependencies.
_DEV_AUTHZ_ROLES = ("admin", "spd_manager", "operator", "vendor_user", "viewer")
_ENTERPRISE_AUTHZ_ROLES = ("enterprise_admin", "hospital_admin", "vendor", "viewer")
_ATLAS_RBAC_ROLES = (
    "regional_administrator", "market_director", "facility_director", "spd_manager", "supervisor", "technician", "viewer",
)

CANONICAL_ROLE_CATALOG = sorted(set(_DEV_AUTHZ_ROLES) | set(_ENTERPRISE_AUTHZ_ROLES) | set(_ATLAS_RBAC_ROLES))


def list_known_roles() -> list[str]:
    return CANONICAL_ROLE_CATALOG


def resolve_permissions(role: str) -> tuple[str, ...]:
    """Delegates to the existing `role_to_permissions` resolver — Genesis
    adds no second permission table. Roles with no entry there (e.g. the
    dev-only `admin`/`spd_manager`/`operator` tokens, which are gated by
    `require_roles(...)` membership rather than a permission list) simply
    resolve to an empty permission tuple here."""
    return role_to_permissions(role)


def identity_summary(actor: str, role: str, tenant_id: str) -> dict:
    return {
        "actor": actor,
        "role": role,
        "tenant_id": tenant_id,
        "known_role": role in CANONICAL_ROLE_CATALOG,
        "permissions": list(resolve_permissions(role)),
    }
