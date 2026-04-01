from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles
from app.retention import compute_retention_metadata

router = APIRouter(tags=["retention-admin"])


class RetentionPolicyPayload(BaseModel):
    artifact_type: str
    retention_days: int = 365
    legal_hold_enabled: bool = False
    notes: str = ""
    is_enabled: bool = True


def _response(row: models.RetentionPolicy) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "artifact_type": row.artifact_type,
        "retention_days": row.retention_days,
        "legal_hold_enabled": row.legal_hold_enabled,
        "notes": row.notes,
        "is_enabled": row.is_enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/retention-policies")
def list_retention_policies(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    rows = (
        db.query(models.RetentionPolicy)
        .filter(models.RetentionPolicy.tenant_id == tenant["tenant_id"])
        .order_by(models.RetentionPolicy.id.desc())
        .all()
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="retention_policy_list",
        resource_type="retention_policy",
        request=request,
        details={"count": len(rows)},
        compliance_flag=True,
    )

    return {"items": [_response(r) for r in rows]}


@router.post("/retention-policies")
def create_retention_policy(
    payload: RetentionPolicyPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.RetentionPolicy(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        artifact_type=payload.artifact_type.strip(),
        retention_days=payload.retention_days,
        legal_hold_enabled=payload.legal_hold_enabled,
        notes=payload.notes,
        is_enabled=payload.is_enabled,
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
        action_type="retention_policy_create",
        resource_type="retention_policy",
        resource_id=row.id,
        request=request,
        details=_response(row),
        compliance_flag=True,
    )

    return {"item": _response(row)}


@router.post("/retention-policies/{policy_id}/toggle")
def toggle_retention_policy(
    policy_id: int,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.RetentionPolicy)
        .filter(
            models.RetentionPolicy.id == policy_id,
            models.RetentionPolicy.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Retention policy not found")

    row.is_enabled = not bool(row.is_enabled)
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="retention_policy_toggle",
        resource_type="retention_policy",
        resource_id=row.id,
        request=request,
        details={"is_enabled": row.is_enabled, "artifact_type": row.artifact_type},
        compliance_flag=True,
    )

    return {"item": _response(row)}


@router.get("/retention-policies/evaluate/{artifact_type}")
def evaluate_retention_policy(
    artifact_type: str,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], artifact_type)
