from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models
from app.services.tenant_bootstrap import bootstrap_tenant

router = APIRouter(tags=["tenant-onboarding"])


class TenantBootstrapPayload(BaseModel):
    tenant_id: str
    tenant_name: str
    admin_email: str
    default_slack_recipient: str = ""
    default_email_recipient: str = ""
    notes: str = ""


def _response(row: models.TenantOnboarding) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "admin_email": row.admin_email,
        "status": row.status,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/tenant-onboarding/bootstrap")
def tenant_bootstrap_route(
    payload: TenantBootstrapPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    result = bootstrap_tenant(
        db,
        tenant_id=payload.tenant_id,
        tenant_name=payload.tenant_name,
        admin_email=payload.admin_email,
        default_slack_recipient=payload.default_slack_recipient,
        default_email_recipient=payload.default_email_recipient,
        notes=payload.notes,
    )

    actor_email = getattr(current_user, "email", None) or getattr(current_user, "username", None) or "unknown"
    log_audit_event(
        db,
        tenant_id=payload.tenant_id,
        tenant_name=payload.tenant_name,
        actor_email=actor_email,
        actor_role="admin",
        action_type="tenant_bootstrap",
        resource_type="tenant_onboarding",
        request=request,
        details=result,
        compliance_flag=True,
    )

    return result


@router.get("/tenant-onboarding/history")
def tenant_onboarding_history(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    rows = db.query(models.TenantOnboarding).order_by(models.TenantOnboarding.id.desc()).limit(200).all()
    return {"items": [_response(r) for r in rows]}
