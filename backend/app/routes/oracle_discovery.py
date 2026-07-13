"""Project Oracle: Clinical Intelligence Scientist & Discovery Engine routes.

Frontend route: /oracle. API prefix: /api/oracle.

Uses `tenant_authz.require_tenant_roles` for tenant-scoped access -- every
query below filters by the authenticated user's own `tenant_id`. Approving
or rejecting a knowledge suggestion requires a leadership role
(`_LEADERSHIP_ROLES`); promoting a hypothesis to `PRODUCTION_KNOWLEDGE` is
additionally tier-checked inside `oracle_validation_pipeline_service`, the
same "route-level RBAC + service-level tier gate" pattern Steward uses.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services import (
    oracle_collaboration_service,
    oracle_digital_twin_research_service,
    oracle_hypothesis_service,
    oracle_innovation_dashboard_service,
    oracle_knowledge_evolution_service,
    oracle_model_observatory_service,
    oracle_registry_service,
    oracle_trend_detection_service,
    oracle_validation_pipeline_service,
    oracle_workspace_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/oracle", tags=["oracle"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _tenant_name(current_user: dict) -> str:
    return current_user.get("tenant_name", "")


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


def _role(current_user: dict) -> str:
    return current_user["role"] or "viewer"


# ---------------------------------------------------------------------------
# Sections 3 & 5 — Hypotheses (Discovery Engine / Hypothesis Generator)
# ---------------------------------------------------------------------------


@router.post("/hypotheses", status_code=201)
def post_create_hypothesis(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_hypothesis_service.create_hypothesis(
            db, _tenant(current_user), changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


@router.get("/hypotheses")
def get_hypotheses(
    discovery_category: str = Query(""), current_stage: str = Query(""), confidence_level: str = Query(""),
    research_owner: str = Query(""), outcome: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"hypotheses": oracle_hypothesis_service.list_hypotheses(
        db, _tenant(current_user), discovery_category=discovery_category, current_stage=current_stage,
        confidence_level=confidence_level, research_owner=research_owner, outcome=outcome,
    )}


@router.get("/hypotheses/{hypothesis_id}")
def get_hypothesis_detail(hypothesis_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    row = oracle_hypothesis_service.get_hypothesis(db, tenant_id, hypothesis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return {
        "hypothesis": oracle_hypothesis_service.to_dict(row),
        "stage_history": oracle_validation_pipeline_service.stage_history(db, tenant_id, hypothesis_id),
    }


@router.post("/hypotheses/{hypothesis_id}/evidence", status_code=201)
def post_add_evidence(hypothesis_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_hypothesis_service.add_evidence(db, _tenant(current_user), hypothesis_id, submitted_by=_actor(current_user), **payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


@router.post("/hypotheses/{hypothesis_id}/literature", status_code=201)
def post_link_literature(hypothesis_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_hypothesis_service.link_supporting_literature(db, _tenant(current_user), hypothesis_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


@router.post("/hypotheses/{hypothesis_id}/confidence")
def post_set_confidence(hypothesis_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_hypothesis_service.set_confidence_level(
            db, _tenant(current_user), hypothesis_id, changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 10 — Validation pipeline
# ---------------------------------------------------------------------------


@router.post("/hypotheses/{hypothesis_id}/advance")
def post_advance_stage(hypothesis_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_validation_pipeline_service.advance_stage(
            db, _tenant(current_user), hypothesis_id, changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


@router.post("/hypotheses/{hypothesis_id}/close")
def post_close_out(hypothesis_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_validation_pipeline_service.close_out_hypothesis(
            db, _tenant(current_user), hypothesis_id, changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 12 — Research collaboration
# ---------------------------------------------------------------------------


@router.post("/hypotheses/{hypothesis_id}/reassign-owner")
def post_reassign_owner(hypothesis_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_collaboration_service.reassign_research_owner(
            db, _tenant(current_user), hypothesis_id, changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


@router.post("/hypotheses/{hypothesis_id}/comments", status_code=201)
def post_add_comment(hypothesis_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_collaboration_service.add_discussion_comment(
            db, _tenant(current_user), hypothesis_id, submitted_by=_actor(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 4 — Emerging trend detection
# ---------------------------------------------------------------------------


@router.post("/trends/detect", status_code=201)
def post_detect_trend(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_trend_detection_service.detect_finding_rate_trend(db, _tenant(current_user), **payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_trend_detection_service.to_dict(row)


@router.get("/trends")
def get_trends(
    trend_category: str = Query(""), direction: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"trends": oracle_trend_detection_service.list_trend_observations(
        db, _tenant(current_user), trend_category=trend_category, direction=direction,
    )}


@router.post("/trends/{trend_id}/promote", status_code=201)
def post_promote_trend(trend_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_trend_detection_service.promote_to_hypothesis(
            db, _tenant(current_user), trend_id, changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 5 — Digital twin research
# ---------------------------------------------------------------------------


@router.post("/digital-twin/apollo", status_code=201)
def post_record_apollo_insight(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    row = oracle_digital_twin_research_service.record_apollo_insight(db, _tenant(current_user), **payload)
    return oracle_digital_twin_research_service.to_dict(row)


@router.post("/digital-twin/vulcan", status_code=201)
def post_record_vulcan_insight(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    instrument_identity = payload.pop("instrument_identity")
    row = oracle_digital_twin_research_service.record_vulcan_insight(db, _tenant(current_user), instrument_identity, **payload)
    return oracle_digital_twin_research_service.to_dict(row)


@router.get("/digital-twin")
def get_digital_twin_insights(
    source_service: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"insights": oracle_digital_twin_research_service.list_insights(db, _tenant(current_user), source_service=source_service)}


@router.post("/digital-twin/{insight_id}/promote", status_code=201)
def post_promote_twin_insight(insight_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_digital_twin_research_service.promote_to_hypothesis(
            db, _tenant(current_user), insight_id, changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 7 — AI Model Observatory
# ---------------------------------------------------------------------------


@router.post("/model-observations", status_code=201)
def post_record_model_observation(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    row = oracle_model_observatory_service.record_observation(db, _tenant(current_user), **payload)
    return oracle_model_observatory_service.to_dict(row)


@router.get("/model-observations")
def get_model_observations(
    observation_type: str = Query(""), reviewed: bool | None = Query(None),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"observations": oracle_model_observatory_service.list_observations(
        db, _tenant(current_user), observation_type=observation_type, reviewed=reviewed,
    )}


@router.post("/model-observations/{observation_id}/review")
def post_review_model_observation(observation_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_model_observatory_service.mark_reviewed(db, _tenant(current_user), observation_id, reviewed_by=_actor(current_user))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_model_observatory_service.to_dict(row)


@router.post("/model-observations/{observation_id}/promote", status_code=201)
def post_promote_model_observation(observation_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_model_observatory_service.promote_to_hypothesis(
            db, _tenant(current_user), observation_id, changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_hypothesis_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 6 — Knowledge evolution
# ---------------------------------------------------------------------------


@router.post("/knowledge-suggestions", status_code=201)
def post_create_knowledge_suggestion(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_knowledge_evolution_service.create_suggestion(
            db, _tenant(current_user), _tenant_name(current_user), submitted_by=_actor(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_knowledge_evolution_service.to_dict(row)


@router.get("/knowledge-suggestions")
def get_knowledge_suggestions(
    status: str = Query(""), hypothesis_id: int | None = Query(None),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"suggestions": oracle_knowledge_evolution_service.list_suggestions(
        db, _tenant(current_user), status=status, hypothesis_id=hypothesis_id,
    )}


@router.post("/knowledge-suggestions/{suggestion_id}/approve")
def post_approve_knowledge_suggestion(
    suggestion_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        row = oracle_knowledge_evolution_service.approve_suggestion(
            db, _tenant(current_user), suggestion_id, reviewer=_actor(current_user), reviewer_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_knowledge_evolution_service.to_dict(row)


@router.post("/knowledge-suggestions/{suggestion_id}/reject")
def post_reject_knowledge_suggestion(
    suggestion_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        row = oracle_knowledge_evolution_service.reject_suggestion(
            db, _tenant(current_user), suggestion_id, reviewer=_actor(current_user), reviewer_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_knowledge_evolution_service.to_dict(row)


@router.post("/knowledge-suggestions/{suggestion_id}/publish")
def post_publish_knowledge_suggestion(suggestion_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        row = oracle_knowledge_evolution_service.mark_published(db, _tenant(current_user), suggestion_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return oracle_knowledge_evolution_service.to_dict(row)


# ---------------------------------------------------------------------------
# Sections 9, 13, 14 — Research workspace, registry, executive dashboard
# ---------------------------------------------------------------------------


@router.get("/workspace")
def get_workspace(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return oracle_workspace_service.workspace_summary(db, _tenant(current_user))


@router.get("/registry/search")
def get_registry_search(
    query: str = Query(""), discovery_category: str = Query(""), confidence_level: str = Query(""),
    current_stage: str = Query(""), outcome: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"results": oracle_registry_service.search_registry(
        db, _tenant(current_user), query=query, discovery_category=discovery_category,
        confidence_level=confidence_level, current_stage=current_stage, outcome=outcome,
    )}


@router.get("/registry/summary")
def get_registry_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return oracle_registry_service.registry_summary(db, _tenant(current_user))


@router.get("/dashboard")
def get_innovation_dashboard(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return oracle_innovation_dashboard_service.innovation_dashboard(db, _tenant(current_user))
