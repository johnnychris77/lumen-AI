from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db import models
from app.metering import get_monthly_usage


DEFAULT_PLAN = {
    "plan_name": "starter",
    "monthly_price_cents": 0,
    "included_inspections": 100,
    "included_evidence_exports": 10,
    "included_trust_center_exports": 10,
    "overage_inspection_cents": 5,
    "overage_evidence_export_cents": 25,
    "overage_trust_center_export_cents": 10,
}


def billing_month(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def get_plan(db: Session, tenant_id: str, tenant_name: str) -> dict:
    row = (
        db.query(models.TenantPlan)
        .filter(models.TenantPlan.tenant_id == tenant_id)
        .order_by(models.TenantPlan.id.desc())
        .first()
    )
    if row:
        return {
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
            "source": "configured",
        }

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        **DEFAULT_PLAN,
        "source": "default",
    }


def build_invoice_preview(db: Session, tenant_id: str, tenant_name: str) -> dict:
    plan = get_plan(db, tenant_id, tenant_name)

    inspections_used = get_monthly_usage(db, tenant_id=tenant_id, event_type="inspection_submitted")
    evidence_used = get_monthly_usage(db, tenant_id=tenant_id, event_type="evidence_pack_exported")
    trust_used = get_monthly_usage(db, tenant_id=tenant_id, event_type="trust_center_exported")

    inspection_overage = max(inspections_used - int(plan["included_inspections"]), 0)
    evidence_overage = max(evidence_used - int(plan["included_evidence_exports"]), 0)
    trust_overage = max(trust_used - int(plan["included_trust_center_exports"]), 0)

    line_items = [
        {
            "item_type": "base_plan",
            "quantity": 1,
            "unit_price_cents": int(plan["monthly_price_cents"]),
            "amount_cents": int(plan["monthly_price_cents"]),
            "notes": plan["plan_name"],
        },
        {
            "item_type": "inspection_overage",
            "quantity": inspection_overage,
            "unit_price_cents": int(plan["overage_inspection_cents"]),
            "amount_cents": inspection_overage * int(plan["overage_inspection_cents"]),
            "notes": f"Used {inspections_used}, included {plan['included_inspections']}",
        },
        {
            "item_type": "evidence_export_overage",
            "quantity": evidence_overage,
            "unit_price_cents": int(plan["overage_evidence_export_cents"]),
            "amount_cents": evidence_overage * int(plan["overage_evidence_export_cents"]),
            "notes": f"Used {evidence_used}, included {plan['included_evidence_exports']}",
        },
        {
            "item_type": "trust_center_export_overage",
            "quantity": trust_overage,
            "unit_price_cents": int(plan["overage_trust_center_export_cents"]),
            "amount_cents": trust_overage * int(plan["overage_trust_center_export_cents"]),
            "notes": f"Used {trust_used}, included {plan['included_trust_center_exports']}",
        },
    ]

    total_cents = sum(item["amount_cents"] for item in line_items)

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "billing_month": billing_month(),
        "plan": plan,
        "usage": {
            "inspection_submitted": inspections_used,
            "evidence_pack_exported": evidence_used,
            "trust_center_exported": trust_used,
        },
        "line_items": line_items,
        "total_cents": total_cents,
    }


def persist_invoice_preview(db: Session, preview: dict) -> dict:
    month = preview["billing_month"]
    tenant_id = preview["tenant_id"]

    db.query(models.InvoiceLineItem).filter(
        models.InvoiceLineItem.tenant_id == tenant_id,
        models.InvoiceLineItem.billing_month == month,
    ).delete()
    db.commit()

    created = []
    for item in preview["line_items"]:
        row = models.InvoiceLineItem(
            tenant_id=preview["tenant_id"],
            tenant_name=preview["tenant_name"],
            billing_month=month,
            item_type=item["item_type"],
            quantity=item["quantity"],
            unit_price_cents=item["unit_price_cents"],
            amount_cents=item["amount_cents"],
            notes=item["notes"],
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        created.append({
            "id": row.id,
            "item_type": row.item_type,
            "quantity": row.quantity,
            "unit_price_cents": row.unit_price_cents,
            "amount_cents": row.amount_cents,
            "notes": row.notes,
        })

    return {
        "tenant_id": preview["tenant_id"],
        "tenant_name": preview["tenant_name"],
        "billing_month": month,
        "items": created,
        "total_cents": preview["total_cents"],
    }
