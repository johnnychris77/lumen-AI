"""v1.9 — Pilot Deployment Loop & Production Workflow Hardening.

Distinct URL prefix (`/api/pilot-deployment/*`) from the existing
`/api/pilot/*` P14 commercial pilot-conversion routes (`routes/pilot.py`,
a trial-subscription concept) — this module is about the first
real-world SPD site's operational readiness, an unrelated domain that
happens to share the English word "pilot".

- GET/PUT /api/pilot-deployment/site-config     — Deliverable 4
- POST    /api/pilot-deployment/error-log        — Deliverable 7
- GET     /api/pilot-deployment/data-collection  — Deliverable 6
- GET     /api/inspections/{id}/data-quality     — Deliverable 5
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.pilot_error_log import ERROR_TYPES
from app.services.data_quality_guardrails_service import evaluate_data_quality
from app.services.pilot_data_collection_service import pilot_data_collection_summary
from app.services.pilot_error_log_service import log_error
from app.services.pilot_site_config_service import config_to_dict, get_or_create_config, update_config

router = APIRouter(tags=["pilot-deployment"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


@router.get("/api/pilot-deployment/site-config")
def get_site_config(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = get_or_create_config(db, tenant_id)
    db.commit()
    return config_to_dict(row)


class SiteConfigIn(BaseModel):
    facility_name: str | None = Field(None, max_length=255)
    department: str | None = Field(None, max_length=255)
    enabled_instrument_families: list[str] | None = None
    required_inspection_zones: list[str] | None = None
    baseline_required: bool | None = None
    minimum_coverage_pct: int | None = Field(None, ge=0, le=100)
    supervisor_review_threshold_score: int | None = Field(None, ge=0, le=100)


@router.put("/api/pilot-deployment/site-config")
def put_site_config(
    body: SiteConfigIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    tenant_id = _tenant(current_user, request)
    row = update_config(
        db, tenant_id, updated_by=_actor(current_user), facility_name=body.facility_name,
        department=body.department, enabled_instrument_families=body.enabled_instrument_families,
        required_inspection_zones=body.required_inspection_zones, baseline_required=body.baseline_required,
        minimum_coverage_pct=body.minimum_coverage_pct,
        supervisor_review_threshold_score=body.supervisor_review_threshold_score,
    )
    db.commit()
    db.refresh(row)
    return config_to_dict(row)


class ErrorLogIn(BaseModel):
    error_type: str = Field(..., description=f"One of {ERROR_TYPES}")
    detail: str = Field("", max_length=500)
    inspection_id: int | None = None


@router.post("/api/pilot-deployment/error-log", status_code=201)
def post_error_log(
    body: ErrorLogIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if body.error_type not in ERROR_TYPES:
        raise HTTPException(status_code=422, detail=f"error_type must be one of {ERROR_TYPES}")
    tenant_id = _tenant(current_user, request)
    row = log_error(
        db, tenant_id=tenant_id, error_type=body.error_type, detail=body.detail,
        actor_role=getattr(current_user, "role", ""), inspection_id=body.inspection_id,
    )
    db.commit()
    return {"logged": row is not None}


@router.get("/api/pilot-deployment/data-collection")
def get_data_collection(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return pilot_data_collection_summary(db, _tenant(current_user, request))


@router.get("/api/inspections/{inspection_id}/data-quality")
def get_inspection_data_quality(
    inspection_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    config = get_or_create_config(db, tenant_id)
    db.commit()
    return evaluate_data_quality(insp, pilot_config=config)
