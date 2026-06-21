"""P14: GPO contract pricing routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth

router = APIRouter(prefix="/api/billing", tags=["gpo"])


class GPOContractRequest(BaseModel):
    gpo_contract_id: str
    gpo_discount_pct: float = 0.0


def _get_or_create_subscription(db: Session, tenant_id: str):
    from app.models.tenant_subscription_p14 import TenantSubscriptionP14
    sub = db.query(TenantSubscriptionP14).filter(
        TenantSubscriptionP14.tenant_id == tenant_id
    ).first()
    if sub is None:
        sub = TenantSubscriptionP14(tenant_id=tenant_id)
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


@router.post("/gpo-contract")
def set_gpo_contract(
    body: GPOContractRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Set GPO contract info for tenant — requires auth."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    sub = _get_or_create_subscription(db, tenant_id)
    sub.gpo_contract_id = body.gpo_contract_id
    sub.gpo_discount_pct = body.gpo_discount_pct
    sub.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "tenant_id": tenant_id,
        "gpo_contract_id": sub.gpo_contract_id,
        "gpo_discount_pct": sub.gpo_discount_pct,
        "updated_at": sub.updated_at.isoformat(),
    }


@router.get("/gpo-contract")
def get_gpo_contract(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Get GPO contract info for tenant — requires auth."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    from app.models.tenant_subscription_p14 import TenantSubscriptionP14
    sub = db.query(TenantSubscriptionP14).filter(
        TenantSubscriptionP14.tenant_id == tenant_id
    ).first()
    if sub is None:
        return {"tenant_id": tenant_id, "gpo_contract_id": None, "gpo_discount_pct": 0.0}
    return {
        "tenant_id": tenant_id,
        "gpo_contract_id": sub.gpo_contract_id,
        "gpo_discount_pct": sub.gpo_discount_pct,
    }
