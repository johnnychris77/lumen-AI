"""v1.6 — Clinical Service Readiness & Instrument Disposition Intelligence API.

- GET  /api/clinical-readiness/dashboard                     — Deliverable 7
- GET  /api/clinical-readiness/enterprise-analytics           — Deliverable 9
- GET  /api/clinical-readiness/instrument-condition            — Deliverable 5 (?instrument_identity=)
- GET  /api/inspections/{id}/evidence-panel                   — Deliverable 3
- GET  /api/inspections/{id}/readiness-timeline               — Deliverable 4
- GET  /api/inspections/{id}/risk-stratification              — Deliverable 8
- GET  /api/inspections/{id}/readiness-report                 — Deliverable 10 (JSON)
- GET  /api/inspections/{id}/readiness-report.pdf              — Deliverable 10 (PDF)
- POST /api/inspections/{id}/disposition-action               — Deliverable 6
- GET  /api/inspections/{id}/disposition-actions               — Deliverable 6 (history)
"""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.disposition_override import DISPOSITION_ACTIONS
from app.services.disposition_evidence_service import get_evidence_panel
from app.services.disposition_workspace_service import (
    InvalidDispositionAction, ReasonRequiredError, list_disposition_actions, submit_disposition_action,
)
from app.services.instrument_condition_service import instrument_condition_history
from app.services.readiness_dashboard_service import enterprise_readiness_analytics, readiness_dashboard
from app.services.readiness_engine import get_primary_finding_type
from app.services.readiness_report_service import build_readiness_report_payload, build_readiness_report_pdf
from app.services.readiness_timeline_service import build_timeline
from app.services.risk_stratification_service import stratify_risk

router = APIRouter(tags=["clinical-readiness"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _get_inspection(db: Session, tenant_id: str, inspection_id: int):
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return insp


@router.get("/api/clinical-readiness/dashboard")
def get_readiness_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return readiness_dashboard(db, _tenant(current_user, request))


@router.get("/api/clinical-readiness/enterprise-analytics")
def get_enterprise_analytics(
    request: Request,
    days: int = 180,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return enterprise_readiness_analytics(db, _tenant(current_user, request), days=days)


@router.get("/api/clinical-readiness/instrument-condition")
def get_instrument_condition(
    request: Request,
    instrument_identity: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    history = instrument_condition_history(db, _tenant(current_user, request), instrument_identity)
    if history is None:
        raise HTTPException(status_code=404, detail="No inspection history found for this instrument identity.")
    return history


@router.get("/api/inspections/{inspection_id}/evidence-panel")
def get_evidence_panel_endpoint(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    panel = get_evidence_panel(db, _tenant(current_user, request), inspection_id)
    if panel is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return panel


@router.get("/api/inspections/{inspection_id}/readiness-timeline")
def get_readiness_timeline(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    return build_timeline(db, tenant_id, insp)


@router.get("/api/inspections/{inspection_id}/risk-stratification")
def get_risk_stratification(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    return stratify_risk(insp, primary_finding_type=get_primary_finding_type(db, insp))


@router.get("/api/inspections/{inspection_id}/readiness-report")
def get_readiness_report(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    return build_readiness_report_payload(db, tenant_id, insp)


@router.get("/api/inspections/{inspection_id}/readiness-report.pdf")
def get_readiness_report_pdf(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    pdf = build_readiness_report_pdf(db, tenant_id, insp)
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="lumenai-readiness-report-{insp.id}.pdf"'},
    )


class DispositionActionIn(BaseModel):
    action: str = Field(..., description=f"One of {DISPOSITION_ACTIONS}")
    ai_recommended_disposition: str = Field("", max_length=50)
    modified_disposition: str = Field("", max_length=50)
    reason: str = Field("", max_length=2000)


@router.post("/api/inspections/{inspection_id}/disposition-action", status_code=201)
def post_disposition_action(
    inspection_id: int,
    body: DispositionActionIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    _get_inspection(db, tenant_id, inspection_id)

    try:
        row = submit_disposition_action(
            db, tenant_id=tenant_id, inspection_id=inspection_id,
            reviewer_name=_actor(current_user), reviewer_role=getattr(current_user, "role", "spd_manager"),
            action=body.action, ai_recommended_disposition=body.ai_recommended_disposition,
            modified_disposition=body.modified_disposition, reason=body.reason,
        )
    except InvalidDispositionAction as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ReasonRequiredError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    from app.services import workflow_state_service

    insp = _get_inspection(db, tenant_id, inspection_id)
    workflow_state_service.record_disposition_action(
        db, insp=insp, tenant_id=tenant_id, action=body.action, actor=_actor(current_user), reason=body.reason,
    )

    db.commit()
    db.refresh(row)
    return {
        "id": row.id, "action": row.action, "modified_disposition": row.modified_disposition,
        "reason": row.reason,
    }


@router.get("/api/inspections/{inspection_id}/disposition-actions")
def get_disposition_actions(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    rows = list_disposition_actions(db, tenant_id, inspection_id)
    return {
        "actions": [
            {
                "id": r.id, "action": r.action, "reviewer_name": r.reviewer_name,
                "ai_recommended_disposition": r.ai_recommended_disposition,
                "modified_disposition": r.modified_disposition, "reason": r.reason,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
