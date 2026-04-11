from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db import models


def month_bounds_utc(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def record_usage_event(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    event_type: str,
    quantity: int = 1,
    resource_id: str = "",
    notes: str = "",
):
    row = models.UsageEvent(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        event_type=event_type,
        quantity=quantity,
        resource_id=str(resource_id or ""),
        notes=notes[:2000],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_monthly_usage(db: Session, *, tenant_id: str, event_type: str) -> int:
    start, end = month_bounds_utc()
    rows = (
        db.query(models.UsageEvent)
        .filter(
            models.UsageEvent.tenant_id == tenant_id,
            models.UsageEvent.event_type == event_type,
            models.UsageEvent.created_at >= start,
            models.UsageEvent.created_at < end,
        )
        .all()
    )
    return sum(int(r.quantity or 0) for r in rows)


def get_quota(db: Session, *, tenant_id: str, tenant_name: str, metric_key: str) -> dict:
    row = (
        db.query(models.TenantQuota)
        .filter(
            models.TenantQuota.tenant_id == tenant_id,
            models.TenantQuota.metric_key == metric_key,
        )
        .order_by(models.TenantQuota.id.desc())
        .first()
    )
    if row:
        return {
            "tenant_id": row.tenant_id,
            "tenant_name": row.tenant_name,
            "metric_key": row.metric_key,
            "monthly_limit": row.monthly_limit,
            "notes": row.notes,
            "source": "configured",
        }

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "metric_key": metric_key,
        "monthly_limit": 0,
        "notes": "",
        "source": "default-unlimited",
    }


def check_quota(db: Session, *, tenant_id: str, tenant_name: str, metric_key: str, requested: int = 1) -> dict:
    quota = get_quota(db, tenant_id=tenant_id, tenant_name=tenant_name, metric_key=metric_key)
    used = get_monthly_usage(db, tenant_id=tenant_id, event_type=metric_key)
    limit = int(quota["monthly_limit"] or 0)

    if limit <= 0:
        return {
            "metric_key": metric_key,
            "used": used,
            "limit": limit,
            "remaining": None,
            "allowed": True,
            "source": quota["source"],
        }

    remaining = max(limit - used, 0)
    allowed = used + requested <= limit

    return {
        "metric_key": metric_key,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "allowed": allowed,
        "source": quota["source"],
    }
