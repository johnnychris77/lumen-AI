"""Advisor — Phase 7: Supervised Advisory Pilot & Human-AI Collaboration API.

Recommendation presentation, technician interaction logging, workflow
impact, clinical performance, user feedback, safety monitoring, the pilot
dashboard, and success metrics. Nothing here can drive or auto-approve a
clinical or operational decision — every route reads or records evidence
for a human decision, never makes one.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.advisory_pilot import AdvisorySafetyEvent
from app.models.model_registry import ModelRegistryEntry
from app.models.supervisor_review import SupervisorReview
from app.services import (
    advisory_clinical_performance_service,
    advisory_pilot_dashboard_service,
    advisory_recommendation_service,
    advisory_safety_service,
    advisory_success_metrics_service,
    advisory_user_feedback_service,
    advisory_workflow_impact_service,
    pilot_service,
)
from app.services.enterprise_audit_service import record_enterprise_audit_event
from app.services.ml import candidate_promotion
from app.services.ml.candidate_training import CANDIDATE_CLASSES

router = APIRouter(tags=["advisory-pilot"])


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


# ── §2 — Pilot Governance ────────────────────────────────────────────────────

class AdvisoryPilotGovernanceIn(BaseModel):
    facility_id: str = Field(..., min_length=1, max_length=100)
    organization: str = Field("", max_length=255)
    department: str = Field("", max_length=255)
    pilot_sponsor: str = Field("", max_length=255)
    clinical_lead: str = Field("", max_length=255)
    quality_lead: str = Field("", max_length=255)
    product_owner: str = Field("", max_length=255)
    engineering_lead: str = Field("", max_length=255)
    success_criteria: str = ""
    agreed_kpis: dict = Field(default_factory=dict)
    pilot_duration_days: int | None = None


@router.post("/advisory-pilot/governance", status_code=201)
def register_pilot_governance(
    body: AdvisoryPilotGovernanceIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    row = pilot_service.start_pilot(
        db, tenant_id, body.facility_id, body.agreed_kpis,
        organization=body.organization, department=body.department,
        clinical_lead=body.clinical_lead, quality_lead=body.quality_lead,
        pilot_sponsor=body.pilot_sponsor, product_owner=body.product_owner,
        engineering_lead=body.engineering_lead, success_criteria=body.success_criteria,
        pilot_duration_days=body.pilot_duration_days,
    )
    record_enterprise_audit_event(
        db, action_type="advisory_pilot_governance_registered", resource_type="pilot_status",
        resource_id=row.id, actor=_actor(current_user), actor_role=getattr(current_user, "role", ""),
        tenant_id=tenant_id,
    )
    return {
        "id": row.id, "facility_id": row.facility_id, "organization": row.organization,
        "department": row.department, "pilot_sponsor": row.pilot_sponsor,
        "clinical_lead": row.clinical_lead, "quality_lead": row.quality_lead,
        "product_owner": row.product_owner, "engineering_lead": row.engineering_lead,
        "success_criteria": row.success_criteria, "pilot_duration_days": row.pilot_duration_days,
    }


# ── §3/§4 — Advisory Mode recommendation + interaction logging ─────────────

class PresentRecommendationIn(BaseModel):
    predicted_class: str
    confidence: float
    model_version: str = ""
    image_quality: str = ""
    evidence_summary: str = ""
    supported_classes: list[str] = Field(default_factory=lambda: list(CANDIDATE_CLASSES))


@router.post("/advisory-pilot/recommendations/present")
def present_recommendation(
    body: PresentRecommendationIn, current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    return advisory_recommendation_service.present_recommendation(
        predicted_class=body.predicted_class, confidence=body.confidence, model_version=body.model_version,
        image_quality=body.image_quality, supported_classes=body.supported_classes,
        evidence_summary=body.evidence_summary,
    )


class RecordInteractionIn(BaseModel):
    inspection_id: int
    model_id: str = Field("", max_length=100)
    model_version: str = Field("", max_length=50)
    predicted_label: str = Field(..., max_length=100)
    confidence: float | None = None
    decision: str = Field(..., description="accepted | modified | rejected")
    modified_to: str = Field("", max_length=100)
    reason_for_rejection: str = ""
    reviewer_comments: str = ""
    user_confidence_rating: int | None = Field(None, ge=1, le=5)


@router.post("/advisory-pilot/recommendations/respond", status_code=201)
def record_interaction(
    body: RecordInteractionIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator")),
):
    tenant_id = _tenant(current_user, request)
    try:
        row = advisory_recommendation_service.record_interaction(
            db, tenant_id=tenant_id, inspection_id=body.inspection_id, model_id=body.model_id,
            model_version=body.model_version, predicted_label=body.predicted_label, confidence=body.confidence,
            decision=body.decision, modified_to=body.modified_to, reason_for_rejection=body.reason_for_rejection,
            reviewer_comments=body.reviewer_comments, user_confidence_rating=body.user_confidence_rating,
            decided_by=_actor(current_user), decided_role=getattr(current_user, "role", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record_enterprise_audit_event(
        db, action_type=f"advisory_recommendation_{body.decision}", resource_type="inspection",
        resource_id=body.inspection_id, actor=_actor(current_user), actor_role=getattr(current_user, "role", ""),
        tenant_id=tenant_id,
    )
    return {
        "id": row.id, "inspection_id": row.inspection_id, "decision": row.decision,
        "modified_to": row.modified_to, "reason_for_rejection": row.reason_for_rejection,
        "user_confidence_rating": row.user_confidence_rating,
        "time_to_decision_seconds": row.time_to_decision_seconds,
    }


@router.get("/advisory-pilot/recommendations")
def list_interactions(
    request: Request, model_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    rows = advisory_recommendation_service.list_interactions(db, tenant_id, model_id=model_id or None)
    return {
        "count": len(rows),
        "interactions": [
            {"id": r.id, "inspection_id": r.inspection_id, "decision": r.decision,
             "predicted_label": r.predicted_label, "confidence": r.confidence,
             "decided_by": r.decided_by, "created_at": r.created_at.isoformat()}
            for r in rows
        ],
    }


# ── §5 — Workflow Impact Analysis ───────────────────────────────────────────

@router.get("/advisory-pilot/workflow-impact")
def workflow_impact(
    request: Request, model_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    interactions = advisory_recommendation_service.list_interactions(db, tenant_id, model_id=model_id or None)
    return advisory_workflow_impact_service.impact_summary(db, tenant_id, interactions, model_id=model_id or None)


# ── §6 — Clinical Performance ────────────────────────────────────────────────

@router.get("/advisory-pilot/clinical-performance")
def clinical_performance(
    request: Request, model_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    interactions = advisory_recommendation_service.list_interactions(db, tenant_id, model_id=model_id or None)
    presentations = [
        advisory_recommendation_service.present_recommendation(
            predicted_class=i.predicted_label, confidence=i.confidence or 0.0, model_version=i.model_version,
            image_quality="", supported_classes=list(CANDIDATE_CLASSES),
        )
        for i in interactions
    ]
    return advisory_clinical_performance_service.performance_summary(reviews, presentations)


# ── §7 — User Experience feedback ───────────────────────────────────────────

class UserFeedbackIn(BaseModel):
    submitted_by: str = Field(..., max_length=255)
    submitted_role: str = Field(..., description="technician | supervisor | manager | quality | biomedical_engineering")
    ease_of_use: int | None = Field(None, ge=1, le=5)
    trust: int | None = Field(None, ge=1, le=5)
    clarity: int | None = Field(None, ge=1, le=5)
    explainability_rating: int | None = Field(None, ge=1, le=5)
    confidence: int | None = Field(None, ge=1, le=5)
    perceived_value: int | None = Field(None, ge=1, le=5)
    suggestions: str = ""


@router.post("/advisory-pilot/feedback", status_code=201)
def submit_feedback(
    body: UserFeedbackIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    row = advisory_user_feedback_service.record_feedback(
        db, tenant_id=tenant_id, submitted_by=body.submitted_by, submitted_role=body.submitted_role,
        ease_of_use=body.ease_of_use, trust=body.trust, clarity=body.clarity,
        explainability_rating=body.explainability_rating, confidence=body.confidence,
        perceived_value=body.perceived_value, suggestions=body.suggestions,
    )
    return {"id": row.id, "submitted_role": row.submitted_role}


@router.get("/advisory-pilot/feedback/summary")
def feedback_summary(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    return advisory_user_feedback_service.feedback_summary(db, tenant_id)


# ── §8 — Safety Monitoring ───────────────────────────────────────────────────

class SafetyEventIn(BaseModel):
    model_id: str = Field("", max_length=100)
    event_type: str
    inspection_id: int | None = None
    description: str = ""
    severity: str = Field("medium", description="low | medium | high | critical")


@router.post("/advisory-pilot/safety-events", status_code=201)
def report_safety_event(
    body: SafetyEventIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    try:
        row = advisory_safety_service.report_event(
            db, tenant_id=tenant_id, model_id=body.model_id, event_type=body.event_type,
            inspection_id=body.inspection_id, description=body.description, severity=body.severity,
            reported_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record_enterprise_audit_event(
        db, action_type="advisory_safety_event_reported", resource_type="advisory_safety_event",
        resource_id=row.id, actor=_actor(current_user), actor_role=getattr(current_user, "role", ""),
        tenant_id=tenant_id, compliance_flag=True,
    )
    return {"id": row.id, "event_type": row.event_type, "severity": row.severity}


class ReviewSafetyEventIn(BaseModel):
    resolution_notes: str = ""


@router.post("/advisory-pilot/safety-events/{event_id}/review")
def review_safety_event(
    event_id: int, body: ReviewSafetyEventIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    event = (
        db.query(AdvisorySafetyEvent)
        .filter(AdvisorySafetyEvent.id == event_id, AdvisorySafetyEvent.tenant_id == tenant_id)
        .first()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Safety event not found.")
    event = advisory_safety_service.review_event(
        db, event, reviewed_by=_actor(current_user), resolution_notes=body.resolution_notes,
    )
    return {"id": event.id, "reviewed": event.reviewed, "reviewed_by": event.reviewed_by}


@router.get("/advisory-pilot/safety-events/summary")
def safety_summary(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    return advisory_safety_service.safety_summary(db, tenant_id)


# ── §9 — Pilot Dashboard ─────────────────────────────────────────────────────

@router.get("/advisory-pilot/dashboard")
def dashboard(
    request: Request, model_id: str = "", facility_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant(current_user, request)
    return advisory_pilot_dashboard_service.pilot_dashboard(
        db, tenant_id, model_id=model_id or None, facility_id=facility_id,
    )


# ── §10 — Success Metrics ────────────────────────────────────────────────────

@router.get("/advisory-pilot/success-metrics")
def success_metrics(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    return advisory_success_metrics_service.success_metrics(db, tenant_id)


# ── §13 — Pilot Final Report + Production promotion gate ───────────────────

@router.get("/advisory-pilot/final-report")
def final_report(
    request: Request, model_db_id: int, facility_id: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """§13 — assembles every gate item's real evidence into one report:
    the pilot dashboard, success metrics, safety summary, user feedback
    summary, and the Pilot -> Production promotion checklist preview for
    the named model. Nothing here writes anything — this is the read-only
    evidence package the Clinical Review Board and customer/governance
    approvers use to decide."""
    tenant_id = _tenant(current_user, request)
    model = (
        db.query(ModelRegistryEntry)
        .filter(ModelRegistryEntry.id == model_db_id, ModelRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found.")

    return {
        "model_id": model.model_id,
        "model_version": model.model_version,
        "candidate_stage": model.candidate_stage,
        "pilot_dashboard": advisory_pilot_dashboard_service.pilot_dashboard(
            db, tenant_id, model_id=model.model_id, facility_id=facility_id,
        ),
        "success_metrics": advisory_success_metrics_service.success_metrics(db, tenant_id),
        "safety_summary": advisory_safety_service.safety_summary(db, tenant_id),
        "user_feedback_summary": advisory_user_feedback_service.feedback_summary(db, tenant_id),
        "production_promotion_checklist": candidate_promotion.evaluate_production_checklist(db, model),
        "human_review_required": True,
    }
