"""P14: Stripe billing webhook handler."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
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
    """Stripe webhook endpoint — no auth header (Stripe signs the request)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # SEC-C-01 (LPR-DIR-022): fail CLOSED. An unsigned or unverifiable billing
    # event must never mutate subscription state — a missing signing secret is a
    # rejection, not a bypass, and a bad signature is a hard 400 (not a silent
    # 200). Only after the signature verifies do we trust the (Stripe-signed)
    # payload metadata for the tenant binding.
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Billing webhook not configured (no signing secret).",
        )
    if not sig_header or not _verify_stripe_signature(payload, sig_header, secret):
        logger.warning("Stripe signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        event = json.loads(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})
    # Trustworthy: the payload is Stripe-signature-verified above.
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
