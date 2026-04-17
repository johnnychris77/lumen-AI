from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.scheduled_account_reviews import run_scheduled_account_review_once
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["scheduled-account-reviews"])


class ScheduledAccountReviewPayload(BaseModel):
    name: str
    review_type: str = "qbr"
    audience: str = "executive"
    period_label_template: str = "Quarterly Business Review - {quarter} {year}"
    schedule_cron: str = "0 8 1 */3 *"
    delivery_channel: str = "email"
    delivery_target: str = ""
    distribution_list_id: int = 0
    include_docx: bool = True
    include_pptx: bool = True
    include_pdf: bool = True
    is_enabled: bool = True
    notes: str = ""


class AssignDistributionListPayload(BaseModel):
    distribution_list_id: int


def _schedule_row(row: models.ScheduledAccountReview) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "name": row.name,
        "review_type": row.review_type,
        "audience": row.audience,
        "period_label_template": row.period_label_template,
        "schedule_cron": row.schedule_cron,
        "delivery_channel": row.delivery_channel,
        "delivery_target": row.delivery_target,
        "distribution_list_id": row.distribution_list_id,
        "include_docx": row.include_docx,
        "include_pptx": row.include_pptx,
        "include_pdf": row.include_pdf,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _delivery_row(row: models.AccountReviewDelivery) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "schedule_id": row.schedule_id,
        "account_review_id": row.account_review_id,
        "export_id": row.export_id,
        "delivery_channel": row.delivery_channel,
        "delivery_target": row.delivery_target,
        "delivery_status": row.delivery_status,
        "result_json": row.result_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/scheduled-account-reviews")
def create_schedule(
    payload: ScheduledAccountReviewPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.ScheduledAccountReview(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        name=payload.name,
        review_type=payload.review_type,
        audience=payload.audience,
        period_label_template=payload.period_label_template,
        schedule_cron=payload.schedule_cron,
        delivery_channel=payload.delivery_channel,
        delivery_target=payload.delivery_target,
        distribution_list_id=payload.distribution_list_id,
        include_docx=payload.include_docx,
        include_pptx=payload.include_pptx,
        include_pdf=payload.include_pdf,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
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
        action_type="scheduled_account_review_create",
        resource_type="scheduled_account_review",
        resource_id=row.id,
        request=request,
        details=_schedule_row(row),
        compliance_flag=True,
    )
    return {"item": _schedule_row(row)}


@router.get("/scheduled-account-reviews")
def list_schedules(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.ScheduledAccountReview)
        .filter(models.ScheduledAccountReview.tenant_id == tenant["tenant_id"])
        .order_by(models.ScheduledAccountReview.id.desc())
        .all()
    )
    return {"items": [_schedule_row(r) for r in rows]}


@router.post("/scheduled-account-reviews/{schedule_id}/run")
def run_schedule(
    schedule_id: int,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.ScheduledAccountReview)
        .filter(
            models.ScheduledAccountReview.id == schedule_id,
            models.ScheduledAccountReview.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled account review not found")

    result = run_scheduled_account_review_once(db, row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="scheduled_account_review_run",
        resource_type="scheduled_account_review",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.get("/scheduled-account-reviews/deliveries")
def list_deliveries(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.AccountReviewDelivery)
        .filter(models.AccountReviewDelivery.tenant_id == tenant["tenant_id"])
        .order_by(models.AccountReviewDelivery.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_delivery_row(r) for r in rows]}


@router.post("/scheduled-account-reviews/{schedule_id}/assign-distribution-list")
def assign_distribution_list(
    schedule_id: int,
    payload: AssignDistributionListPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.ScheduledAccountReview)
        .filter(
            models.ScheduledAccountReview.id == schedule_id,
            models.ScheduledAccountReview.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled account review not found")

    dl = (
        db.query(models.DistributionList)
        .filter(
            models.DistributionList.id == payload.distribution_list_id,
            models.DistributionList.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not dl:
        raise HTTPException(status_code=404, detail="Distribution list not found")

    row.distribution_list_id = payload.distribution_list_id
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _schedule_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="scheduled_account_review_assign_distribution_list",
        resource_type="scheduled_account_review",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}
