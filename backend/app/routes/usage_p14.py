"""P14: Usage metering routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth

router = APIRouter(prefix="/api/usage", tags=["usage-metering"])


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _get_or_create_counter(db: Session, tenant_id: str, facility_id: str, month_year: str):
    from app.models.usage import TenantUsageCounter
    counter = db.query(TenantUsageCounter).filter(
        TenantUsageCounter.tenant_id == tenant_id,
        TenantUsageCounter.facility_id == facility_id,
        TenantUsageCounter.month_year == month_year,
    ).first()
    if counter is None:
        counter = TenantUsageCounter(
            tenant_id=tenant_id,
            facility_id=facility_id,
            month_year=month_year,
            inspection_count=0,
            cap=2000,
        )
        db.add(counter)
        db.commit()
        db.refresh(counter)
    return counter


@router.get("/current-month")
def current_month_usage(
    request: Request,
    facility_id: str = "",
    db: Session = Depends(get_db),
) -> dict:
    """Return current month inspection count, cap, remaining, pct_used."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    month_year = _current_month()
    counter = _get_or_create_counter(db, tenant_id, facility_id, month_year)
    remaining = max(0, counter.cap - counter.inspection_count)
    pct_used = round(counter.inspection_count / counter.cap * 100, 1) if counter.cap > 0 else 0.0
    return {
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "month_year": month_year,
        "inspection_count": counter.inspection_count,
        "cap": counter.cap,
        "remaining": remaining,
        "pct_used": pct_used,
    }


@router.post("/increment")
def increment_usage(
    request: Request,
    facility_id: str = "",
    amount: int = 1,
    db: Session = Depends(get_db),
) -> dict:
    """Increment inspection counter for the current month."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    month_year = _current_month()
    counter = _get_or_create_counter(db, tenant_id, facility_id, month_year)
    counter.inspection_count += amount
    counter.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "tenant_id": tenant_id,
        "inspection_count": counter.inspection_count,
        "cap": counter.cap,
        "remaining": max(0, counter.cap - counter.inspection_count),
    }
