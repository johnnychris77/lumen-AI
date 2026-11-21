from __future__ import annotations

from fastapi import Depends, HTTPException, Request
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
    from app.deps import _decode_jwt, dev_token_role

    auth_header = (
        request.headers.get("authorization")
        or request.headers.get("Authorization")
        or ""
    )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = auth_header.split(" ", 1)[1].strip()

    # Dev token path (only active when ENABLE_DEV_AUTH=true and not in production)
    role = dev_token_role(token)
    if role is not None:
        return f"{role}@local.dev"

    # JWT path
    payload = _decode_jwt(token)
    if payload and payload.get("sub"):
        return str(payload["sub"])

    raise HTTPException(status_code=401, detail="Invalid or expired token")


def _membership_tenant(db: Session, request: Request, user_email: str) -> str:
    """The tenant a ``require_tenant_roles`` caller acts in (P472-03 batch 4).

    * A tenant named in EITHER header is the explicit selection; membership is
      asserted on it by the caller of this function. Two headers that disagree
      are refused (403) — previously ``X-LumenAI-Tenant-Id`` won and a
      disagreeing ``X-Tenant-Id`` was silently ignored.
    * With no tenant named, the caller acts in their SOLE enabled membership.
      Previously they were placed in a shared ``default-tenant`` (AW-06M), which
      refused every member who did not happen to belong to it and pooled every
      member who did.
    * No membership, or several with none selected: refused (403). Nothing is
      served from a shared default.
    """
    from app.auth.tenant_scope import NO_VERIFIED_TENANT_DETAIL, named_tenant

    named = named_tenant(request)
    if named:
        return named
    if not user_email:
        raise HTTPException(status_code=403, detail="Unable to resolve current user email for tenant authorization.")
    memberships = (
        db.query(models.TenantMembership.tenant_id)
        .filter(models.TenantMembership.user_email == user_email, models.TenantMembership.is_enabled)
        .distinct()
        .all()
    )
    if len(memberships) == 1:
        return memberships[0][0]
    raise HTTPException(status_code=403, detail=NO_VERIFIED_TENANT_DETAIL)


def require_tenant_roles(*allowed_roles: str):
    """
    FastAPI dependency factory for tenant-scoped role enforcement.

    Identity is sourced from the validated bearer token — never from
    caller-controlled request headers.
    """
    from app.deps import get_db

    allowed = {role for role in allowed_roles if role}

    def _dependency(
        request: Request,
        db: Session = Depends(get_db),
    ) -> dict:
        # Resolve identity from the bearer token (raises 401 if invalid)
        user_email = _resolve_user_email_from_token(request)

        tenant_id = _membership_tenant(db, request, user_email)

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
