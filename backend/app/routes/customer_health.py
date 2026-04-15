from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.customer_health import (
    build_customer_health_summary,
    create_health_snapshot,
    latest_snapshot,
    recommendations,
)
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["customer-health"])


def _row(row: models.CustomerHealthSnapshot) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "health_score": row.health_score,
        "health_status": row.health_status,
        "usage_score": row.usage_score,
        "governance_score": row.governance_score,
        "adoption_score": row.adoption_score,
        "risk_flags_json": row.risk_flags_json,
        "summary_json": row.summary_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/customer-health/summary")
def customer_health_summary(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    latest = latest_snapshot(db, tenant["tenant_id"])
    live = build_customer_health_summary(db, tenant["tenant_id"], tenant["tenant_name"], 30)

    return {
        "live": live,
        "latest_snapshot": _row(latest) if latest else None,
    }


@router.post("/customer-health/snapshot")
def snapshot_customer_health(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row, summary = create_health_snapshot(db, tenant["tenant_id"], tenant["tenant_name"], 30)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="customer_health_snapshot_create",
        resource_type="customer_health_snapshot",
        resource_id=row.id,
        request=request,
        details=summary,
        compliance_flag=True,
    )

    return {
        "snapshot": _row(row),
        "summary": summary,
    }


@router.get("/customer-health/history")
def customer_health_history(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.CustomerHealthSnapshot)
        .filter(models.CustomerHealthSnapshot.tenant_id == tenant["tenant_id"])
        .order_by(models.CustomerHealthSnapshot.id.desc())
        .limit(100)
        .all()
    )
    return {"items": [_row(r) for r in rows]}


@router.get("/customer-health/recommendations")
def customer_health_recommendations(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    summary = build_customer_health_summary(db, tenant["tenant_id"], tenant["tenant_name"], 30)
    return {
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "health_score": summary["health_score"],
        "health_status": summary["health_status"],
        "risk_flags": summary["risk_flags"],
        "recommendations": recommendations(summary),
    }
