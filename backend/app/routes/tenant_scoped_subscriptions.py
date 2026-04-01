from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["tenant-scoped-subscriptions"])


class ScopedSubscriptionPayload(BaseModel):
    name: str
    role_scope: str = "executive"
    site_name: str = "all"
    channel: str = "slack"
    recipients: str = ""
    digest_type: str = "weekly"
    is_enabled: bool = True


def _response(row: models.DigestSubscription) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "role_scope": row.role_scope,
        "site_name": row.site_name,
        "channel": row.channel,
        "recipients": row.recipients,
        "digest_type": row.digest_type,
        "is_enabled": row.is_enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/tenant-subscriptions")
def list_tenant_subscriptions(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.DigestSubscription)
        .filter(models.DigestSubscription.site_name.in_(["all", tenant["tenant_id"], tenant["tenant_name"]]))
        .order_by(models.DigestSubscription.id.desc())
        .all()
    )
    return {"items": [_response(r) for r in rows]}


@router.post("/tenant-subscriptions")
def create_tenant_subscription(
    payload: ScopedSubscriptionPayload,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = models.DigestSubscription(
        name=payload.name,
        role_scope=payload.role_scope,
        site_name=payload.site_name if payload.site_name != "all" else tenant["tenant_id"],
        channel=payload.channel,
        recipients=payload.recipients,
        digest_type=payload.digest_type,
        is_enabled=payload.is_enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"item": _response(row)}


@router.post("/tenant-subscriptions/{subscription_id}/toggle")
def toggle_tenant_subscription(
    subscription_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = db.query(models.DigestSubscription).filter(models.DigestSubscription.id == subscription_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Subscription not found")

    row.is_enabled = not bool(row.is_enabled)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"item": _response(row)}
