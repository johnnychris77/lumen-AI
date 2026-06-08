from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import models


def ensure_tenant_membership_table(db: Session) -> None:
    models.TenantMembership.__table__.create(bind=db.get_bind(), checkfirst=True)


def get_enabled_tenant_membership(
    db: Session,
    *,
    tenant_id: str,
    user_email: str,
) -> Any | None:
    ensure_tenant_membership_table(db)

    return (
        db.query(models.TenantMembership)
        .filter(
            models.TenantMembership.tenant_id == tenant_id,
            models.TenantMembership.user_email == user_email,
            models.TenantMembership.is_enabled.is_(True),
        )
        .first()
    )


def require_enabled_tenant_membership(
    db: Session,
    *,
    tenant_id: str,
    user_email: str,
) -> Any:
    membership = get_enabled_tenant_membership(
        db,
        tenant_id=tenant_id,
        user_email=user_email,
    )

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="Enabled tenant membership required.",
        )

    return membership
