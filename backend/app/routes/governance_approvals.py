from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.notifications.approval_notifications import notify_approval
from app.event_dispatcher import dispatch_event
from app.services.governance_execution import execute_approved_change, mark_execution_result
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["governance-approvals"])


class ApprovalRequestPayload(BaseModel):
    request_type: str
    target_resource: str
    target_resource_id: str = ""
    requested_payload: dict
    justification: str = ""


class ApprovalDecisionPayload(BaseModel):
    review_notes: str = ""


def _response(row: models.GovernanceApproval) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "request_type": row.request_type,
        "target_resource": row.target_resource,
        "target_resource_id": row.target_resource_id,
        "requested_by": row.requested_by,
        "requested_role": row.requested_role,
        "requested_payload": row.requested_payload,
        "status": row.status,
        "reviewed_by": row.reviewed_by,
        "review_notes": row.review_notes,
        "execution_status": row.execution_status,
        "execution_notes": row.execution_notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "executed_at": row.executed_at.isoformat() if row.executed_at else None,
    }


@router.post("/governance-approvals/request")
def create_governance_approval_request(
    payload: ApprovalRequestPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = models.GovernanceApproval(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        request_type=payload.request_type,
        target_resource=payload.target_resource,
        target_resource_id=payload.target_resource_id,
        requested_by=current_user["user_email"],
        requested_role=current_user["role_name"],
        requested_payload=json.dumps({
            "payload": payload.requested_payload,
            "justification": payload.justification,
        })[:4000],
        status="pending",
        execution_status="not_started",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="governance_approval_request_create",
        resource_type="governance_approval",
        resource_id=row.id,
        request=request,
        details=_response(row),
        compliance_flag=True,
    )

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="approval_requested",
        payload={
            "approval_id": row.id,
            "request_type": row.request_type,
            "target_resource": row.target_resource,
            "target_resource_id": row.target_resource_id,
            "requested_by": row.requested_by,
            "status": row.status,
            "requested_payload": row.requested_payload,
            "created_at": row.created_at.isoformat() if row.created_at else "",
        },
    )

    return {"item": _response(row), "notification": notify_approval(_response(row), mode="new")}


@router.get("/governance-approvals/pending")
def list_pending_governance_approvals(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    rows = (
        db.query(models.GovernanceApproval)
        .filter(
            models.GovernanceApproval.tenant_id == tenant["tenant_id"],
            models.GovernanceApproval.status == "pending",
        )
        .order_by(models.GovernanceApproval.id.desc())
        .all()
    )
    return {"items": [_response(r) for r in rows]}


@router.get("/governance-approvals/history")
def list_governance_approvals_history(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.GovernanceApproval)
        .filter(models.GovernanceApproval.tenant_id == tenant["tenant_id"])
        .order_by(models.GovernanceApproval.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_response(r) for r in rows]}


@router.post("/governance-approvals/{approval_id}/approve")
def approve_governance_request(
    approval_id: int,
    payload: ApprovalDecisionPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.GovernanceApproval)
        .filter(
            models.GovernanceApproval.id == approval_id,
            models.GovernanceApproval.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Approval request is not pending")

    if row.requested_by.strip().lower() == current_user["user_email"].strip().lower():
        raise HTTPException(status_code=400, detail="Dual control violation: requester cannot approve their own request")

    row.status = "approved"
    row.reviewed_by = current_user["user_email"]
    row.review_notes = payload.review_notes
    row.reviewed_at = datetime.now(timezone.utc)

    db.add(row)
    db.commit()
    db.refresh(row)

    execution_result = None
    try:
        execution_result = execute_approved_change(db, row)
        row = mark_execution_result(db, row, status="executed", notes=execution_result["message"])
    except Exception as e:
        row = mark_execution_result(db, row, status="failed", notes=str(e))

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="governance_approval_approved",
        resource_type="governance_approval",
        resource_id=row.id,
        request=request,
        details={"approval": _response(row), "execution_result": execution_result},
        compliance_flag=True,
    )

    return {"item": _response(row), "execution_result": execution_result}


@router.post("/governance-approvals/{approval_id}/reject")
def reject_governance_request(
    approval_id: int,
    payload: ApprovalDecisionPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.GovernanceApproval)
        .filter(
            models.GovernanceApproval.id == approval_id,
            models.GovernanceApproval.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Approval request is not pending")

    if row.requested_by.strip().lower() == current_user["user_email"].strip().lower():
        raise HTTPException(status_code=400, detail="Dual control violation: requester cannot reject their own request")

    row.status = "rejected"
    row.reviewed_by = current_user["user_email"]
    row.review_notes = payload.review_notes
    row.reviewed_at = datetime.now(timezone.utc)
    row.execution_status = "not_applicable"

    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="governance_approval_rejected",
        resource_type="governance_approval",
        resource_id=row.id,
        request=request,
        details=_response(row),
        compliance_flag=True,
    )

    return {"item": _response(row)}
