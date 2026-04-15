from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.implementation_readiness import (
    approve_checkpoint,
    block_item,
    complete_item,
    readiness_summary,
    seed_readiness_items,
)
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["implementation-readiness"])


class ReadinessItemPayload(BaseModel):
    category: str = "setup"
    item_key: str
    title: str
    owner: str = ""
    is_required: bool = True
    notes: str = ""


class ItemCompletePayload(BaseModel):
    notes: str = ""


class ItemBlockPayload(BaseModel):
    blocker_reason: str
    notes: str = ""


class CheckpointPayload(BaseModel):
    checkpoint_key: str
    title: str
    is_required: bool = True


class ApprovalPayload(BaseModel):
    checkpoint_id: int
    approval_notes: str = ""


def _item_row(row: models.ImplementationReadinessItem) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "category": row.category,
        "item_key": row.item_key,
        "title": row.title,
        "owner": row.owner,
        "status": row.status,
        "is_required": row.is_required,
        "blocker_reason": row.blocker_reason,
        "completed_by": row.completed_by,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _checkpoint_row(row: models.GoLiveCheckpoint) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "checkpoint_key": row.checkpoint_key,
        "title": row.title,
        "status": row.status,
        "approved_by": row.approved_by,
        "approved_role": row.approved_role,
        "approval_notes": row.approval_notes,
        "is_required": row.is_required,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
    }


@router.get("/implementation-readiness")
def get_readiness(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return readiness_summary(db, tenant["tenant_id"], tenant["tenant_name"])


@router.post("/implementation-readiness/seed")
def seed_readiness(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    seed_readiness_items(db, tenant["tenant_id"], tenant["tenant_name"])
    result = readiness_summary(db, tenant["tenant_id"], tenant["tenant_name"])

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="implementation_readiness_seed",
        resource_type="implementation_readiness",
        request=request,
        details={"readiness_score": result["readiness_score"]},
        compliance_flag=True,
    )
    return result


@router.post("/implementation-readiness/items")
def create_item(
    payload: ReadinessItemPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.ImplementationReadinessItem(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        category=payload.category,
        item_key=payload.item_key,
        title=payload.title,
        owner=payload.owner,
        status="not_started",
        is_required=payload.is_required,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _item_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="implementation_readiness_item_create",
        resource_type="implementation_readiness_item",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.post("/implementation-readiness/items/{item_id}/complete")
def complete_readiness_item(
    item_id: int,
    payload: ItemCompletePayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    try:
        row = complete_item(db, tenant["tenant_id"], item_id, current_user["user_email"], payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = _item_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="implementation_readiness_item_complete",
        resource_type="implementation_readiness_item",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.post("/implementation-readiness/items/{item_id}/block")
def block_readiness_item(
    item_id: int,
    payload: ItemBlockPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    try:
        row = block_item(db, tenant["tenant_id"], item_id, payload.blocker_reason, payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = _item_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="implementation_readiness_item_block",
        resource_type="implementation_readiness_item",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.get("/go-live-control-center")
def go_live_control_center(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return readiness_summary(db, tenant["tenant_id"], tenant["tenant_name"])


@router.post("/go-live-control-center/checkpoints")
def create_checkpoint(
    payload: CheckpointPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.GoLiveCheckpoint(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        checkpoint_key=payload.checkpoint_key,
        title=payload.title,
        status="pending",
        is_required=payload.is_required,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _checkpoint_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="go_live_checkpoint_create",
        resource_type="go_live_checkpoint",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.post("/go-live-control-center/approve")
def approve_go_live_checkpoint(
    payload: ApprovalPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    try:
        row = approve_checkpoint(
            db,
            tenant["tenant_id"],
            payload.checkpoint_id,
            current_user["user_email"],
            current_user["role_name"],
            payload.approval_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = _checkpoint_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="go_live_checkpoint_approve",
        resource_type="go_live_checkpoint",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}
