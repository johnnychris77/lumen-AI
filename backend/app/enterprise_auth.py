from fastapi import HTTPException, Request

from app.auth.context import AuthContext, build_dev_auth_context


DEV_TOKEN = "Bearer dev-token"


def get_request_actor(request: Request) -> str:
    return (
        request.headers.get("x-lumenai-actor")
        or request.headers.get("x-lumenai-user-email")
        or request.headers.get("x-user-email")
        or "unknown"
    )


def get_request_role(request: Request) -> str:
    return request.headers.get("x-lumenai-role", "")


def get_request_tenant_id(request: Request) -> str:
    return (
        request.headers.get("x-lumenai-tenant-id")
        or request.headers.get("x-tenant-id")
        or "default-tenant"
    )


def get_request_tenant_name(request: Request) -> str:
    return (
        request.headers.get("x-lumenai-tenant-name")
        or request.headers.get("x-tenant-name")
        or get_request_tenant_id(request)
    )


def get_auth_context(request: Request) -> AuthContext:
    authorization = request.headers.get("authorization", "")

    if authorization != DEV_TOKEN:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return build_dev_auth_context(
        actor=get_request_actor(request),
        role=get_request_role(request),
        tenant_id=get_request_tenant_id(request),
        tenant_name=get_request_tenant_name(request),
    )


def require_enterprise_auth(request: Request) -> AuthContext:
    return get_auth_context(request)


def require_enterprise_role(
    request: Request,
    *,
    allowed_roles: set[str],
    detail: str = "Access denied.",
) -> AuthContext:
    auth_context = require_enterprise_auth(request)

    if not auth_context.has_role(allowed_roles):
        raise HTTPException(status_code=403, detail=detail)

    return auth_context


def require_hospital_or_enterprise_admin(
    request: Request,
    *,
    detail: str = "Hospital or enterprise administrator access required.",
) -> AuthContext:
    return require_enterprise_role(
        request,
        allowed_roles={"hospital_admin", "enterprise_admin"},
        detail=detail,
    )


def require_vendor(
    request: Request,
    *,
    detail: str = "Vendor access required.",
) -> AuthContext:
    return require_enterprise_role(
        request,
        allowed_roles={"vendor"},
        detail=detail,
    )


def require_permission(
    request: Request,
    *,
    permission: str,
    detail: str = "Permission denied.",
) -> AuthContext:
    auth_context = require_enterprise_auth(request)

    if not auth_context.has_permission(permission):
        raise HTTPException(status_code=403, detail=detail)

    return auth_context
