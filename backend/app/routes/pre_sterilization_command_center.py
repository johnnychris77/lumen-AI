"""Pre-Sterilization Command Center — the executive and operational view of
whether instruments, trays, departments, and facilities are clinically
ready to proceed to packaging and sterilization.

Route: /pre-sterilization-command-center (frontend). API prefix below.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.services.pre_sterilization_command_center_service import (
    _annotate,
    _reviewed_ids,
    baseline_coverage,
    clinical_inspection_readiness,
    executive_risk_dashboard,
    facility_readiness,
    high_risk_findings_queue,
    instrument_readiness,
    missing_zone_coverage_queue,
    repair_remove_queue,
    supervisor_review_queue,
    tray_readiness,
)

router = APIRouter(prefix="/api/pre-sterilization-command-center", tags=["pre-sterilization-command-center"])

_READ_ROLES = ("admin", "spd_manager", "operator", "viewer")


def _tenant_cases(db: Session, current_user) -> tuple[str, list]:
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    cases = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id)
        .order_by(models.Inspection.created_at.desc())
        .limit(5000)
        .all()
    )
    return tenant_id, cases


def _tenant_annotated(db: Session, current_user) -> tuple[str, list, list[dict]]:
    tenant_id, cases = _tenant_cases(db, current_user)
    reviewed_ids = _reviewed_ids(db, tenant_id)
    annotated = _annotate(cases, reviewed_ids)
    return tenant_id, cases, annotated


@router.get("/clinical-inspection-readiness")
def get_clinical_inspection_readiness(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 1 — Clinical Inspection Readiness Score."""
    tenant_id, _, annotated = _tenant_annotated(db, current_user)
    return {"tenant_id": tenant_id, **clinical_inspection_readiness(annotated)}


@router.get("/tray-readiness")
def get_tray_readiness(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 2 — Tray Readiness Score."""
    tenant_id, _, annotated = _tenant_annotated(db, current_user)
    return {"tenant_id": tenant_id, "trays": tray_readiness(annotated)}


@router.get("/instrument-readiness")
def get_instrument_readiness(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 3 — Instrument Readiness Score."""
    tenant_id, _, annotated = _tenant_annotated(db, current_user)
    return {"tenant_id": tenant_id, "instruments": instrument_readiness(annotated)}


@router.get("/facility-readiness")
def get_facility_readiness(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 4 — Facility Readiness Score."""
    tenant_id, _, annotated = _tenant_annotated(db, current_user)
    return {"tenant_id": tenant_id, "facilities": facility_readiness(annotated)}


@router.get("/high-risk-findings")
def get_high_risk_findings(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 5 — High-Risk Findings Queue."""
    tenant_id, _, annotated = _tenant_annotated(db, current_user)
    items = high_risk_findings_queue(annotated)
    return {"tenant_id": tenant_id, "count": len(items), "items": items}


@router.get("/supervisor-review-queue")
def get_supervisor_review_queue(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 6 — Supervisor Review Queue."""
    tenant_id, _, annotated = _tenant_annotated(db, current_user)
    items = supervisor_review_queue(annotated)
    return {"tenant_id": tenant_id, "count": len(items), "items": items}


@router.get("/missing-zone-coverage")
def get_missing_zone_coverage(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 7 — Missing Anatomy Zone Coverage."""
    tenant_id, cases = _tenant_cases(db, current_user)
    items = missing_zone_coverage_queue(cases)
    return {"tenant_id": tenant_id, "count": len(items), "items": items}


@router.get("/baseline-coverage")
def get_baseline_coverage(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 8 — Baseline Coverage."""
    tenant_id, cases = _tenant_cases(db, current_user)
    return {"tenant_id": tenant_id, **baseline_coverage(db, tenant_id, cases)}


@router.get("/repair-remove-queue")
def get_repair_remove_queue(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 9 — Repair / Remove From Service Queue."""
    tenant_id, _, annotated = _tenant_annotated(db, current_user)
    return {"tenant_id": tenant_id, **repair_remove_queue(annotated)}


@router.get("/executive-risk-dashboard")
def get_executive_risk_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Module 10 — Executive Risk Dashboard."""
    tenant_id, cases, annotated = _tenant_annotated(db, current_user)
    return {"tenant_id": tenant_id, **executive_risk_dashboard(db, tenant_id, cases, annotated)}


@router.get("/dashboard")
def get_full_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Aggregator — all ten modules in one call for the command-center page."""
    tenant_id, cases, annotated = _tenant_annotated(db, current_user)
    return {
        "tenant_id": tenant_id,
        "clinical_inspection_readiness": clinical_inspection_readiness(annotated),
        "tray_readiness": tray_readiness(annotated),
        "instrument_readiness": instrument_readiness(annotated),
        "facility_readiness": facility_readiness(annotated),
        "high_risk_findings_queue": high_risk_findings_queue(annotated),
        "supervisor_review_queue": supervisor_review_queue(annotated),
        "missing_zone_coverage_queue": missing_zone_coverage_queue(cases),
        "baseline_coverage": baseline_coverage(db, tenant_id, cases),
        "repair_remove_queue": repair_remove_queue(annotated),
        "executive_risk_dashboard": executive_risk_dashboard(db, tenant_id, cases, annotated),
        "human_review_required": True,
    }
