from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.billing import build_invoice_preview
from app.deps import get_db
from app.db import models
from app.dunning import renewal_health_summary
from app.subscription_lifecycle import get_active_subscription
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["finance-console"])


def _subscription_response(row: models.TenantSubscription | None) -> dict:
    if not row:
        return {}
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "plan_name": row.plan_name,
        "status": row.status,
        "renewal_interval_days": row.renewal_interval_days,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "current_period_start": row.current_period_start.isoformat() if row.current_period_start else None,
        "current_period_end": row.current_period_end.isoformat() if row.current_period_end else None,
        "last_payment_status": row.last_payment_status,
        "dunning_status": row.dunning_status,
        "suspension_status": row.suspension_status,
        "notes": row.notes,
    }


@router.get("/finance-console/summary")
def finance_console_summary(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    subscription = get_active_subscription(db, tenant["tenant_id"])
    invoice_preview = build_invoice_preview(db, tenant["tenant_id"], tenant["tenant_name"])
    dunning = renewal_health_summary(db, tenant["tenant_id"])

    invoice_rows = (
        db.query(models.InvoiceLineItem)
        .filter(models.InvoiceLineItem.tenant_id == tenant["tenant_id"])
        .order_by(models.InvoiceLineItem.id.desc())
        .limit(100)
        .all()
    )

    payment_rows = (
        db.query(models.PaymentEvent)
        .filter(models.PaymentEvent.tenant_id == tenant["tenant_id"])
        .order_by(models.PaymentEvent.id.desc())
        .limit(50)
        .all()
    )

    return JSONResponse({
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "subscription": _subscription_response(subscription),
        "invoice_preview": invoice_preview,
        "dunning": dunning,
        "invoice_history": [
            {
                "id": row.id,
                "billing_month": row.billing_month,
                "item_type": row.item_type,
                "quantity": row.quantity,
                "unit_price_cents": row.unit_price_cents,
                "amount_cents": row.amount_cents,
                "notes": row.notes,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in invoice_rows
        ],
        "payment_history": [
            {
                "id": row.id,
                "event_type": row.event_type,
                "status": row.status,
                "amount_cents": row.amount_cents,
                "billing_month": row.billing_month,
                "notes": row.notes,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in payment_rows
        ],
    })
