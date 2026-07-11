"""v4.9 — LumenAI OS: Project Phoenix — Self-Improving Healthcare
Intelligence Platform routes.

Frontend routes: /phoenix, /platform-health.
API prefix: /api/phoenix — free namespace (confirmed via research).

## Tenant authorization

Like Athena (v4.8), every route in this file uses `tenant_authz.
require_tenant_roles` (real `TenantMembership` verification) rather than
the header-only pattern the first 16 modules used. Phoenix is a new
module, not a retrofit — it does not knowingly reintroduce the
cross-tenant gap those modules still carry.

  * GET  /learning-engine/summary                                        — Section 1
  * POST /recommendations/generate, GET /recommendations,
    GET  /recommendations/{id}                                            — Section 2
  * GET  /observatory/summary, POST /observatory/latency,
    GET  /observatory/latency, GET /observatory/coverage                  — Section 3
  * GET  /workflow-optimization/summary,
    GET  /workflow-optimization/{workflow_id}                             — Section 4
  * GET  /knowledge-evolution/summary                                      — Section 5
  * POST /competency-intelligence/run,
    GET  /competency-intelligence/opportunities                            — Section 6
  * GET  /platform-health/dashboard                                        — Section 7
  * POST /innovation/ideas, GET /innovation/ideas, GET /innovation/ideas/{id},
    PATCH /innovation/ideas/{id}/status, GET /innovation/summary            — Section 8
  * POST /recommendations/{id}/validation/start,
    POST /recommendations/{id}/validation/advance,
    POST /recommendations/{id}/validation/outcomes,
    GET  /recommendations/{id}/validation                                  — Section 9
  * POST /maturity/compute, GET /maturity/history                          — Section 10
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.services import (
    phoenix_ai_observatory_service,
    phoenix_competency_intelligence_service,
    phoenix_innovation_pipeline_service,
    phoenix_knowledge_evolution_service,
    phoenix_learning_engine_service,
    phoenix_maturity_index_service,
    phoenix_platform_health_service,
    phoenix_recommendation_engine,
    phoenix_validation_pipeline_service,
    phoenix_workflow_optimization_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/phoenix", tags=["phoenix"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


def _audit(db: Session, tenant_id: str, actor: str, action_type: str, resource_type: str, resource_id: str, details: dict) -> None:
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=actor, actor_role="",
        action_type=action_type, resource_type=resource_type, resource_id=resource_id, details=details, compliance_flag=True,
    )


# ---------------------------------------------------------------------------
# Section 1 — Phoenix Learning Engine
# ---------------------------------------------------------------------------


@router.get("/learning-engine/summary")
def get_learning_engine_summary(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_learning_engine_service.learning_engine_summary(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 2 — Improvement Recommendation Engine
# ---------------------------------------------------------------------------


@router.post("/recommendations/generate")
def post_generate_recommendations(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = phoenix_recommendation_engine.generate_recommendations(db, tenant_id)
    _audit(db, tenant_id, actor, "phoenix.recommendations_generated", "phoenix_improvement_recommendations", "", {"count": len(result)})
    return {"recommendations": result}


@router.get("/recommendations")
def get_recommendations(status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {"recommendations": phoenix_recommendation_engine.list_recommendations(db, tenant_id, status=status)}


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    try:
        return phoenix_recommendation_engine.get_recommendation(db, tenant_id, recommendation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 3 — AI Performance Observatory
# ---------------------------------------------------------------------------


@router.get("/observatory/summary")
def get_observatory_summary(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_ai_observatory_service.observatory_summary(db, tenant_id)


@router.post("/observatory/latency", status_code=201)
def post_latency_sample(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    try:
        return phoenix_ai_observatory_service.record_latency_sample(
            db, tenant_id, stage=payload.get("stage", ""), latency_ms=payload.get("latency_ms", 0.0),
            inspection_id=payload.get("inspection_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/observatory/latency")
def get_latency_summary(stage: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_ai_observatory_service.latency_summary(db, tenant_id, stage=stage)


@router.get("/observatory/coverage")
def get_coverage_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_ai_observatory_service.coverage_summary(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 4 — Workflow Optimization Engine
# ---------------------------------------------------------------------------


@router.get("/workflow-optimization/summary")
def get_workflow_optimization_summary(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_workflow_optimization_service.workflow_optimization_summary(db, tenant_id)


@router.get("/workflow-optimization/{workflow_id}")
def get_workflow_optimization_recommendation(workflow_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_workflow_optimization_service.recommend_workflow_optimization(db, tenant_id, workflow_id)


# ---------------------------------------------------------------------------
# Section 5 — Knowledge Evolution Center
# ---------------------------------------------------------------------------


@router.get("/knowledge-evolution/summary")
def get_knowledge_evolution_summary(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_knowledge_evolution_service.knowledge_evolution_summary(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 6 — Competency Intelligence
# ---------------------------------------------------------------------------


@router.post("/competency-intelligence/run")
def post_run_competency_intelligence(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = phoenix_competency_intelligence_service.run_all_detectors(db, tenant_id)
    _audit(db, tenant_id, actor, "phoenix.competency_intelligence_run", "quality_competency_opportunities", "", {})
    return result


@router.get("/competency-intelligence/opportunities")
def get_competency_opportunities(status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    from app.services.competency_intelligence_service import list_opportunities

    return {"opportunities": list_opportunities(db, tenant_id, status=status)}


# ---------------------------------------------------------------------------
# Section 7 — Platform Health Dashboard
# ---------------------------------------------------------------------------


@router.get("/platform-health/dashboard")
def get_platform_health_dashboard(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_platform_health_service.platform_health_dashboard(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 8 — Innovation Pipeline
# ---------------------------------------------------------------------------


@router.post("/innovation/ideas", status_code=201)
def post_innovation_idea(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = phoenix_innovation_pipeline_service.create_idea(
            db, tenant_id, title=payload.get("title", ""), description=payload.get("description", ""),
            evidence=payload.get("evidence", ""), estimated_roi_usd=payload.get("estimated_roi_usd"),
            clinical_impact=payload.get("clinical_impact", "medium"), technical_complexity=payload.get("technical_complexity", "medium"),
            priority=payload.get("priority", "medium"), submitted_by=payload.get("submitted_by", actor),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "phoenix.innovation_idea_created", "phoenix_innovation_ideas", str(result["id"]), {"title": result["title"]})
    return result


@router.get("/innovation/ideas")
def get_innovation_ideas(approval_status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {"ideas": phoenix_innovation_pipeline_service.list_ideas(db, tenant_id, approval_status=approval_status)}


@router.get("/innovation/summary")
def get_innovation_summary(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_innovation_pipeline_service.pipeline_summary(db, tenant_id)


@router.get("/innovation/ideas/{idea_id}")
def get_innovation_idea(idea_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    try:
        return phoenix_innovation_pipeline_service.get_idea(db, tenant_id, idea_id)
    except phoenix_innovation_pipeline_service.InnovationIdeaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/innovation/ideas/{idea_id}/status")
def patch_innovation_idea_status(idea_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = phoenix_innovation_pipeline_service.update_idea_status(
            db, tenant_id, idea_id, approval_status=payload.get("approval_status", ""),
            roadmap_assignment=payload.get("roadmap_assignment", ""),
        )
    except phoenix_innovation_pipeline_service.InnovationIdeaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "phoenix.innovation_idea_status_changed", "phoenix_innovation_ideas", str(idea_id), {"approval_status": result["approval_status"]})
    return result


# ---------------------------------------------------------------------------
# Section 9 — Continuous Validation
# ---------------------------------------------------------------------------


@router.post("/recommendations/{recommendation_id}/validation/start")
def post_start_validation(recommendation_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = phoenix_validation_pipeline_service.start_validation(db, tenant_id, recommendation_id)
    except phoenix_validation_pipeline_service.RecommendationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "phoenix.validation_started", "phoenix_improvement_recommendations", str(recommendation_id), {})
    return result


@router.post("/recommendations/{recommendation_id}/validation/advance")
def post_advance_validation(recommendation_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = phoenix_validation_pipeline_service.advance_validation(
            db, tenant_id, recommendation_id, decided_by=actor, decided_role=payload.get("decided_role", ""),
            decision=payload.get("decision", ""), notes=payload.get("notes", ""),
            outcome_notes=payload.get("outcome_notes", ""), lessons_learned=payload.get("lessons_learned", ""),
            measured_impact=payload.get("measured_impact", ""),
        )
    except phoenix_validation_pipeline_service.RecommendationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "phoenix.validation_advanced", "phoenix_improvement_recommendations", str(recommendation_id), {"decision": payload.get("decision", "")})
    return result


@router.post("/recommendations/{recommendation_id}/validation/outcomes", status_code=201)
def post_validation_outcome(recommendation_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        return phoenix_validation_pipeline_service.record_outcome(
            db, tenant_id, recommendation_id, stage=payload.get("stage", ""), outcome_notes=payload.get("outcome_notes", ""),
            lessons_learned=payload.get("lessons_learned", ""), measured_impact=payload.get("measured_impact", ""),
            recorded_by=actor,
        )
    except phoenix_validation_pipeline_service.RecommendationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/recommendations/{recommendation_id}/validation")
def get_validation_status(recommendation_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    try:
        return phoenix_validation_pipeline_service.get_validation_status(db, tenant_id, recommendation_id)
    except phoenix_validation_pipeline_service.RecommendationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 10 — Platform Maturity Index
# ---------------------------------------------------------------------------


@router.post("/maturity/compute")
def post_compute_maturity_index(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return phoenix_maturity_index_service.compute_platform_maturity_index(db, tenant_id)


@router.get("/maturity/history")
def get_maturity_history(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {"history": phoenix_maturity_index_service.maturity_history(db, tenant_id)}
