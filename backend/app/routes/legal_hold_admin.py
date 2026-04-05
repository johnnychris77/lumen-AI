from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["legal-hold-admin"])


class LegalHoldPayload(BaseModel):
    artifact_type: str
    legal_hold_enabled: bool
    notes: str = ""


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


@router.post("/legal-hold")
def set_legal_hold(
    payload: LegalHoldPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.RetentionPolicy)
        .filter(
            models.RetentionPolicy.tenant_id == tenant["tenant_id"],
            models.RetentionPolicy.artifact_type == payload.artifact_type,
        )
        .order_by(models.RetentionPolicy.id.desc())
        .first()
    )

    if row:
        row.legal_hold_enabled = payload.legal_hold_enabled
        row.notes = payload.notes or row.notes
        db.add(row)
        db.commit()
        db.refresh(row)
    else:
        row = models.RetentionPolicy(
            tenant_id=tenant["tenant_id"],
            tenant_name=tenant["tenant_name"],
            artifact_type=payload.artifact_type,
            retention_days=365,
            legal_hold_enabled=payload.legal_hold_enabled,
            notes=payload.notes,
            is_enabled=True,
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
        action_type="legal_hold_update",
        resource_type="retention_policy",
        resource_id=row.id,
        request=request,
        details=_response(row),
        compliance_flag=True,
    )

    return {"item": _response(row)}
