from __future__ import annotations

from fastapi import Depends, HTTPException

from app.core.jwt_auth import get_current_principal
from app.core.principal import Principal


def require_tenant_context(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if not principal.tenant_id or principal.tenant_id in {"None", "null", ""}:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "TENANT_CONTEXT_REQUIRED",
                    "message": "Tenant context is required to access this resource.",
                    "status_code": 403,
                }
            },
        )

    return principal


def assert_same_tenant(resource_tenant_id: str | None, principal: Principal) -> None:
    if not resource_tenant_id or resource_tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource was not found.",
                    "status_code": 404,
                }
            },
        )


def tenant_filter(principal: Principal) -> dict[str, str]:
    return {"tenant_id": principal.tenant_id}
