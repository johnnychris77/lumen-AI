from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.tenant_scope import verified_request_tenant
from app.deps import get_db


def resolve_tenant(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """The verified tenant of the request (P472-03 AW-01, AW-02).

    This dependency used to return the ``X-Tenant-Id`` header as it arrived
    (default ``default-tenant``), with no check. Routes paired it with a guard
    that verified membership against a *different* header, or with a guard that
    checked only a global role, so a caller could read and write another
    tenant's records by naming it.

    It now authenticates the caller and returns the tenant they are a verified
    member of (``app.auth.tenant_scope.principal_tenant``). A named tenant the
    caller is not a member of, or two tenant headers that disagree, is refused
    with 403.

    ``tenant_name`` is a display label derived from the verified tenant id. It
    used to be copied from the ``X-Tenant-Name`` header and was stored in audit
    rows as sent, so a caller chose the name their actions were recorded under.
    """
    tenant_id = verified_request_tenant(request, db)
    tenant_name = tenant_id.replace("-", " ").title().strip() or tenant_id
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
    }
