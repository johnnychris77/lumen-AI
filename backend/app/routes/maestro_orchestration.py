"""LumenAI AI Specialist — Project Maestro: Operational Orchestration &
Decision Intelligence routes.

Frontend route: /maestro. API prefix: /api/maestro.

Maestro is a pure read-and-synthesize leadership layer over every other
specialist -- see `app/models/maestro_orchestration.py` for the full
naming disambiguation from Phase 22's `app.agents.orchestrator` and
Nova's `nova_orchestration_service.py`, neither of which this router
touches.

Uses `tenant_authz.require_tenant_roles`, consistent with every sprint
since Athena (v4.8).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.maestro_orchestration import BRIEF_TYPES
from app.services import (
    maestro_capa_integration_service,
    maestro_daily_brief_service,
    maestro_decision_journal_service,
    maestro_orchestration_service,
    maestro_priority_engine_service,
    maestro_recommendation_engine_service,
    maestro_timeline_service,
)
from app.services.maestro_health_index_service import compute_operational_health, to_dict as health_to_dict
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/maestro", tags=["maestro"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Section 1 — Operational Orchestrator
# ---------------------------------------------------------------------------


@router.post("/run")
def post_run_orchestration(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return maestro_orchestration_service.run_daily_orchestration(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 2 — Priority Engine
# ---------------------------------------------------------------------------


@router.post("/priorities/run", status_code=201)
def post_run_priorities(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    rows = maestro_priority_engine_service.compute_priorities(db, _tenant(current_user))
    return {"priorities": [maestro_priority_engine_service.to_dict(r) for r in rows]}


@router.get("/priorities")
def get_priorities(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"priorities": maestro_priority_engine_service.latest_priorities(db, _tenant(current_user))}


# ---------------------------------------------------------------------------
# Sections 3 & 5 — Leadership Recommendation Engine
# ---------------------------------------------------------------------------


@router.post("/recommendations/run", status_code=201)
def post_run_recommendations(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    specific = maestro_recommendation_engine_service.generate_recommendations(db, _tenant(current_user))
    strategic = maestro_recommendation_engine_service.generate_strategic_recommendations(db, _tenant(current_user))
    return {
        "recommendations": [
            maestro_recommendation_engine_service.to_dict(r) for r in (*specific, *strategic)
        ],
    }


@router.get("/recommendations")
def get_recommendations(
    status: str = Query(""), timeline_horizon: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {
        "recommendations": maestro_recommendation_engine_service.list_recommendations(
            db, _tenant(current_user), status=status, timeline_horizon=timeline_horizon,
        ),
    }


@router.post("/recommendations/{recommendation_id}/status")
def post_recommendation_status(
    recommendation_id: int, payload: dict,
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    row = maestro_recommendation_engine_service.update_status(
        db, _tenant(current_user), recommendation_id, payload.get("status", ""),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return maestro_recommendation_engine_service.to_dict(row)


@router.post("/recommendations/{recommendation_id}/create-capa", status_code=201)
def post_create_capa(
    recommendation_id: int,
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    capa = maestro_capa_integration_service.create_capa_from_recommendation(
        db, _tenant(current_user), recommendation_id, owner=_actor(current_user),
    )
    if capa is None:
        raise HTTPException(status_code=404, detail="No matching CAPA-draft recommendation or triggering pattern found")
    return capa


# ---------------------------------------------------------------------------
# Section 4 — Daily Operational Brief
# ---------------------------------------------------------------------------


@router.post("/briefs/{brief_type}/generate", status_code=201)
def post_generate_brief(
    brief_type: str, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    if brief_type not in BRIEF_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown brief_type '{brief_type}'")
    row = maestro_daily_brief_service.generate_brief(db, _tenant(current_user), brief_type)
    return maestro_daily_brief_service.to_dict(row)


@router.get("/briefs/{brief_type}/latest")
def get_latest_brief(
    brief_type: str, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    result = maestro_daily_brief_service.latest_brief(db, _tenant(current_user), brief_type)
    if result is None:
        raise HTTPException(status_code=404, detail="No brief generated yet")
    return result


# ---------------------------------------------------------------------------
# Section 6 — Strategy Timeline
# ---------------------------------------------------------------------------


@router.get("/timeline")
def get_timeline(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return maestro_timeline_service.strategy_timeline(db, _tenant(current_user))


@router.post("/timeline/{recommendation_id}/move")
def post_move_timeline(
    recommendation_id: int, payload: dict,
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        row = maestro_timeline_service.move_horizon(
            db, _tenant(current_user), recommendation_id, payload.get("timeline_horizon", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return maestro_recommendation_engine_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 7 — Operational Health Index
# ---------------------------------------------------------------------------


@router.post("/health/run", status_code=201)
def post_run_health(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = compute_operational_health(db, _tenant(current_user))
    return health_to_dict(row)


# ---------------------------------------------------------------------------
# Section 8 — Decision Journal
# ---------------------------------------------------------------------------


@router.post("/decisions", status_code=201)
def post_decision(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = maestro_decision_journal_service.record_decision(
            db, _tenant(current_user), payload.get("recommendation_id"),
            leader_decision=payload.get("leader_decision", ""), decided_by=_actor(current_user),
            decided_role=current_user.get("role", ""), outcome=payload.get("outcome", ""),
            lessons_learned=payload.get("lessons_learned", ""), new_status=payload.get("new_status"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return maestro_decision_journal_service.to_dict(row)


@router.get("/decisions")
def get_decisions(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"journal": maestro_decision_journal_service.list_journal(db, _tenant(current_user))}


@router.get("/decisions/{recommendation_id}")
def get_decisions_for_recommendation(
    recommendation_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    return {"journal": maestro_decision_journal_service.journal_for_recommendation(db, _tenant(current_user), recommendation_id)}


# ---------------------------------------------------------------------------
# Section 9 — Leadership Workspace (`/maestro`)
# ---------------------------------------------------------------------------


@router.get("/workspace")
def get_workspace(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return maestro_orchestration_service.leadership_workspace_summary(db, _tenant(current_user))
