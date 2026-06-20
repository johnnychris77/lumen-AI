from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import models


def assert_tenant_membership(
    db: Session,
    *,
    tenant_id: str,
    user_email: str,
) -> bool:
    """
    Enforce tenant boundary access.

    A user is allowed only when:
    - user_email is present
    - tenant_id is present
    - an enabled TenantMembership row exists for that user and tenant
    """

    if not user_email:
        raise HTTPException(
            status_code=403,
            detail="Unable to resolve current user email for tenant authorization.",
        )

    if not tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Unable to resolve tenant for authorization.",
        )

    membership = (
        db.query(models.TenantMembership)
        .filter(
            models.TenantMembership.user_email == user_email,
            models.TenantMembership.tenant_id == tenant_id,
            models.TenantMembership.is_enabled,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="User is not authorized for this tenant.",
        )

    return True


def user_has_tenant_membership(
    db: Session,
    *,
    tenant_id: str,
    user_email: str,
) -> bool:
    try:
        return assert_tenant_membership(
            db,
            tenant_id=tenant_id,
            user_email=user_email,
        )
    except HTTPException:
        return False


def _resolve_user_email_from_token(request) -> str:
    """
    Extract user identity from the validated bearer token.
    Falls back to headers only after token validation, never trusts headers as identity proof.
    """
    from app.deps import _decode_jwt, _DEV_AUTH_ACTIVE, _DEV_ROLE_MAP

    auth_header = (
        request.headers.get("authorization")
        or request.headers.get("Authorization")
        or ""
    )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = auth_header.split(" ", 1)[1].strip()

    # Dev token path (only active when ENABLE_DEV_AUTH=true and not in production)
    if _DEV_AUTH_ACTIVE and token in _DEV_ROLE_MAP:
        role = _DEV_ROLE_MAP[token]
        return f"{role}@local.dev"

    # JWT path
    payload = _decode_jwt(token)
    if payload and payload.get("sub"):
        return str(payload["sub"])

    raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_tenant_roles(*allowed_roles: str):
    """
    FastAPI dependency factory for tenant-scoped role enforcement.

    Identity is sourced from the validated bearer token — never from
    caller-controlled request headers.
    """
    from fastapi import Depends, Request

    from app.deps import get_db

    allowed = {role for role in allowed_roles if role}

    def _dependency(
        request: Request,
        db: Session = Depends(get_db),
    ) -> dict:
        # Resolve identity from the bearer token (raises 401 if invalid)
        user_email = _resolve_user_email_from_token(request)

        tenant_id = (
            request.headers.get("x-lumenai-tenant-id")
            or request.headers.get("x-tenant-id")
            or "default-tenant"
        ).strip() or "default-tenant"

        tenant_name = (
            request.headers.get("x-lumenai-tenant-name")
            or request.headers.get("x-tenant-name")
            or tenant_id
        ).strip() or tenant_id

        tenant = {
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
        }

        assert_tenant_membership(
            db,
            tenant_id=str(tenant_id or ""),
            user_email=user_email,
        )

        membership = (
            db.query(models.TenantMembership)
            .filter(
                models.TenantMembership.user_email == user_email,
                models.TenantMembership.tenant_id == str(tenant_id),
                models.TenantMembership.is_enabled,
            )
            .first()
        )

        if allowed and membership and membership.role not in allowed:
            raise HTTPException(
                status_code=403,
                detail="User does not have the required tenant role.",
            )

        role = membership.role if membership else None
        return {
            "tenant": tenant,
            "tenant_id": tenant_id,
            "user_email": user_email,
            "role": role,
            "role_name": role,  # MED-6: both keys present to satisfy downstream routes
        }

    return _dependency
