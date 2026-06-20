from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.billing import build_invoice_preview, get_plan, persist_invoice_preview
from app.enterprise_auth import require_enterprise_auth
from app.event_dispatcher import dispatch_event
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["billing"])

# ────────────────────────────────────────────────────────────────────────────────
# Stripe Checkout routes
# ────────────────────────────────────────────────────────────────────────────────

STRIPE_PRICE_IDS = {
    "professional": os.environ.get("STRIPE_PRICE_PROFESSIONAL", "price_professional_placeholder"),
    "enterprise": os.environ.get("STRIPE_PRICE_ENTERPRISE", "price_enterprise_placeholder"),
}

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


class CheckoutRequest(BaseModel):
    tenant_id: str
    target_tier: str  # "professional" | "enterprise"
    success_url: str = "/billing/success"
    cancel_url: str = "/billing/upgrade"


@router.post("/billing/checkout")
def create_checkout(req: CheckoutRequest, request: Request, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    if req.target_tier not in STRIPE_PRICE_IDS:
        raise HTTPException(400, detail="Invalid tier")

    if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY.startswith("sk_test_placeholder"):
        return {
            "status": "sandbox",
            "message": "Set STRIPE_SECRET_KEY to enable live checkout",
            "checkout_url": None,
            "tenant_id": req.tenant_id,
            "target_tier": req.target_tier,
        }

    try:
        import stripe  # type: ignore[import]
        stripe.api_key = STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_IDS[req.target_tier], "quantity": 1}],
            metadata={"tenant_id": req.tenant_id, "target_tier": req.target_tier},
            success_url=req.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=req.cancel_url,
        )
        return {"status": "ok", "checkout_url": session.url, "session_id": session.id}
    except ImportError:
        return {
            "status": "sandbox",
            "message": "stripe package not installed. Run: pip install stripe",
            "checkout_url": None,
        }
    except Exception as exc:
        raise HTTPException(500, detail=str(exc))


@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe sends events here. Verifies signature and updates tenant tier."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not STRIPE_SECRET_KEY:
        raise HTTPException(400, detail="Stripe not configured")

    try:
        import stripe  # type: ignore[import]
        stripe.api_key = STRIPE_SECRET_KEY
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload)
    except Exception as exc:
        raise HTTPException(400, detail=f"Webhook error: {exc}")

    event_type = event.get("type", "")

    if event_type in ("checkout.session.completed", "customer.subscription.updated"):
        data = event.get("data", {}).get("object", {})
        metadata = data.get("metadata", {})
        tenant_id = metadata.get("tenant_id", "")
        target_tier = metadata.get("target_tier", "")
        if tenant_id and target_tier:
            _upgrade_tenant_tier(tenant_id, target_tier, db)

    elif event_type == "customer.subscription.deleted":
        data = event.get("data", {}).get("object", {})
        metadata = data.get("metadata", {})
        tenant_id = metadata.get("tenant_id", "")
        if tenant_id:
            _downgrade_tenant_tier(tenant_id, "standard", db)

    return {"received": True}


def _upgrade_tenant_tier(tenant_id: str, tier: str, db: Session) -> None:
    from app.models.tenant_plan import TenantPlan
    from app.models.payment_event import PaymentEvent

    plan = db.query(TenantPlan).filter_by(tenant_id=tenant_id).first()
    if plan:
        plan.data_tier = tier
        plan.plan_name = tier
    else:
        db.add(TenantPlan(
            tenant_id=tenant_id,
            tenant_name=tenant_id,
            plan_name=tier,
            data_tier=tier,
        ))

    db.add(PaymentEvent(
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        event_type="tier_upgrade",
        status="completed",
        amount_cents=0,
        billing_month=datetime.now(timezone.utc).strftime("%Y-%m"),
        notes=f"Upgraded to {tier} via Stripe webhook",
    ))
    db.commit()


def _downgrade_tenant_tier(tenant_id: str, tier: str, db: Session) -> None:
    from app.models.tenant_plan import TenantPlan
    plan = db.query(TenantPlan).filter_by(tenant_id=tenant_id).first()
    if plan:
        plan.data_tier = tier
        plan.plan_name = tier
        db.commit()


@router.get("/billing/status")
def billing_status(tenant_id: str, request: Request, db: Session = Depends(get_db)):
    require_enterprise_auth(request)
    from app.tier_guard import get_tenant_tier, TIER_FEATURES
    from app.models.tenant_plan import TenantPlan

    tier = get_tenant_tier(tenant_id, db)
    plan = db.query(TenantPlan).filter_by(tenant_id=tenant_id).first()

    return {
        "tenant_id": tenant_id,
        "current_tier": tier,
        "features_included": sorted(TIER_FEATURES.get(tier, set())),
        "plan_name": plan.plan_name if plan else "unassigned",
        "monthly_price_cents": plan.monthly_price_cents if plan else 0,
        "stripe_configured": bool(STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith("sk_test_placeholder")),
    }


@router.post("/billing/upgrade")
def upgrade(req: CheckoutRequest, request: Request, db: Session = Depends(get_db)):
    return create_checkout(req, request, db)


class TenantPlanPayload(BaseModel):
    plan_name: str = "starter"
    monthly_price_cents: int = 0
    included_inspections: int = 100
    included_evidence_exports: int = 10
    included_trust_center_exports: int = 10
    overage_inspection_cents: int = 5
    overage_evidence_export_cents: int = 25
    overage_trust_center_export_cents: int = 10


def _plan_response(row: models.TenantPlan) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "plan_name": row.plan_name,
        "monthly_price_cents": row.monthly_price_cents,
        "included_inspections": row.included_inspections,
        "included_evidence_exports": row.included_evidence_exports,
        "included_trust_center_exports": row.included_trust_center_exports,
        "overage_inspection_cents": row.overage_inspection_cents,
        "overage_evidence_export_cents": row.overage_evidence_export_cents,
        "overage_trust_center_export_cents": row.overage_trust_center_export_cents,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/billing/plan")
def set_tenant_plan(
    payload: TenantPlanPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.TenantPlan(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        plan_name=payload.plan_name,
        monthly_price_cents=payload.monthly_price_cents,
        included_inspections=payload.included_inspections,
        included_evidence_exports=payload.included_evidence_exports,
        included_trust_center_exports=payload.included_trust_center_exports,
        overage_inspection_cents=payload.overage_inspection_cents,
        overage_evidence_export_cents=payload.overage_evidence_export_cents,
        overage_trust_center_export_cents=payload.overage_trust_center_export_cents,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="tenant_plan_set",
        resource_type="tenant_plan",
        resource_id=row.id,
        request=request,
        details=_plan_response(row),
        compliance_flag=True,
    )

    return {"item": _plan_response(row)}


@router.get("/billing/plan")
def get_tenant_plan(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return get_plan(db, tenant["tenant_id"], tenant["tenant_name"])


@router.get("/billing/invoice-preview")
def invoice_preview(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return build_invoice_preview(db, tenant["tenant_id"], tenant["tenant_name"])


@router.post("/billing/invoice-preview/persist")
def persist_invoice(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    preview = build_invoice_preview(db, tenant["tenant_id"], tenant["tenant_name"])
    result = persist_invoice_preview(db, preview)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="invoice_preview_persist",
        resource_type="invoice_line_item",
        request=request,
        details=result,
        compliance_flag=True,
    )

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="invoice_persisted",
        payload={
            "billing_month": result["billing_month"],
            "item_count": len(result["items"]),
            "total_cents": result["total_cents"],
        },
    )

    return result
