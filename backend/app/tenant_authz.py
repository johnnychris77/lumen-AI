from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.authz import get_current_user
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant


def require_tenant_roles(*allowed_roles: str):
    async def dependency(
        current_user=Depends(get_current_user),
        tenant: dict = Depends(resolve_tenant),
        db: Session = Depends(get_db),
    ):
        email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or ""
        email = str(email).strip().lower()

        if not email:
            raise HTTPException(status_code=403, detail="Unable to resolve current user email for tenant authorization.")

        membership = (
            db.query(models.TenantMembership)
            .filter(
                models.TenantMembership.user_email == email,
                models.TenantMembership.tenant_id == tenant["tenant_id"],
                models.TenantMembership.is_enabled == True,
            )
            .first()
        )

        if not membership:
            raise HTTPException(
                status_code=403,
                detail=f"User '{email}' is not authorized for tenant '{tenant['tenant_id']}'."
            )

        if membership.role_name not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Tenant role '{membership.role_name}' is not permitted for this resource."
            )

        return {
            "user_email": email,
            "tenant_id": membership.tenant_id,
            "tenant_name": membership.tenant_name,
            "role_name": membership.role_name,
        }

    return dependency
