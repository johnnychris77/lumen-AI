"""LumenAI AI Specialist — Project Sage: SPD Education, Competency &
Workforce Intelligence routes.

Frontend routes: /sage (leadership/educator workspace), /my-learning
(technician self-view). API prefix: /api/sage.

Uses `tenant_authz.require_tenant_roles`, consistent with every sprint since
Athena (v4.8). Individual-level competency/learning data (gaps, learning
plans, assessments, executive summary) is leadership-only
(`_LEADERSHIP_ROLES`) per Section 16 -- a viewer/operator may only ever see
their OWN data, via `/my-learning`, which resolves the learner identity from
the authenticated user, never from a client-supplied technician parameter.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.vulcan_reliability import VulcanReliabilityAssessment
from app.services import (
    sage_aegis_vulcan_integration_service,
    sage_assessment_service,
    sage_athena_apollo_integration_service,
    sage_competency_taxonomy_service,
    sage_effectiveness_service,
    sage_executive_intelligence_service,
    sage_feedback_service,
    sage_image_library_service,
    sage_knowledge_gap_service,
    sage_learning_plan_service,
    sage_microlearning_service,
    sage_my_learning_service,
    sage_workforce_privacy_service,
    sage_workspace_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/sage", tags=["sage"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Section 2 — Competency Taxonomy
# ---------------------------------------------------------------------------


@router.get("/taxonomy")
def get_taxonomy(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES))):
    return sage_competency_taxonomy_service.taxonomy_tree()


# ---------------------------------------------------------------------------
# Section 3 — Competency Gap Detection (leadership-only: individual data)
# ---------------------------------------------------------------------------


@router.post("/gaps/detect/{technician}", status_code=201)
def post_detect_gaps(
    technician: str, window_days: int = Query(90),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    tenant_id = _tenant(current_user)
    sage_workforce_privacy_service.log_individual_access(
        db, tenant_id, viewer=_actor(current_user), viewer_role=current_user.get("role", ""),
        subject=technician, resource_type="sage_knowledge_gap",
    )
    return {"gaps": sage_knowledge_gap_service.run_gap_detection_for_technician(db, tenant_id, technician, window_days)}


@router.get("/gaps")
def get_gaps(
    competency_domain: str = Query(""), scope_type: str = Query(""), scope_value: str = Query(""),
    instrument_family: str = Query(""), anatomy_zone: str = Query(""), status: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    return {
        "gaps": sage_knowledge_gap_service.list_gaps(
            db, _tenant(current_user), competency_domain=competency_domain, scope_type=scope_type,
            scope_value=scope_value, instrument_family=instrument_family, anatomy_zone=anatomy_zone, status=status,
        )
    }


# ---------------------------------------------------------------------------
# Section 5 — Adaptive Learning Plans (leadership-only to create/manage)
# ---------------------------------------------------------------------------


@router.post("/learning-plans", status_code=201)
def post_learning_plan(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    due_date = payload.get("due_date")
    row = sage_learning_plan_service.create_learning_plan(
        db, _tenant(current_user), learner_or_group=payload.get("learner_or_group", ""), created_by=_actor(current_user),
        knowledge_gap_id=payload.get("knowledge_gap_id"), scope_type=payload.get("scope_type", "individual"),
        identified_need=payload.get("identified_need", ""), supporting_evidence=payload.get("supporting_evidence"),
        learning_objective=payload.get("learning_objective", ""), instrument_family=payload.get("instrument_family", ""),
        anatomy_zone=payload.get("anatomy_zone", ""), finding_category=payload.get("finding_category", ""),
        education_content=payload.get("education_content", ""), microlearning_module_id=payload.get("microlearning_module_id"),
        practice_activity=payload.get("practice_activity", ""),
        return_demonstration_required=bool(payload.get("return_demonstration_required", False)),
        evaluator=payload.get("evaluator", ""), due_date=datetime.fromisoformat(due_date) if due_date else None,
        confidence=payload.get("confidence", "moderate"),
    )
    return sage_learning_plan_service.to_dict(row)


@router.post("/learning-plans/{plan_id}/approve")
def post_approve_plan(plan_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sage_learning_plan_service.approve_learning_plan(db, _tenant(current_user), plan_id, approved_by=_actor(current_user))
    if row is None:
        raise HTTPException(status_code=404, detail="Learning plan not found")
    return sage_learning_plan_service.to_dict(row)


@router.post("/learning-plans/{plan_id}/reject-or-edit")
def post_reject_or_edit_plan(plan_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = sage_learning_plan_service.reject_or_edit_learning_plan(
            db, _tenant(current_user), plan_id, acted_by=_actor(current_user), action=payload.get("action", "edit"),
            override_reason=payload.get("override_reason", ""), edits=payload.get("edits"),
        )
    except sage_learning_plan_service.OverrideReasonRequiredError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Learning plan not found")
    return sage_learning_plan_service.to_dict(row)


@router.post("/learning-plans/{plan_id}/complete")
def post_complete_plan(plan_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sage_learning_plan_service.mark_completed(db, _tenant(current_user), plan_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Learning plan not found")
    return sage_learning_plan_service.to_dict(row)


@router.get("/learning-plans")
def get_learning_plans(
    learner_or_group: str = Query(""), completion_status: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    return {"plans": sage_learning_plan_service.list_plans(db, _tenant(current_user), learner_or_group=learner_or_group, completion_status=completion_status)}


@router.get("/learning-plans/{plan_id}")
def get_learning_plan(plan_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sage_learning_plan_service.get_plan(db, _tenant(current_user), plan_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Learning plan not found")
    return row


# ---------------------------------------------------------------------------
# Section 6 — Microlearning Generator
# ---------------------------------------------------------------------------


@router.post("/microlearning/{finding_type}", status_code=201)
def post_build_module(
    finding_type: str, instrument_family: str = Query(""), anatomy_zone: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    row = sage_microlearning_service.build_module_from_finding(
        db, _tenant(current_user), finding_type, instrument_family=instrument_family, anatomy_zone=anatomy_zone,
    )
    if row is None:
        raise HTTPException(status_code=422, detail=f"'{finding_type}' is not an approved knowledge-library category")
    return sage_microlearning_service._to_dict(row)


@router.post("/microlearning/{module_id}/approve")
def post_approve_module(module_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sage_microlearning_service.approve_module(db, _tenant(current_user), module_id, approved_by=_actor(current_user))
    if row is None:
        raise HTTPException(status_code=404, detail="Microlearning module not found")
    return sage_microlearning_service._to_dict(row)


@router.get("/microlearning")
def get_modules(approval_status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"modules": sage_microlearning_service.list_modules(db, _tenant(current_user), approval_status=approval_status)}


# ---------------------------------------------------------------------------
# Section 7 — Competency Assessment Builder
# ---------------------------------------------------------------------------


@router.post("/assessments", status_code=201)
def post_assessment(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = sage_assessment_service.create_assessment(
            db, _tenant(current_user), assessment_format=payload.get("assessment_format", ""),
            target_learner=payload.get("target_learner", ""), competency_domain=payload.get("competency_domain", ""),
            content=payload.get("content"), learning_plan_id=payload.get("learning_plan_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sage_assessment_service.to_dict(row)


@router.post("/assessments/{assessment_id}/result")
def post_assessment_result(assessment_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sage_assessment_service.record_result(db, _tenant(current_user), assessment_id, result=payload.get("result", {}))
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return sage_assessment_service.to_dict(row)


@router.post("/assessments/{assessment_id}/validate")
def post_validate_assessment(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sage_assessment_service.validate_result(db, _tenant(current_user), assessment_id, validated_by=_actor(current_user))
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return sage_assessment_service.to_dict(row)


@router.get("/assessments")
def get_assessments(target_learner: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"assessments": sage_assessment_service.list_assessments(db, _tenant(current_user), target_learner=target_learner)}


# ---------------------------------------------------------------------------
# Section 8 — Image-Based Learning Library
# ---------------------------------------------------------------------------


@router.post("/images/{retained_image_id}/curate", status_code=201)
def post_curate_image(retained_image_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sage_image_library_service.curate_image_for_education(
        db, _tenant(current_user), retained_image_id, anatomy_zone=payload.get("anatomy_zone", ""),
        usage_rights=payload.get("usage_rights", "internal_education_use"), dataset_version=payload.get("dataset_version", "1.0.0"),
    )
    if row is None:
        raise HTTPException(status_code=422, detail="Image is not consented and gold-labeled; cannot curate for education")
    return sage_image_library_service.to_dict(row)


@router.post("/images/{entry_id}/phi-review")
def post_phi_review(entry_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sage_image_library_service.mark_phi_reviewed(db, _tenant(current_user), entry_id, cleared=bool(payload.get("cleared", False)))
    if row is None:
        raise HTTPException(status_code=404, detail="Education image entry not found")
    return sage_image_library_service.to_dict(row)


@router.get("/images")
def get_images(
    instrument_family: str = Query(""), anatomy_zone: str = Query(""), finding_category: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {
        "images": sage_image_library_service.list_education_images(
            db, _tenant(current_user), instrument_family=instrument_family, anatomy_zone=anatomy_zone,
            finding_category=finding_category, phi_cleared_only=True,
        )
    }


# ---------------------------------------------------------------------------
# Section 9 — Learning Effectiveness Engine
# ---------------------------------------------------------------------------


@router.post("/learning-plans/{plan_id}/measure-effectiveness", status_code=201)
def post_measure_effectiveness(
    plan_id: int, window_days: int = Query(30),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    from app.models.sage_education import SageLearningPlan
    plan = db.query(SageLearningPlan).filter(SageLearningPlan.id == plan_id, SageLearningPlan.tenant_id == _tenant(current_user)).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Learning plan not found")
    if plan.completion_status != "completed":
        raise HTTPException(status_code=422, detail="Effectiveness can only be measured for a completed learning plan")
    row = sage_effectiveness_service.measure_learning_plan_effectiveness(db, _tenant(current_user), plan, window_days=window_days)
    plan.effectiveness_assessment_id = row.id
    db.commit()
    return sage_effectiveness_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 10 — Sage Workspace
# ---------------------------------------------------------------------------


@router.get("/workspace")
def get_workspace(
    instrument_family: str = Query(""), anatomy_zone: str = Query(""), competency_domain: str = Query(""),
    learner_or_group: str = Query(""), shift: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    return sage_workspace_service.workspace_summary(
        db, _tenant(current_user), instrument_family=instrument_family, anatomy_zone=anatomy_zone,
        competency_domain=competency_domain, learner_or_group=learner_or_group, shift=shift,
    )


# ---------------------------------------------------------------------------
# Section 11 — Technician Learning Center (`/my-learning`)
# ---------------------------------------------------------------------------


@router.get("/my-learning")
def get_my_learning(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    """Always resolves the learner from the AUTHENTICATED identity -- never
    from a client-supplied parameter, so a technician can never view a
    peer's learning data through this endpoint."""
    return sage_my_learning_service.my_learning_center(db, _tenant(current_user), _actor(current_user))


# ---------------------------------------------------------------------------
# Section 12 — Educator and Supervisor Feedback
# ---------------------------------------------------------------------------


@router.post("/feedback", status_code=201)
def post_feedback(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = sage_feedback_service.record_feedback(
            db, _tenant(current_user), action=payload.get("action", ""), submitted_by=_actor(current_user),
            submitted_role=current_user.get("role", ""), learning_plan_id=payload.get("learning_plan_id"),
            knowledge_gap_id=payload.get("knowledge_gap_id"), comment=payload.get("comment", ""),
            override_reason=payload.get("override_reason", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sage_feedback_service.to_dict(row)


@router.get("/feedback/{plan_id}")
def get_feedback(plan_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"feedback": sage_feedback_service.feedback_for_plan(db, _tenant(current_user), plan_id)}


# ---------------------------------------------------------------------------
# Sections 13, 14 — Aegis / Vulcan Integration
# ---------------------------------------------------------------------------


@router.get("/aegis-recommendation")
def get_aegis_recommendation(
    instrument_identity: str = Query(...), zone: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    return sage_aegis_vulcan_integration_service.sage_recommendation_from_aegis(db, _tenant(current_user), instrument_identity, zone=zone or None)


@router.get("/vulcan-recommendation/{assessment_id}")
def get_vulcan_recommendation(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    assessment = (
        db.query(VulcanReliabilityAssessment)
        .filter(VulcanReliabilityAssessment.id == assessment_id, VulcanReliabilityAssessment.tenant_id == _tenant(current_user))
        .first()
    )
    if assessment is None:
        raise HTTPException(status_code=404, detail="Vulcan reliability assessment not found")
    return sage_aegis_vulcan_integration_service.sage_recommendation_from_vulcan(assessment)


# ---------------------------------------------------------------------------
# Section 15 — Athena and Apollo Integration
# ---------------------------------------------------------------------------


@router.get("/institutional-content")
def get_institutional_content(query: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"entries": sage_athena_apollo_integration_service.approved_institutional_content(db, _tenant(current_user), query=query)}


@router.get("/department-competency-evidence")
def get_department_competency_evidence(
    department: str = Query("unspecified"),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    result = sage_athena_apollo_integration_service.department_competency_evidence(db, _tenant(current_user), department)
    return result or {"department": department, "competency_score": None, "education_score": None, "snapshot_created_at": None}


# ---------------------------------------------------------------------------
# Section 18 — Executive Workforce Intelligence
# ---------------------------------------------------------------------------


@router.get("/executive-summary")
def get_executive_summary(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return sage_executive_intelligence_service.executive_workforce_intelligence(db, _tenant(current_user))
