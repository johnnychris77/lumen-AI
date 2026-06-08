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


def require_tenant_roles(*allowed_roles: str):
    """
    FastAPI dependency factory for tenant-scoped role enforcement.

    This preserves compatibility with existing routes that import
    require_tenant_roles while routing authorization through the newer
    tenant membership boundary helper.
    """
    from fastapi import Depends, Request

    from app.deps import get_db

    allowed = {role for role in allowed_roles if role}

    def _dependency(
        request: Request,
        db: Session = Depends(get_db),
    ) -> dict:
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

        user_email = (
            request.headers.get("x-lumenai-user-email")
            or request.headers.get("x-user-email")
            or request.headers.get("x-lumenai-actor")
            or ""
        )

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

        return {
            "tenant": tenant,
            "tenant_id": tenant_id,
            "user_email": user_email,
            "role": membership.role if membership else None,
        }

    return _dependency
