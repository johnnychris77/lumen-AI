"""P14: Stripe billing webhook handler."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.deps import get_db

router = APIRouter(prefix="/api/billing", tags=["billing-webhooks"])
logger = logging.getLogger(__name__)


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Verify Stripe webhook signature (simplified HMAC check)."""
    try:
        # Stripe format: t=timestamp,v1=hash,...
        parts = {k: v for k, v in (p.split("=", 1) for p in sig_header.split(",") if "=" in p)}
        timestamp = parts.get("t", "")
        v1 = parts.get("v1", "")
        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, v1)
    except Exception:
        return False


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


@router.post("/webhook")
async def billing_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Stripe webhook endpoint — no auth (Stripe signs the request)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if secret and sig_header:
        if not _verify_stripe_signature(payload, sig_header, secret):
            logger.warning("Stripe signature verification failed")
            # Return 200 anyway to avoid Stripe retries on signature issues in test
            return {"received": True, "warning": "signature_invalid"}

    try:
        event = json.loads(payload)
    except Exception:
        return {"received": True}

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})
    tenant_id = data.get("metadata", {}).get("tenant_id", "unknown")

    logger.info("Stripe webhook received: %s for tenant %s", event_type, tenant_id)

    try:
        if event_type == "invoice.payment_failed":
            sub = _get_or_create_subscription(db, tenant_id)
            sub.subscription_status = "payment_failed"
            sub.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("Tenant %s payment_failed", tenant_id)

        elif event_type == "customer.subscription.deleted":
            sub = _get_or_create_subscription(db, tenant_id)
            sub.subscription_status = "cancelled"
            sub.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("Tenant %s subscription cancelled", tenant_id)

        elif event_type == "customer.subscription.updated":
            plan = data.get("plan", {}).get("nickname", "")
            if plan:
                sub = _get_or_create_subscription(db, tenant_id)
                sub.plan_tier = plan
                sub.updated_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("Tenant %s plan updated to %s", tenant_id, plan)
    except Exception as exc:
        logger.error("Error processing webhook: %s", exc)

    return {"received": True}
