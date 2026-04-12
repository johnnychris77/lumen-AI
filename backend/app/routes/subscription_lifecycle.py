from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.event_dispatcher import dispatch_event
from app.subscription_lifecycle import (
    activate_subscription,
    change_subscription_plan,
    get_active_subscription,
    renew_subscription,
)
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["subscription-lifecycle"])


class SubscriptionPlanPayload(BaseModel):
    plan_name: str
    notes: str = ""


def _sub_response(row: models.TenantSubscription | None) -> dict:
    if not row:
        return {}
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "plan_name": row.plan_name,
        "status": row.status,
        "renewal_interval_days": row.renewal_interval_days,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "current_period_start": row.current_period_start.isoformat() if row.current_period_start else None,
        "current_period_end": row.current_period_end.isoformat() if row.current_period_end else None,
        "canceled_at": row.canceled_at.isoformat() if row.canceled_at else None,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/subscription/activate")
def activate_subscription_route(
    payload: SubscriptionPlanPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = activate_subscription(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        plan_name=payload.plan_name,
        actor_email=current_user["user_email"],
        notes=payload.notes,
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="subscription_activate",
        resource_type="tenant_subscription",
        request=request,
        details=result,
        compliance_flag=True,
    )

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="subscription_activated",
        payload=result,
    )

    return result


@router.post("/subscription/upgrade")
def upgrade_subscription_route(
    payload: SubscriptionPlanPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = change_subscription_plan(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        new_plan=payload.plan_name,
        actor_email=current_user["user_email"],
        event_type="upgrade",
        notes=payload.notes,
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="subscription_upgrade",
        resource_type="tenant_subscription",
        request=request,
        details=result,
        compliance_flag=True,
    )

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="subscription_upgraded",
        payload=result,
    )

    return result


@router.post("/subscription/downgrade")
def downgrade_subscription_route(
    payload: SubscriptionPlanPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = change_subscription_plan(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        new_plan=payload.plan_name,
        actor_email=current_user["user_email"],
        event_type="downgrade",
        notes=payload.notes,
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="subscription_downgrade",
        resource_type="tenant_subscription",
        request=request,
        details=result,
        compliance_flag=True,
    )

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="subscription_downgraded",
        payload=result,
    )

    return result


@router.post("/subscription/renew")
def renew_subscription_route(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = renew_subscription(
        db,
        tenant_id=tenant["tenant_id"],
        actor_email=current_user["user_email"],
        notes="Manual renewal",
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="subscription_renew",
        resource_type="tenant_subscription",
        request=request,
        details=result,
        compliance_flag=True,
    )

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="subscription_renewed",
        payload=result,
    )

    return result


@router.get("/subscription/status")
def subscription_status(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = get_active_subscription(db, tenant["tenant_id"])
    return _sub_response(row)


@router.get("/subscription/history")
def subscription_history(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.SubscriptionChangeEvent)
        .filter(models.SubscriptionChangeEvent.tenant_id == tenant["tenant_id"])
        .order_by(models.SubscriptionChangeEvent.id.desc())
        .limit(200)
        .all()
    )

    return {
        "items": [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "tenant_name": row.tenant_name,
                "event_type": row.event_type,
                "previous_plan": row.previous_plan,
                "new_plan": row.new_plan,
                "subscription_status": row.subscription_status,
                "actor_email": row.actor_email,
                "notes": row.notes,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }
