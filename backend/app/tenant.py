from __future__ import annotations

from fastapi import Header


def resolve_tenant(
    x_tenant_id: str | None = Header(default=None),
    x_tenant_name: str | None = Header(default=None),
) -> dict:
    tenant_id = (x_tenant_id or "default-tenant").strip() or "default-tenant"
    tenant_name = (x_tenant_name or tenant_id.replace("-", " ").title()).strip() or "Default Tenant"
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
    }
