"""v2.5 — Project Sentinel: Predictive Simulation & Clinical Scenario Engine routes.

Route: /scenario-analysis (frontend). API prefix: /api/scenario-analysis.

  * POST /api/scenario-analysis/{inspection_id}/generate         — Sections 1-3
  * GET  /api/scenario-analysis/{inspection_id}                  — Section 7
  * GET  /api/scenario-analysis/{inspection_id}/workflow-impact   — Section 4
  * GET  /api/scenario-analysis/instrument-health                — Section 5
  * GET  /api/scenario-analysis/education/compare                — Section 6
  * POST /api/scenario-analysis/{simulation_run_id}/actual-outcome — Section 8
  * GET  /api/scenario-analysis/analytics                        — Section 9
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services import simulation_engine_service as engine

router = APIRouter(prefix="/api/scenario-analysis", tags=["scenario-analysis"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


class ActualOutcomeIn(BaseModel):
    actual_disposition: str = Field(..., min_length=1, max_length=50)
    notes: str = Field("", max_length=2000)


@router.post("/{inspection_id}/generate")
def post_generate_scenarios(
    inspection_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = engine.generate_scenarios(db, tenant_id, inspection_id)
    except engine.SimulationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="scenario_analysis.generate", resource_type="simulation_run", resource_id=str(result["id"]),
        details={"inspection_id": inspection_id, "recommended_scenario": result["recommended_scenario"]},
    )
    return result


@router.get("/analytics")
def get_analytics(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return engine.enterprise_scenario_analytics(db, tenant_id)


@router.get("/instrument-health")
def get_instrument_health(
    request: Request,
    instrument_barcode: str = Query(""),
    instrument_udi: str = Query(""),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if instrument_barcode:
        identity = f"barcode:{instrument_barcode}"
    elif instrument_udi:
        identity = f"udi:{instrument_udi}"
    else:
        raise HTTPException(status_code=422, detail="instrument_barcode or instrument_udi is required.")

    tenant_id = _tenant(current_user, request)
    result = engine.project_instrument_health(db, tenant_id, identity)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No inspection history found for instrument identity '{identity}'.")
    return result


@router.get("/education/compare")
def get_educational_comparison(
    request: Request,
    instrument_type: str = Query(...),
    finding_type: str = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return engine.educational_comparison(db, tenant_id, instrument_type, finding_type)


@router.post("/{simulation_run_id}/actual-outcome")
def post_actual_outcome(
    simulation_run_id: int, body: ActualOutcomeIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = engine.record_actual_outcome(
            db, tenant_id, simulation_run_id,
            actual_disposition=body.actual_disposition, recorded_by=_actor(current_user), notes=body.notes,
        )
    except engine.SimulationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="scenario_analysis.outcome_recorded", resource_type="scenario_outcome", resource_id=str(result["id"]),
        details={"simulation_run_id": simulation_run_id, "actual_disposition": body.actual_disposition},
    )
    return result


@router.get("/{inspection_id}/workflow-impact")
def get_workflow_impact(
    inspection_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return engine.project_workflow_impact(db, tenant_id, inspection_id)
    except engine.SimulationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{inspection_id}")
def get_scenario_analysis(
    inspection_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = engine.get_latest_run(db, tenant_id, inspection_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No scenario analysis exists yet for inspection {inspection_id}. Generate it first.",
        )
    return result
