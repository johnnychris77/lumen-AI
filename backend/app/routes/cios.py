"""Phase 23 — Clinical Intelligence Operating System (CIOS) routes.

Route: /cios-dashboard (frontend). API prefix below.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.cios import event_bus
from app.cios.certificate import build_certificate, render_certificate_pdf
from app.cios.dashboard import build_dashboard
from app.cios.decision_ledger import list_decisions
from app.cios.governance import governance_snapshot
from app.cios.orchestrator import run_cios_pipeline
from app.cios.rule_registry import CLINICAL_RULE_REGISTRY
from app.cios.state_machine import derive_state
from app.db import models
from app.deps import get_db
from app.models.supervisor_review import SupervisorReview

router = APIRouter(prefix="/api/cios", tags=["clinical-intelligence-operating-system"])

_READ_ROLES = ("admin", "spd_manager", "operator", "viewer")


def _get_inspection(db: Session, inspection_id: int, tenant_id: str):
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return insp


@router.get("/run/{inspection_id}")
def run_cios(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 1 — run the full Clinical Intelligence Operating System pipeline."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    insp = _get_inspection(db, inspection_id, tenant_id)
    return run_cios_pipeline(db, insp, tenant_id)


@router.get("/state/{inspection_id}")
def get_inspection_state(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 4 — Inspection State Machine."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    insp = _get_inspection(db, inspection_id, tenant_id)
    review = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.inspection_id == inspection_id)
        .order_by(SupervisorReview.id.desc())
        .first()
    )
    return {"inspection_id": inspection_id, **derive_state(insp, review)}


@router.get("/decision-ledger/{inspection_id}")
def get_decision_ledger(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 5 — Clinical Decision Ledger for one inspection."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    _get_inspection(db, inspection_id, tenant_id)
    return {"inspection_id": inspection_id, "decisions": list_decisions(db, tenant_id, inspection_id)}


@router.get("/events")
def get_events(
    inspection_id: int | None = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 6 — Enterprise Event Bus."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    return {"events": event_bus.list_events(db, tenant_id, inspection_id, limit)}


@router.get("/certificate/{inspection_id}")
def get_certificate(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 8 — Clinical Readiness Certificate (JSON)."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    insp = _get_inspection(db, inspection_id, tenant_id)
    cios_result = run_cios_pipeline(db, insp, tenant_id)
    return build_certificate(db, insp, tenant_id, cios_result)


@router.get("/certificate/{inspection_id}/pdf")
def get_certificate_pdf(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 8 — Clinical Readiness Certificate (PDF)."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    insp = _get_inspection(db, inspection_id, tenant_id)
    cios_result = run_cios_pipeline(db, insp, tenant_id)
    certificate = build_certificate(db, insp, tenant_id, cios_result)
    pdf_bytes = render_certificate_pdf(certificate)
    filename = f"lumenai_readiness_certificate_{inspection_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/governance")
def get_governance(current_user=Depends(require_roles(*_READ_ROLES))):
    """Section 10 — Platform Governance version snapshot."""
    return governance_snapshot()


@router.get("/rule-registry")
def get_rule_registry(current_user=Depends(require_roles(*_READ_ROLES))):
    """Section 11 — Clinical Rule Registry."""
    return {"rules": CLINICAL_RULE_REGISTRY}


@router.get("/dashboard")
def get_cios_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 9 — Enterprise Health Dashboard (/cios-dashboard)."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    return build_dashboard(db, tenant_id)
