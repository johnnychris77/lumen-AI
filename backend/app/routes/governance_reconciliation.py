from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.services.governance_reconciliation import reconcile_execution, execute_rollback
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["governance-reconciliation"])


def _rollback_response(row: models.GovernanceRollback) -> dict:
    return {
        "id": row.id,
        "approval_id": row.approval_id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "request_type": row.request_type,
        "target_resource": row.target_resource,
        "target_resource_id": row.target_resource_id,
        "before_state": row.before_state,
        "after_state": row.after_state,
        "rollback_status": row.rollback_status,
        "rollback_notes": row.rollback_notes,
        "rolled_back_by": row.rolled_back_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "rolled_back_at": row.rolled_back_at.isoformat() if row.rolled_back_at else None,
    }


@router.get("/governance-rollbacks")
def list_rollbacks(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.GovernanceRollback)
        .filter(models.GovernanceRollback.tenant_id == tenant["tenant_id"])
        .order_by(models.GovernanceRollback.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_rollback_response(r) for r in rows]}


@router.get("/governance-approvals/{approval_id}/reconcile")
def reconcile_governance_approval(
    approval_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
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

    result = reconcile_execution(db, approval=row)
    return JSONResponse({"approval_id": row.id, "reconciliation": result})


@router.post("/governance-rollbacks/{rollback_id}/execute")
def execute_governance_rollback(
    rollback_id: int,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.GovernanceRollback)
        .filter(
            models.GovernanceRollback.id == rollback_id,
            models.GovernanceRollback.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Rollback not found")

    result = execute_rollback(db, rollback=row, actor_email=current_user["user_email"])

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="governance_rollback_execute",
        resource_type="governance_rollback",
        resource_id=row.id,
        request=request,
        details={"rollback": _rollback_response(row), "result": result},
        compliance_flag=True,
    )

    return {"rollback": _rollback_response(row), "result": result}
