from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models

router = APIRouter(tags=["tenant-admin"])


class TenantMembershipPayload(BaseModel):
    user_email: str
    tenant_id: str
    tenant_name: str
    role_name: str = "viewer"
    is_enabled: bool = True


def _membership_response(row: models.TenantMembership) -> dict:
    return {
        "id": row.id,
        "user_email": row.user_email,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "role_name": row.role_name,
        "is_enabled": row.is_enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/tenant-admin/memberships")
def list_tenant_memberships(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    rows = db.query(models.TenantMembership).order_by(models.TenantMembership.id.desc()).all()

    actor_email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "unknown"
    log_audit_event(
        db,
        tenant_id="platform",
        tenant_name="Platform Admin",
        actor_email=actor_email,
        actor_role="admin",
        action_type="tenant_memberships_list",
        resource_type="tenant_membership",
        request=request,
        details={"count": len(rows)},
        compliance_flag=True,
    )

    return {"items": [_membership_response(r) for r in rows]}


@router.post("/tenant-admin/memberships")
def create_tenant_membership(
    payload: TenantMembershipPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    row = models.TenantMembership(
        user_email=payload.user_email.strip().lower(),
        tenant_id=payload.tenant_id.strip(),
        tenant_name=payload.tenant_name.strip(),
        role_name=payload.role_name.strip(),
        is_enabled=payload.is_enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    actor_email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "unknown"
    log_audit_event(
        db,
        tenant_id=payload.tenant_id,
        tenant_name=payload.tenant_name,
        actor_email=actor_email,
        actor_role="admin",
        action_type="tenant_membership_create",
        resource_type="tenant_membership",
        resource_id=row.id,
        request=request,
        details=_membership_response(row),
        compliance_flag=True,
    )

    return {"item": _membership_response(row)}


@router.post("/tenant-admin/memberships/{membership_id}/toggle")
def toggle_tenant_membership(
    membership_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    row = db.query(models.TenantMembership).filter(models.TenantMembership.id == membership_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant membership not found")

    row.is_enabled = not bool(row.is_enabled)
    db.add(row)
    db.commit()
    db.refresh(row)

    actor_email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "unknown"
    log_audit_event(
        db,
        tenant_id=row.tenant_id,
        tenant_name=row.tenant_name,
        actor_email=actor_email,
        actor_role="admin",
        action_type="tenant_membership_toggle",
        resource_type="tenant_membership",
        resource_id=row.id,
        request=request,
        details={"is_enabled": row.is_enabled, "user_email": row.user_email, "role_name": row.role_name},
        compliance_flag=True,
    )

    return {"item": _membership_response(row)}
