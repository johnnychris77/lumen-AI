from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.dunning import (
    mark_payment_failed,
    mark_payment_success,
    record_payment_event,
    renewal_health_summary,
    suspend_if_past_due,
)
from app.billing import build_invoice_preview, billing_month
from app.event_dispatcher import dispatch_event
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["dunning"])


class PaymentStatusPayload(BaseModel):
    notes: str = ""


@router.post("/dunning/payment-failed")
def payment_failed(
    payload: PaymentStatusPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    preview = build_invoice_preview(db, tenant["tenant_id"], tenant["tenant_name"])
    result = mark_payment_failed(db, tenant["tenant_id"], notes=payload.notes)
    event = record_payment_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        event_type="payment_failed",
        status="failed",
        amount_cents=preview["total_cents"],
        billing_month=preview["billing_month"],
        notes=payload.notes,
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="payment_failed_marked",
        resource_type="payment_event",
        resource_id=event.id,
        request=request,
        details=result,
        compliance_flag=True,
    )

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="payment_failed",
        payload={
            **result,
            "billing_month": preview["billing_month"],
            "amount_cents": preview["total_cents"],
        },
    )

    return result


@router.post("/dunning/payment-succeeded")
def payment_succeeded(
    payload: PaymentStatusPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    preview = build_invoice_preview(db, tenant["tenant_id"], tenant["tenant_name"])
    result = mark_payment_success(db, tenant["tenant_id"], notes=payload.notes)
    event = record_payment_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        event_type="payment_succeeded",
        status="succeeded",
        amount_cents=preview["total_cents"],
        billing_month=preview["billing_month"],
        notes=payload.notes,
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="payment_succeeded_marked",
        resource_type="payment_event",
        resource_id=event.id,
        request=request,
        details=result,
        compliance_flag=True,
    )

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="payment_succeeded",
        payload={
            **result,
            "billing_month": preview["billing_month"],
            "amount_cents": preview["total_cents"],
        },
    )

    return result


@router.post("/dunning/run-suspension-check")
def run_suspension_check(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = suspend_if_past_due(db, tenant["tenant_id"], grace_days=7)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="subscription_suspension_check",
        resource_type="tenant_subscription",
        request=request,
        details=result,
        compliance_flag=True,
    )

    return result


@router.get("/dunning/status")
def dunning_status(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return renewal_health_summary(db, tenant["tenant_id"])
