from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.billing import build_invoice_preview, get_plan, persist_invoice_preview
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["billing"])


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

    return result
