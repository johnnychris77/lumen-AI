from __future__ import annotations

from typing import Any

from fastapi import Request

from app.auth.context import AuthContext, build_dev_auth_context, role_to_permissions


def get_current_user(request: Request) -> dict[str, Any]:
    """
    Backward-compatible MVP helper.

    Legacy routes may import `get_current_user` from `app.auth`.
    Keep this FastAPI-compatible: request must be typed as Request, not Request | None.
    """
    actor = (
        request.headers.get("x-lumenai-actor")
        or request.headers.get("x-lumenai-user-email")
        or request.headers.get("x-user-email")
        or "unknown"
    )

    role = request.headers.get("x-lumenai-role") or "viewer"

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

    return {
        "email": actor,
        "actor": actor,
        "role": role,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
    }


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
