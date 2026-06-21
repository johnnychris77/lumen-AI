"""P22: Healthcare Digital Quality Twin — API routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.digital_quality_twin import ScenarioSimulation
from app.services.digital_quality_twin_service import (
    DISCLAIMER,
    get_executive_brief,
    get_forecasts,
    get_intervention_models,
    get_twin_state,
    run_scenario,
    synthesize_twin,
)

router = APIRouter(tags=["digital_quality_twin"])

_DISCLAIMER = DISCLAIMER


def _tenant(request: Request) -> str:
    return get_request_tenant_id(request)


def _actor(request: Request) -> str:
    return get_request_actor(request) or "unknown"


def _to_dict(obj: Any) -> dict:
    """Serialize a SQLAlchemy model to a plain dict."""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class SimulateRequest(BaseModel):
    scenario_type: str = "quality_improvement"
    intervention_type: str = "vendor_change"
    parameters: dict = {}


class SynthesizeRequest(BaseModel):
    facility_id: str = ""


class CreateInterventionRequest(BaseModel):
    intervention_type: str
    intervention_target: str = ""
    baseline_quality_score: float = 0.0
    projected_quality_score: float = 0.0
    projected_improvement: float = 0.0
    effort_estimate: str = "medium"
    timeframe_days: int = 90


class ApproveScenarioRequest(BaseModel):
    reviewed_by: str = ""


# ---------------------------------------------------------------------------
# Twin State
# ---------------------------------------------------------------------------


@router.get("/api/quality-twin/state")
def twin_state(
    request: Request,
    facility_id: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """Current quality twin state snapshot."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    state = get_twin_state(db, tenant_id, facility_id=facility_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.state.view",
        resource_type="quality_twin_state",
        resource_id="",
        details={"facility_id": facility_id},
    )

    return {
        "status": "success",
        "state": state,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Forecasts
# ---------------------------------------------------------------------------


@router.get("/api/quality-twin/forecasts")
def forecasts(
    request: Request,
    db: Session = Depends(get_db),
):
    """30/60/90-day quality risk forecasts."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    items = get_forecasts(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.forecasts.list",
        resource_type="quality_forecasts",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "forecasts": items,
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Scenario Simulation
# ---------------------------------------------------------------------------


@router.post("/api/quality-twin/simulate")
def simulate(
    request: Request,
    body: SimulateRequest,
    db: Session = Depends(get_db),
):
    """Run a what-if scenario simulation."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    result = run_scenario(
        db,
        tenant_id,
        scenario_type=body.scenario_type,
        intervention_type=body.intervention_type,
        parameters=body.parameters,
    )

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.simulate",
        resource_type="scenario_simulation",
        resource_id=str(result.get("id", "")),
        details={
            "scenario_type": body.scenario_type,
            "intervention_type": body.intervention_type,
        },
    )

    return {
        "status": "success",
        "simulation": result,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Interventions
# ---------------------------------------------------------------------------


@router.get("/api/quality-twin/interventions")
def list_interventions(
    request: Request,
    db: Session = Depends(get_db),
):
    """List advisory intervention models."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    items = get_intervention_models(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.interventions.list",
        resource_type="intervention_models",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "interventions": items,
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/api/quality-twin/interventions")
def create_intervention(
    request: Request,
    body: CreateInterventionRequest,
    db: Session = Depends(get_db),
):
    """Create an intervention model record."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    from app.models.digital_quality_twin import InterventionModel

    model = InterventionModel(
        tenant_id=tenant_id,
        intervention_type=body.intervention_type,
        intervention_target=body.intervention_target,
        baseline_quality_score=body.baseline_quality_score,
        projected_quality_score=body.projected_quality_score,
        projected_improvement=body.projected_improvement,
        effort_estimate=body.effort_estimate,
        timeframe_days=body.timeframe_days,
        human_review_required=True,
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.interventions.create",
        resource_type="intervention_models",
        resource_id=str(model.id),
        details={"intervention_type": body.intervention_type},
    )

    return {
        "status": "success",
        "intervention": _to_dict(model),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Executive Brief
# ---------------------------------------------------------------------------


@router.get("/api/quality-twin/executive-brief")
def executive_brief(
    request: Request,
    role: str = Query(default="quality_director"),
    db: Session = Depends(get_db),
):
    """Role-specific executive decision brief."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    brief = get_executive_brief(db, tenant_id, role=role)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.executive_brief.view",
        resource_type="executive_decision_brief",
        resource_id="",
        details={"role": role},
    )

    return {
        "status": "success",
        "brief": brief,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Synthesize
# ---------------------------------------------------------------------------


@router.post("/api/quality-twin/synthesize")
def synthesize(
    request: Request,
    body: SynthesizeRequest,
    db: Session = Depends(get_db),
):
    """Trigger full twin synthesis from all 9 data sources."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    result = synthesize_twin(db, tenant_id, facility_id=body.facility_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.synthesize",
        resource_type="quality_twin_state",
        resource_id="",
        details={"facility_id": body.facility_id, "sources_ingested": len(result.get("sources_ingested", []))},
    )

    return {
        "status": "success",
        "twin_state": result,
        "sources_ingested": result.get("sources_ingested", []),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/api/quality-twin/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    """Consolidated quality twin KPI dashboard."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    state = get_twin_state(db, tenant_id)
    forecasts_list = get_forecasts(db, tenant_id)

    scenarios = (
        db.query(ScenarioSimulation)
        .filter(ScenarioSimulation.tenant_id == tenant_id)
        .all()
    )
    human_review_required_count = sum(
        1 for s in scenarios if s.human_review_required
    )

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.dashboard.view",
        resource_type="quality_twin_dashboard",
        resource_id="",
    )

    return {
        "status": "success",
        "overall_quality_score": state["overall_quality_score"],
        "open_emerging_risks": state["open_emerging_risks"],
        "open_investigations": state["open_investigations"],
        "active_recalls": state["active_recalls"],
        "trend_direction": state["trend_direction"],
        "human_review_required_count": human_review_required_count,
        "benchmarking_percentile": state["benchmarking_percentile"],
        "forecasts_count": len(forecasts_list),
        "data_source": state.get("data_source", "simulated"),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Scenarios list
# ---------------------------------------------------------------------------


@router.get("/api/quality-twin/scenarios")
def list_scenarios(
    request: Request,
    db: Session = Depends(get_db),
):
    """List saved scenario simulations."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    rows = (
        db.query(ScenarioSimulation)
        .filter(ScenarioSimulation.tenant_id == tenant_id)
        .order_by(ScenarioSimulation.id.desc())
        .all()
    )

    items = [_to_dict(r) for r in rows]

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.scenarios.list",
        resource_type="scenario_simulations",
        resource_id="all",
        details={"count": len(items)},
    )

    return {
        "status": "success",
        "scenarios": items,
        "count": len(items),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Approve scenario
# ---------------------------------------------------------------------------


@router.patch("/api/quality-twin/scenarios/{scenario_id}/approve")
def approve_scenario(
    scenario_id: int,
    request: Request,
    body: ApproveScenarioRequest,
    db: Session = Depends(get_db),
):
    """Human-approve a scenario simulation."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    scenario = (
        db.query(ScenarioSimulation)
        .filter(
            ScenarioSimulation.id == scenario_id,
            ScenarioSimulation.tenant_id == tenant_id,
        )
        .first()
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found.")

    scenario.status = "approved"
    scenario.reviewed_by = body.reviewed_by or _actor(request)
    scenario.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(scenario)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="quality_twin.scenario.approve",
        resource_type="scenario_simulations",
        resource_id=str(scenario_id),
        details={"reviewed_by": scenario.reviewed_by},
    )

    return {
        "status": "success",
        "scenario": _to_dict(scenario),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }
