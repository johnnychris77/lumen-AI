from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.metering import check_quota, get_monthly_usage
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["usage-metering"])


class TenantQuotaPayload(BaseModel):
    metric_key: str
    monthly_limit: int
    notes: str = ""


def _quota_response(row: models.TenantQuota) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "metric_key": row.metric_key,
        "monthly_limit": row.monthly_limit,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/tenant-quotas")
def create_tenant_quota(
    payload: TenantQuotaPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.TenantQuota(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        metric_key=payload.metric_key,
        monthly_limit=payload.monthly_limit,
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
        action_type="tenant_quota_create",
        resource_type="tenant_quota",
        resource_id=row.id,
        request=request,
        details=_quota_response(row),
        compliance_flag=True,
    )

    return {"item": _quota_response(row)}


@router.get("/tenant-quotas")
def list_tenant_quotas(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.TenantQuota)
        .filter(models.TenantQuota.tenant_id == tenant["tenant_id"])
        .order_by(models.TenantQuota.id.desc())
        .all()
    )
    return {"items": [_quota_response(r) for r in rows]}


@router.get("/usage/summary")
def usage_summary(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.UsageEvent)
        .filter(models.UsageEvent.tenant_id == tenant["tenant_id"])
        .order_by(models.UsageEvent.id.desc())
        .all()
    )

    grouped = defaultdict(int)
    for row in rows:
        grouped[row.event_type] += int(row.quantity or 0)

    items = [{"event_type": k, "total": v} for k, v in sorted(grouped.items())]

    quota_status = []
    metric_keys = sorted(set([x["event_type"] for x in items] + ["inspection_submitted", "evidence_pack_exported", "trust_center_exported"]))
    for metric_key in metric_keys:
        quota_status.append(check_quota(db, tenant_id=tenant["tenant_id"], tenant_name=tenant["tenant_name"], metric_key=metric_key))

    return {
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "usage_totals": items,
        "quota_status": quota_status,
    }


@router.get("/usage/check/{metric_key}")
def usage_check(
    metric_key: str,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return check_quota(db, tenant_id=tenant["tenant_id"], tenant_name=tenant["tenant_name"], metric_key=metric_key)
