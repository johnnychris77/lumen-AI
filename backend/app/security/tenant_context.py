"""Verified tenant-context resolution (Pilot Zero Directive 002, Phase 3).

Single place that turns an authenticated principal into a tenant the data
layer may safely be scoped to. The rules, all fail-closed:

* A platform admin (``role == "admin"``) may operate across all tenants —
  this is explicit, not inferred from missing scope.
* Any other principal is scoped to a tenant it has a **verified enabled
  membership** for. Membership was resolved from the ``tenant_memberships``
  table at authentication time (never from a header).
* A requested tenant (e.g. via ``X-Tenant-Id``) is only honored when it is
  in the principal's verified memberships; otherwise 403.
* Missing verified tenant context raises 403 — it never degrades to an
  unfiltered ("all tenants") query for a non-admin.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.security.principal import AuthenticatedPrincipal


@dataclass(frozen=True)
class TenantScope:
    """Result of verified resolution.

    ``all_tenants`` is True only for an explicit platform-admin. When it is
    False, ``tenant_id`` is a non-empty, membership-verified string. The two
    states are mutually exclusive, so a data-access layer can never receive
    "not all tenants AND no tenant id".
    """

    all_tenants: bool
    tenant_id: str | None

    def __post_init__(self) -> None:
        if not self.all_tenants and not self.tenant_id:
            # Defensive: this object must never represent an unfiltered
            # non-admin scope.
            raise ValueError("Non-admin TenantScope requires a tenant_id.")


def resolve_verified_tenant(
    principal: AuthenticatedPrincipal,
    *,
    requested_tenant_id: str | None = None,
) -> TenantScope:
    """Resolve the tenant a principal may act within, failing closed.

    ``requested_tenant_id`` may come from a client header but carries no
    authority on its own — it is only accepted when it matches a verified
    membership.
    """
    if principal.is_platform_admin:
        # Admin may target a specific tenant if asked, else all tenants.
        if requested_tenant_id:
            return TenantScope(all_tenants=False, tenant_id=requested_tenant_id)
        return TenantScope(all_tenants=True, tenant_id=None)

    verified = principal.verified_tenant_ids()

    if requested_tenant_id:
        if requested_tenant_id not in verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of the requested tenant.",
            )
        return TenantScope(all_tenants=False, tenant_id=requested_tenant_id)

    if principal.active_tenant_id and principal.active_tenant_id in verified:
        return TenantScope(all_tenants=False, tenant_id=principal.active_tenant_id)

    # No verified tenant context — fail closed. Never fall through to an
    # unfiltered query.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No verified tenant membership for this request.",
    )
