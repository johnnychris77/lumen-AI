from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.customer_success import (
    ensure_default_playbooks,
    renewal_risk_summary,
    run_renewal_risk,
)
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["customer-success"])


class PlaybookPayload(BaseModel):
    playbook_key: str
    title: str
    trigger_type: str = "health_score"
    trigger_threshold: int = 60
    recommended_actions: list[str] = []
    owner_role: str = "customer_success"
    is_enabled: bool = True
    notes: str = ""


def _playbook_row(row: models.CustomerSuccessPlaybook) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "playbook_key": row.playbook_key,
        "title": row.title,
        "trigger_type": row.trigger_type,
        "trigger_threshold": row.trigger_threshold,
        "recommended_actions_json": row.recommended_actions_json,
        "owner_role": row.owner_role,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/customer-success/playbooks")
def list_playbooks(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    ensure_default_playbooks(db, tenant["tenant_id"], tenant["tenant_name"])
    rows = (
        db.query(models.CustomerSuccessPlaybook)
        .filter(models.CustomerSuccessPlaybook.tenant_id == tenant["tenant_id"])
        .order_by(models.CustomerSuccessPlaybook.id.asc())
        .all()
    )
    return {"items": [_playbook_row(r) for r in rows]}


@router.post("/customer-success/playbooks")
def create_playbook(
    payload: PlaybookPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.CustomerSuccessPlaybook(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        playbook_key=payload.playbook_key,
        title=payload.title,
        trigger_type=payload.trigger_type,
        trigger_threshold=payload.trigger_threshold,
        recommended_actions_json=str(payload.recommended_actions),
        owner_role=payload.owner_role,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _playbook_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="customer_success_playbook_create",
        resource_type="customer_success_playbook",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.get("/customer-success/renewal-risk")
def get_renewal_risk(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return renewal_risk_summary(db, tenant["tenant_id"], tenant["tenant_name"])


@router.post("/customer-success/renewal-risk/run")
def run_renewal_risk_route(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    result = run_renewal_risk(db, tenant["tenant_id"], tenant["tenant_name"])

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="customer_success_renewal_risk_run",
        resource_type="renewal_risk_case",
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.get("/customer-success/recommendations")
def get_customer_success_recommendations(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    summary = renewal_risk_summary(db, tenant["tenant_id"], tenant["tenant_name"])
    return {
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "health_score": summary["health_score"],
        "health_status": summary["health_status"],
        "risk_flags": summary["risk_flags"],
        "open_case_count": summary["open_case_count"],
        "recommendations": summary["recommendations"],
    }
