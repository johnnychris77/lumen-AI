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


def get_user_enabled_memberships(db: Session, *, user_email: str) -> list[Any]:
    ensure_tenant_membership_table(db)
    return (
        db.query(models.TenantMembership)
        .filter(
            models.TenantMembership.user_email == user_email,
            models.TenantMembership.is_enabled.is_(True),
        )
        .all()
    )


def resolve_effective_tenant(
    db: Session,
    *,
    user_email: str,
    requested_tenant_id: str | None,
) -> str | None:
    """Fail-closed tenant resolution from the user's VERIFIED memberships.

    The authenticated user's own tenant context — never a client-supplied header
    on its own — decides which tenant they act in:

    * Honor ``requested_tenant_id`` only when the user is an enabled member of it.
    * Otherwise fall back to the user's sole enabled membership (so a correct
      request works regardless of a wrong/absent/hardcoded tenant header).
    * Otherwise return ``None`` — the caller denies access (fail-closed). A user
      who belongs to no enabled tenant, or to several with no valid explicit
      choice, is never silently granted one.
    """
    if requested_tenant_id and get_enabled_tenant_membership(
        db, tenant_id=requested_tenant_id, user_email=user_email
    ):
        return requested_tenant_id
    memberships = get_user_enabled_memberships(db, user_email=user_email)
    if len(memberships) == 1:
        return memberships[0].tenant_id
    return None
