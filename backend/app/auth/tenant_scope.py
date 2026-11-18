"""Tenant scope for routes whose request can name a tenant (P472-03).

The tenant a request acts in is ALWAYS the tenant of its verified auth context
(``require_enterprise_auth(request, db=db)``): for a signed user token that is a
tenant the user is an enabled member of — the explicit ``X-Tenant-Id`` header
when one is sent and membership verifies, otherwise the user's sole membership.

A ``tenant_id`` that arrives in a query string or request body is never a
selector. It is only a claim, and a claim that names any other tenant is
refused. It is never rewritten to the caller's own tenant: a request that names
a tenant it may not use fails, it is not silently served from somewhere else.

A user who belongs to several tenants selects one with ``X-Tenant-Id`` (verified
against membership by the auth layer); a ``tenant_id`` claim must then agree.

Usage, inline in a handler so the endpoint-governance scanner sees the auth call::

    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db), tenant_id)
"""
from __future__ import annotations

from fastapi import HTTPException

from app.auth.context import AuthContext

# One message for every refusal, so a response does not reveal whether the named
# tenant exists.
TENANT_DENIED_DETAIL = "Access to the requested tenant is not permitted."


def authorized_tenant(ctx: AuthContext, *claimed_tenant_ids: str | None) -> str:
    """Return the verified tenant of ``ctx``; refuse any claim of another tenant.

    ``claimed_tenant_ids`` are the tenant identifiers the CLIENT sent (query
    parameter, body field). Empty or absent claims are ignored — the request then
    simply acts in the verified tenant. Fails closed with HTTP 403.
    """
    tenant = (getattr(ctx, "tenant_id", "") or "").strip()
    if not tenant:
        raise HTTPException(status_code=403, detail="No verified tenant for this request.")
    for claimed in claimed_tenant_ids:
        if claimed is None:
            continue
        if not isinstance(claimed, str):
            raise HTTPException(status_code=403, detail=TENANT_DENIED_DETAIL)
        if claimed.strip() and claimed.strip() != tenant:
            raise HTTPException(status_code=403, detail=TENANT_DENIED_DETAIL)
    return tenant
