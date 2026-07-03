from __future__ import annotations

from typing import Any

from fastapi import Request

from app.auth.context import AuthContext, build_dev_auth_context, role_to_permissions


def get_current_user(request: Request) -> dict[str, Any]:
    """
    Backward-compatible helper used by the enterprise/executive routes.

    SECURITY: this previously read identity and role straight from client
    headers and never raised — every route "protected" by it was effectively
    unauthenticated. It now requires a valid bearer token:

      * a dev token from the ENABLE_DEV_AUTH map (non-production only),
      * the demo token when DEMO_MODE=1, or
      * a JWT issued by /auth/login (role resolved server-side from the DB).

    Tenant id/name remain header-supplied *scoping hints* (tenant membership
    is enforced separately by tenant_authz); identity and role never come
    from headers.
    """
    from fastapi import HTTPException

    authorization = (
        request.headers.get("authorization")
        or request.headers.get("Authorization")
        or ""
    )
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    tenant_id = (
        request.headers.get("x-lumenai-tenant-id")
        or request.headers.get("x-tenant-id")
        or "default-tenant"
    )
    tenant_name = (
        request.headers.get("x-lumenai-tenant-name")
        or request.headers.get("x-tenant-name")
        or tenant_id
    )

    # Import lazily to avoid import-time cycles.
    from app.deps import _DEV_AUTH_ACTIVE, _DEV_ROLE_MAP, _decode_jwt

    # Dev token map — only active outside production with ENABLE_DEV_AUTH=true.
    if _DEV_AUTH_ACTIVE and token in _DEV_ROLE_MAP:
        role = _DEV_ROLE_MAP[token]
        actor = f"{role}@local.dev"
        return {
            "email": actor,
            "actor": actor,
            "role": role,
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
        }

    # Demo token — only when DEMO_MODE=1, scoped to the demo tenant and a
    # non-privileged role.
    import os

    if os.getenv("DEMO_MODE", "0").strip() == "1" and token == "demo-token":
        return {
            "email": "demo@lumenai.com",
            "actor": "demo@lumenai.com",
            "role": "viewer",
            "tenant_id": "demo",
            "tenant_name": "Demo Tenant",
        }

    # JWT issued by /auth/login: identity from the validated `sub` claim,
    # role resolved server-side (never from headers).
    payload = _decode_jwt(token)
    if payload and payload.get("sub"):
        username = str(payload["sub"])
        role = "viewer"
        try:
            from app.routers.auth_simple import _user_role

            role = _user_role(username) or "viewer"
        except Exception:
            pass
        return {
            "email": username,
            "actor": username,
            "role": role,
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
        }

    raise HTTPException(status_code=401, detail="Invalid or expired token.")


def get_current_auth_context(request: Request) -> AuthContext:
    user = get_current_user(request)

    return build_dev_auth_context(
        actor=user.get("actor") or user.get("email") or "unknown",
        role=user.get("role") or "viewer",
        tenant_id=user.get("tenant_id") or "default-tenant",
        tenant_name=user.get("tenant_name") or user.get("tenant_id") or "default-tenant",
    )


__all__ = [
    "AuthContext",
    "build_dev_auth_context",
    "role_to_permissions",
    "get_current_user",
    "get_current_auth_context",
]
