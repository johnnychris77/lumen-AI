from fastapi import HTTPException, Request


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


def require_enterprise_auth(request: Request) -> dict:
    authorization = request.headers.get("authorization", "")

    if authorization != DEV_TOKEN:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return {
        "actor": get_request_actor(request),
        "role": get_request_role(request),
    }


def require_enterprise_role(
    request: Request,
    *,
    allowed_roles: set[str],
    detail: str = "Access denied.",
) -> dict:
    auth_context = require_enterprise_auth(request)

    if auth_context["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail=detail)

    return auth_context


def require_hospital_or_enterprise_admin(
    request: Request,
    *,
    detail: str = "Hospital or enterprise administrator access required.",
) -> dict:
    return require_enterprise_role(
        request,
        allowed_roles={"hospital_admin", "enterprise_admin"},
        detail=detail,
    )


def require_vendor(
    request: Request,
    *,
    detail: str = "Vendor access required.",
) -> dict:
    return require_enterprise_role(
        request,
        allowed_roles={"vendor"},
        detail=detail,
    )
