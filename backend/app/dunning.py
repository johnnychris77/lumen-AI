from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record_payment_event(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    event_type: str,
    status: str,
    amount_cents: int,
    billing_month: str,
    notes: str = "",
):
    row = models.PaymentEvent(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        event_type=event_type,
        status=status,
        amount_cents=amount_cents,
        billing_month=billing_month,
        notes=notes[:2000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_active_subscription(db: Session, tenant_id: str):
    return (
        db.query(models.TenantSubscription)
        .filter(models.TenantSubscription.tenant_id == tenant_id)
        .order_by(models.TenantSubscription.id.desc())
        .first()
    )


def mark_payment_failed(db: Session, tenant_id: str, notes: str = "") -> dict:
    sub = get_active_subscription(db, tenant_id)
    if not sub:
        raise ValueError("No subscription found")

    sub.last_payment_status = "failed"
    sub.dunning_status = "past_due"
    sub.suspension_status = "warning"
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return {
        "tenant_id": sub.tenant_id,
        "tenant_name": sub.tenant_name,
        "plan_name": sub.plan_name,
        "last_payment_status": sub.last_payment_status,
        "dunning_status": sub.dunning_status,
        "suspension_status": sub.suspension_status,
        "current_period_end": sub.current_period_end.isoformat(),
        "notes": notes,
    }


def mark_payment_success(db: Session, tenant_id: str, notes: str = "") -> dict:
    sub = get_active_subscription(db, tenant_id)
    if not sub:
        raise ValueError("No subscription found")

    sub.last_payment_status = "current"
    sub.dunning_status = "none"
    sub.suspension_status = "active"
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return {
        "tenant_id": sub.tenant_id,
        "tenant_name": sub.tenant_name,
        "plan_name": sub.plan_name,
        "last_payment_status": sub.last_payment_status,
        "dunning_status": sub.dunning_status,
        "suspension_status": sub.suspension_status,
        "current_period_end": sub.current_period_end.isoformat(),
        "notes": notes,
    }


def suspend_if_past_due(db: Session, tenant_id: str, grace_days: int = 7) -> dict:
    sub = get_active_subscription(db, tenant_id)
    if not sub:
        raise ValueError("No subscription found")

    due = sub.current_period_end + timedelta(days=grace_days)
    should_suspend = _now() > due and sub.last_payment_status == "failed"

    if should_suspend:
        sub.status = "suspended"
        sub.suspension_status = "suspended"
        sub.dunning_status = "final_notice"
        db.add(sub)
        db.commit()
        db.refresh(sub)

    return {
        "tenant_id": sub.tenant_id,
        "tenant_name": sub.tenant_name,
        "status": sub.status,
        "last_payment_status": sub.last_payment_status,
        "dunning_status": sub.dunning_status,
        "suspension_status": sub.suspension_status,
        "current_period_end": sub.current_period_end.isoformat(),
        "grace_days": grace_days,
        "suspended": should_suspend,
    }


def renewal_health_summary(db: Session, tenant_id: str) -> dict:
    sub = get_active_subscription(db, tenant_id)
    if not sub:
        return {}

    days_to_renewal = (sub.current_period_end - _now()).days
    return {
        "tenant_id": sub.tenant_id,
        "tenant_name": sub.tenant_name,
        "plan_name": sub.plan_name,
        "status": sub.status,
        "last_payment_status": sub.last_payment_status,
        "dunning_status": sub.dunning_status,
        "suspension_status": sub.suspension_status,
        "current_period_end": sub.current_period_end.isoformat(),
        "days_to_renewal": days_to_renewal,
    }
