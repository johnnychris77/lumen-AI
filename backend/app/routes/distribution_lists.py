from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.distribution_governance import resolve_delivery_target
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["distribution-lists"])


class DistributionListPayload(BaseModel):
    name: str
    audience_type: str = "executive"
    requires_approval: bool = False
    is_enabled: bool = True
    notes: str = ""


class DistributionRecipientPayload(BaseModel):
    recipient_email: str
    recipient_name: str = ""
    recipient_role: str = "stakeholder"
    is_enabled: bool = True
    notes: str = ""


def _list_row(row: models.DistributionList) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "name": row.name,
        "audience_type": row.audience_type,
        "requires_approval": row.requires_approval,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _recipient_row(row: models.DistributionRecipient) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "list_id": row.list_id,
        "recipient_email": row.recipient_email,
        "recipient_name": row.recipient_name,
        "recipient_role": row.recipient_role,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/distribution-lists")
def create_distribution_list(
    payload: DistributionListPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.DistributionList(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        name=payload.name,
        audience_type=payload.audience_type,
        requires_approval=payload.requires_approval,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _list_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="distribution_list_create",
        resource_type="distribution_list",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.get("/distribution-lists")
def list_distribution_lists(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.DistributionList)
        .filter(models.DistributionList.tenant_id == tenant["tenant_id"])
        .order_by(models.DistributionList.id.desc())
        .all()
    )
    return {"items": [_list_row(r) for r in rows]}


@router.post("/distribution-lists/{list_id}/recipients")
def add_recipient(
    list_id: int,
    payload: DistributionRecipientPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    dl = (
        db.query(models.DistributionList)
        .filter(
            models.DistributionList.id == list_id,
            models.DistributionList.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not dl:
        raise HTTPException(status_code=404, detail="Distribution list not found")

    row = models.DistributionRecipient(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        list_id=list_id,
        recipient_email=payload.recipient_email,
        recipient_name=payload.recipient_name,
        recipient_role=payload.recipient_role,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _recipient_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="distribution_recipient_add",
        resource_type="distribution_recipient",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.get("/distribution-lists/{list_id}/recipients")
def list_recipients(
    list_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.DistributionRecipient)
        .filter(
            models.DistributionRecipient.tenant_id == tenant["tenant_id"],
            models.DistributionRecipient.list_id == list_id,
        )
        .order_by(models.DistributionRecipient.id.asc())
        .all()
    )
    return {"items": [_recipient_row(r) for r in rows]}


@router.get("/distribution-lists/{list_id}/delivery-preview")
def delivery_preview(
    list_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return resolve_delivery_target(db, tenant["tenant_id"], "", list_id)
