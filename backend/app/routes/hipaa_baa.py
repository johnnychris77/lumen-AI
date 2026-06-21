"""P14: HIPAA BAA tracker routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth

router = APIRouter(prefix="/api/tenant", tags=["hipaa-baa"])


class BAASignRequest(BaseModel):
    hipaa_baa_reference: str = ""


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


@router.post("/hipaa-baa")
def sign_hipaa_baa(
    body: BAASignRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Record HIPAA BAA signature — requires auth."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    sub = _get_or_create_subscription(db, tenant_id)
    sub.hipaa_baa_signed_at = datetime.now(timezone.utc)
    sub.hipaa_baa_reference = body.hipaa_baa_reference
    sub.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "tenant_id": tenant_id,
        "hipaa_baa_signed_at": sub.hipaa_baa_signed_at.isoformat(),
        "hipaa_baa_reference": sub.hipaa_baa_reference,
        "status": "signed",
    }


@router.get("/hipaa-baa")
def get_hipaa_baa(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Get HIPAA BAA status — requires auth."""
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    from app.models.tenant_subscription_p14 import TenantSubscriptionP14
    sub = db.query(TenantSubscriptionP14).filter(
        TenantSubscriptionP14.tenant_id == tenant_id
    ).first()
    if sub is None or sub.hipaa_baa_signed_at is None:
        return {
            "tenant_id": tenant_id,
            "hipaa_baa_signed": False,
            "hipaa_baa_signed_at": None,
            "hipaa_baa_reference": None,
        }
    return {
        "tenant_id": tenant_id,
        "hipaa_baa_signed": True,
        "hipaa_baa_signed_at": sub.hipaa_baa_signed_at.isoformat(),
        "hipaa_baa_reference": sub.hipaa_baa_reference,
    }
