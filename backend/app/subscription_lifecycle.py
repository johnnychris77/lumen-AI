from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.db import models


PLAN_DEFAULTS = {
    "starter": {
        "monthly_price_cents": 0,
        "included_inspections": 100,
        "included_evidence_exports": 10,
        "included_trust_center_exports": 10,
        "overage_inspection_cents": 5,
        "overage_evidence_export_cents": 25,
        "overage_trust_center_export_cents": 10,
        "renewal_interval_days": 30,
    },
    "growth": {
        "monthly_price_cents": 29900,
        "included_inspections": 1000,
        "included_evidence_exports": 100,
        "included_trust_center_exports": 100,
        "overage_inspection_cents": 3,
        "overage_evidence_export_cents": 15,
        "overage_trust_center_export_cents": 8,
        "renewal_interval_days": 30,
    },
    "enterprise": {
        "monthly_price_cents": 99900,
        "included_inspections": 10000,
        "included_evidence_exports": 1000,
        "included_trust_center_exports": 1000,
        "overage_inspection_cents": 1,
        "overage_evidence_export_cents": 5,
        "overage_trust_center_export_cents": 3,
        "renewal_interval_days": 30,
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_end(start: datetime, days: int) -> datetime:
    return start + timedelta(days=int(days))


def get_active_subscription(db: Session, tenant_id: str) -> models.TenantSubscription | None:
    return (
        db.query(models.TenantSubscription)
        .filter(models.TenantSubscription.tenant_id == tenant_id)
        .order_by(models.TenantSubscription.id.desc())
        .first()
    )


def log_subscription_event(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    event_type: str,
    previous_plan: str,
    new_plan: str,
    subscription_status: str,
    actor_email: str,
    notes: str = "",
):
    row = models.SubscriptionChangeEvent(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        event_type=event_type,
        previous_plan=previous_plan,
        new_plan=new_plan,
        subscription_status=subscription_status,
        actor_email=actor_email,
        notes=notes[:2000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def upsert_plan_from_subscription(db: Session, tenant_id: str, tenant_name: str, plan_name: str):
    spec = PLAN_DEFAULTS.get(plan_name, PLAN_DEFAULTS["starter"])

    row = models.TenantPlan(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        plan_name=plan_name,
        monthly_price_cents=spec["monthly_price_cents"],
        included_inspections=spec["included_inspections"],
        included_evidence_exports=spec["included_evidence_exports"],
        included_trust_center_exports=spec["included_trust_center_exports"],
        overage_inspection_cents=spec["overage_inspection_cents"],
        overage_evidence_export_cents=spec["overage_evidence_export_cents"],
        overage_trust_center_export_cents=spec["overage_trust_center_export_cents"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def activate_subscription(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    plan_name: str,
    actor_email: str,
    notes: str = "",
) -> dict:
    spec = PLAN_DEFAULTS.get(plan_name, PLAN_DEFAULTS["starter"])
    now = _now()

    current = get_active_subscription(db, tenant_id)
    if current and current.status == "active":
        current.status = "superseded"
        db.add(current)
        db.commit()

    sub = models.TenantSubscription(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        plan_name=plan_name,
        status="active",
        renewal_interval_days=spec["renewal_interval_days"],
        started_at=now,
        current_period_start=now,
        current_period_end=_period_end(now, spec["renewal_interval_days"]),
        notes=notes,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    upsert_plan_from_subscription(db, tenant_id, tenant_name, plan_name)
    log_subscription_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        event_type="activate",
        previous_plan=current.plan_name if current else "",
        new_plan=plan_name,
        subscription_status="active",
        actor_email=actor_email,
        notes=notes,
    )

    return {
        "subscription_id": sub.id,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "plan_name": plan_name,
        "status": sub.status,
        "current_period_end": sub.current_period_end.isoformat(),
    }


def change_subscription_plan(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    new_plan: str,
    actor_email: str,
    event_type: str,
    notes: str = "",
) -> dict:
    sub = get_active_subscription(db, tenant_id)
    if not sub:
        return activate_subscription(
            db,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            plan_name=new_plan,
            actor_email=actor_email,
            notes=notes or f"Auto-activated via {event_type}",
        )

    previous_plan = sub.plan_name
    sub.plan_name = new_plan
    db.add(sub)
    db.commit()
    db.refresh(sub)

    upsert_plan_from_subscription(db, tenant_id, tenant_name, new_plan)
    log_subscription_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        event_type=event_type,
        previous_plan=previous_plan,
        new_plan=new_plan,
        subscription_status=sub.status,
        actor_email=actor_email,
        notes=notes,
    )

    return {
        "subscription_id": sub.id,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "previous_plan": previous_plan,
        "new_plan": new_plan,
        "status": sub.status,
        "current_period_end": sub.current_period_end.isoformat(),
    }


def renew_subscription(
    db: Session,
    *,
    tenant_id: str,
    actor_email: str,
    notes: str = "",
) -> dict:
    sub = get_active_subscription(db, tenant_id)
    if not sub:
        raise ValueError("No subscription found")

    start = sub.current_period_end
    end = _period_end(start, sub.renewal_interval_days)
    sub.current_period_start = start
    sub.current_period_end = end
    sub.status = "active"
    db.add(sub)
    db.commit()
    db.refresh(sub)

    log_subscription_event(
        db,
        tenant_id=sub.tenant_id,
        tenant_name=sub.tenant_name,
        event_type="renew",
        previous_plan=sub.plan_name,
        new_plan=sub.plan_name,
        subscription_status=sub.status,
        actor_email=actor_email,
        notes=notes,
    )

    return {
        "subscription_id": sub.id,
        "tenant_id": sub.tenant_id,
        "tenant_name": sub.tenant_name,
        "plan_name": sub.plan_name,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat(),
        "current_period_end": sub.current_period_end.isoformat(),
    }
