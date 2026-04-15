from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.governance_sla import run_sla_evaluation, sla_dashboard
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["governance-sla"])


class SlaPolicyPayload(BaseModel):
    policy_key: str
    threshold_hours: int = 24
    escalation_channel: str = ""
    escalation_target: str = ""
    is_enabled: bool = True
    notes: str = ""


def _policy_row(row: models.GovernanceSlaPolicy) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "policy_key": row.policy_key,
        "threshold_hours": row.threshold_hours,
        "escalation_channel": row.escalation_channel,
        "escalation_target": row.escalation_target,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _event_row(row: models.GovernanceSlaEvent) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "policy_key": row.policy_key,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "severity": row.severity,
        "age_hours": row.age_hours,
        "status": row.status,
        "escalation_channel": row.escalation_channel,
        "escalation_target": row.escalation_target,
        "details_json": row.details_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/governance-sla/policies")
def create_policy(
    payload: SlaPolicyPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.GovernanceSlaPolicy(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        policy_key=payload.policy_key,
        threshold_hours=payload.threshold_hours,
        escalation_channel=payload.escalation_channel,
        escalation_target=payload.escalation_target,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _policy_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="governance_sla_policy_create",
        resource_type="governance_sla_policy",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )

    return {"item": result}


@router.get("/governance-sla/policies")
def list_policies(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.GovernanceSlaPolicy)
        .filter(models.GovernanceSlaPolicy.tenant_id == tenant["tenant_id"])
        .order_by(models.GovernanceSlaPolicy.id.desc())
        .all()
    )
    return {"items": [_policy_row(r) for r in rows]}


@router.post("/governance-sla/run")
def run_sla(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    result = run_sla_evaluation(db, tenant["tenant_id"], tenant["tenant_name"])

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="governance_sla_run",
        resource_type="governance_sla",
        request=request,
        details=result,
        compliance_flag=True,
    )

    return result


@router.get("/governance-sla/events")
def list_events(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.GovernanceSlaEvent)
        .filter(models.GovernanceSlaEvent.tenant_id == tenant["tenant_id"])
        .order_by(models.GovernanceSlaEvent.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_event_row(r) for r in rows]}


@router.get("/governance-sla/dashboard")
def dashboard(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return sla_dashboard(db, tenant["tenant_id"], tenant["tenant_name"])
