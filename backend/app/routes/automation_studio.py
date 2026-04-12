from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.automation_engine import process_trigger
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["automation-studio"])


class AutomationRulePayload(BaseModel):
    name: str
    trigger_type: str
    condition: dict = {}
    action_type: str
    action: dict = {}
    is_enabled: bool = True
    notes: str = ""


class AutomationTestPayload(BaseModel):
    trigger_type: str
    payload: dict


def _rule_row(row: models.AutomationRule) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "name": row.name,
        "trigger_type": row.trigger_type,
        "condition_json": row.condition_json,
        "action_type": row.action_type,
        "action_json": row.action_json,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _run_row(row: models.AutomationRun) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "rule_id": row.rule_id,
        "trigger_type": row.trigger_type,
        "action_type": row.action_type,
        "status": row.status,
        "input_json": row.input_json,
        "result_json": row.result_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/automation-rules")
def list_rules(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.AutomationRule)
        .filter(models.AutomationRule.tenant_id == tenant["tenant_id"])
        .order_by(models.AutomationRule.id.desc())
        .all()
    )
    return {"items": [_rule_row(r) for r in rows]}


@router.post("/automation-rules")
def create_rule(
    payload: AutomationRulePayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.AutomationRule(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        name=payload.name,
        trigger_type=payload.trigger_type,
        condition_json=json.dumps(payload.condition)[:4000],
        action_type=payload.action_type,
        action_json=json.dumps(payload.action)[:4000],
        is_enabled=payload.is_enabled,
        notes=payload.notes,
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
        action_type="automation_rule_create",
        resource_type="automation_rule",
        resource_id=row.id,
        request=request,
        details=_rule_row(row),
        compliance_flag=True,
    )

    return {"item": _rule_row(row)}


@router.get("/automation-runs")
def list_runs(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.AutomationRun)
        .filter(models.AutomationRun.tenant_id == tenant["tenant_id"])
        .order_by(models.AutomationRun.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_run_row(r) for r in rows]}


@router.post("/automation-rules/test")
def test_rules(
    payload: AutomationTestPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    result = process_trigger(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type=payload.trigger_type,
        payload=payload.payload,
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="automation_rule_test",
        resource_type="automation_rule",
        request=request,
        details=result,
        compliance_flag=True,
    )

    return result
