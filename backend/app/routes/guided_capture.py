"""v1.2 — Guided Capture & Coverage Workflow routes.

- GET  /api/guided-capture/{instrument_type} — Guided Capture Panel + Capture
  Checklist + Coverage Score/readiness, all in one response.
- GET  /api/inspections/{id}/image-tags — per-image view tags for an inspection.
- POST /api/inspections/{id}/coverage-override — supervisor/admin override to
  unlock a final AI decision despite incomplete coverage, when org policy
  requires full coverage (see app/services/guided_capture.py).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.config import get_settings
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.inspection_image_tag import InspectionImageTag
from app.services.guided_capture import coverage_readiness, guided_capture_panel

router = APIRouter(tags=["guided-capture"])

_READ_ROLES = ("admin", "spd_manager", "operator", "viewer")


@router.get("/guided-capture/{instrument_type}")
def get_guided_capture_panel(
    instrument_type: str,
    captured_zones: str | None = Query(None, description="Comma-separated list of zones already captured"),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Guided Capture Panel + Capture Checklist + Coverage Score, in one call.

    ``captured_zones`` omitted means "not yet assessed" (coverage_status
    reflects that honestly); an explicit (possibly empty) comma-separated
    list is assessed normally.
    """
    zones = [z.strip() for z in captured_zones.split(",") if z.strip()] if captured_zones is not None else None
    panel = guided_capture_panel(instrument_type, zones)
    readiness = coverage_readiness(
        instrument_type, zones,
        require_full_coverage=get_settings().require_full_coverage_before_final_decision,
    )
    return {**panel, **readiness}


def _get_inspection(db: Session, inspection_id: int, tenant_id: str, is_admin: bool) -> models.Inspection:
    query = db.query(models.Inspection).filter(models.Inspection.id == inspection_id)
    if tenant_id and not is_admin:
        query = query.filter(models.Inspection.tenant_id == tenant_id)
    row = query.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return row


@router.get("/inspections/{inspection_id}/image-tags")
def list_image_tags(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = getattr(current_user, "tenant_id", None)
    is_admin = getattr(current_user, "role", "") == "admin"
    _get_inspection(db, inspection_id, tenant_id, is_admin)

    rows = (
        db.query(InspectionImageTag)
        .filter(InspectionImageTag.inspection_id == inspection_id)
        .order_by(InspectionImageTag.id.asc())
        .all()
    )
    return {
        "inspection_id": inspection_id,
        "count": len(rows),
        "tags": [
            {
                "id": r.id,
                "instrument_family": r.instrument_family,
                "anatomy_zone": r.anatomy_zone,
                "image_view": r.image_view,
                "capture_quality": r.capture_quality,
                "notes": r.notes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


class CoverageOverrideIn(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1000)


@router.post("/inspections/{inspection_id}/coverage-override", status_code=200)
def apply_coverage_override(
    inspection_id: int,
    body: CoverageOverrideIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Section 7 — Supervisor Override. Lets a supervisor/admin proceed to a
    final AI decision despite missing zone coverage, with a required reason.
    Audit-logged; does not alter the coverage score itself, only the gate."""
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    is_admin = getattr(current_user, "role", "") == "admin"
    row = _get_inspection(db, inspection_id, tenant_id, is_admin)

    actor = getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")
    now = datetime.now(timezone.utc)

    row.coverage_override_reason = body.reason
    row.coverage_override_by = actor
    row.coverage_override_at = now
    row.coverage_gate_status = "ready"
    row.is_draft = False
    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id or row.tenant_id,
        tenant_name=row.tenant_name,
        actor_email=actor,
        actor_role=getattr(current_user, "role", "spd_manager"),
        action_type="coverage_override_applied",
        resource_type="inspection",
        resource_id=str(row.id),
        details={"reason": body.reason, "coverage_status": row.coverage_status},
        compliance_flag=True,
    )

    return {
        "id": row.id,
        "coverage_gate_status": row.coverage_gate_status,
        "is_draft": row.is_draft,
        "coverage_override_reason": row.coverage_override_reason,
        "coverage_override_by": row.coverage_override_by,
        "coverage_override_at": row.coverage_override_at.isoformat(),
    }
