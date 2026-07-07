"""v2.0 — Anatomy-Aware Clinical Intelligence ("Project Anatomy").

Exposes the Anatomy Zone Engine, the Zone Risk Matrix, Dynamic Inspection
Guidance, and Learning Dataset v2 — all computed live from the real anatomy
data in instrument_anatomy.py and the real stored inspection/review rows,
never a separate fabricated dataset.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services.learning_dataset_v2 import learning_dataset_v2
from app.services.zone_intelligence import dynamic_inspection_guidance, zone_engine, zone_risk_matrix

router = APIRouter(tags=["anatomy-intelligence"])

_READ_ROLES = ("admin", "spd_manager", "supervisor", "operator", "viewer")


@router.get("/anatomy/zone-risk-matrix")
def get_zone_risk_matrix(current_user=Depends(require_roles(*_READ_ROLES))):
    """Deliverable 5 — every declared anatomy zone bucketed by risk tier."""
    return zone_risk_matrix()


@router.get("/anatomy/zone-engine/{instrument_type}/{zone_name:path}")
def get_zone_engine(
    instrument_type: str,
    zone_name: str,
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Deliverable 2 — Instrument -> Anatomy -> Zone -> Risk -> Typical
    Findings -> Recommended Inspection Method for one named zone."""
    result = zone_engine(instrument_type, zone_name)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_name}' is not a declared anatomy zone for instrument '{instrument_type}'.",
        )
    return result


@router.get("/anatomy/inspection-zone-guidance/{instrument_type}/{zone_name:path}")
def get_inspection_zone_guidance(
    instrument_type: str,
    zone_name: str,
    coverage_status: str | None = None,
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Deliverable 7 — Dynamic Inspection Guidance for the zone currently
    being captured: risk level, expected findings, inspection tips,
    required lighting, recommended angle, coverage status."""
    result = dynamic_inspection_guidance(instrument_type, zone_name, coverage_status=coverage_status)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_name}' is not a declared anatomy zone for instrument '{instrument_type}'.",
        )
    return result


@router.get("/anatomy/learning-dataset")
def get_learning_dataset(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Deliverable 8 — Learning Dataset v2, joined live from real supervisor
    reviews / inspections / image tags. Admin/spd_manager only — this is a
    training-data export surface, not a general read endpoint."""
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    return learning_dataset_v2(db, tenant_id)
