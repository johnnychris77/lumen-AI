from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import HTTPException

from app.core.principal import Principal
from app.core.tenant_context import assert_same_tenant


READ_ACTIONS = {"read", "view", "list", "download", "verify"}
WRITE_ACTIONS = {"create", "update", "delete", "approve", "close", "assign"}

TENANT_ADMIN_ROLES = {"system_admin", "customer_admin"}
QUALITY_ROLES = {"system_admin", "customer_admin", "quality_manager"}
AUDITOR_ROLES = {"system_admin", "customer_admin", "auditor"}
VENDOR_ROLES = {"vendor_user"}


@dataclass(frozen=True)
class ProtectedObject:
    object_id: str
    tenant_id: str
    workflow_type: str
    vendor_id: str | None = None
    assigned_user_ids: tuple[str, ...] = ()


def _access_denied() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "error": {
                "code": "ACCESS_DENIED",
                "message": "You do not have permission to access this resource.",
                "status_code": 403,
            }
        },
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found.",
                "status_code": 404,
            }
        },
    )


def require_role(principal: Principal, allowed_roles: Iterable[str]) -> None:
    if not principal.has_any_role(set(allowed_roles)):
        raise _access_denied()


def require_read_only_for_auditor(principal: Principal, action: str) -> None:
    if principal.has_role("auditor") and action in WRITE_ACTIONS:
        raise _access_denied()


def require_vendor_assignment(
    principal: Principal,
    protected_object: ProtectedObject,
    principal_vendor_id: str | None = None,
) -> None:
    if principal.has_role("vendor_user"):
        if not protected_object.vendor_id:
            raise _not_found()

        if principal_vendor_id and principal_vendor_id != protected_object.vendor_id:
            raise _not_found()


def require_object_permission(
    principal: Principal,
    protected_object: ProtectedObject,
    action: str = "read",
    principal_vendor_id: str | None = None,
) -> None:
    assert_same_tenant(protected_object.tenant_id, principal)

    require_read_only_for_auditor(principal, action)

    if principal.has_any_role(TENANT_ADMIN_ROLES):
        return

    if principal.has_role("auditor"):
        if action in READ_ACTIONS and protected_object.workflow_type in {"audit", "evidence", "capa"}:
            return
        raise _access_denied()

    if principal.has_role("quality_manager"):
        if protected_object.workflow_type in {"quality", "inspection", "capa", "evidence"}:
            return
        raise _access_denied()

    if principal.has_role("vendor_user"):
        require_vendor_assignment(principal, protected_object, principal_vendor_id=principal_vendor_id)
        if action in READ_ACTIONS and protected_object.workflow_type in {"vendor", "capa"}:
            return
        raise _access_denied()

    raise _access_denied()
