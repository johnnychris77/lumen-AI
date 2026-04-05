from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models
from app.notifications.approval_notifications import notify_approval
from app.services.approval_escalation_service import (
    run_approval_escalation_once,
    approval_escalation_scheduler_running,
)
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["approval-notifications"])


def _approval_response(row: models.GovernanceApproval) -> dict:
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
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
    }


@router.get("/approval-notifications/status")
def approval_notifications_status(
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return JSONResponse({
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "enabled": str(os.getenv("LUMENAI_APPROVAL_NOTIFICATIONS_ENABLED", "false")).lower() in {"1", "true", "yes", "on"},
        "channels": os.getenv("LUMENAI_APPROVAL_NOTIFY_CHANNELS", "slack"),
        "escalation_hours": os.getenv("LUMENAI_APPROVAL_ESCALATION_HOURS", "24"),
        "scheduler_running": approval_escalation_scheduler_running(),
    })


@router.post("/approval-notifications/test-latest")
def approval_notifications_test_latest(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.GovernanceApproval)
        .filter(models.GovernanceApproval.tenant_id == tenant["tenant_id"])
        .order_by(models.GovernanceApproval.id.desc())
        .first()
    )
    if not row:
        return JSONResponse({"detail": "No approval requests found for tenant."}, status_code=404)

    return JSONResponse({
        "approval": _approval_response(row),
        "notification": notify_approval(_approval_response(row), mode="new"),
    })


@router.post("/approval-notifications/run-escalation")
def approval_notifications_run_escalation(
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    return JSONResponse(run_approval_escalation_once())
