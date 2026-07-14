"""Routes for the Lumen Decision Engine & Observation Doctrine.

Exposes:
  - GET  /api/inspections/{id}/decision — fetch the persisted Result Contract
  - POST /api/decision-policies                     — create a draft policy
  - GET  /api/decision-policies                      — list this tenant's policies
  - POST /api/decision-policies/{id}/submit          — submit for approval
  - POST /api/decision-policies/{id}/approve         — approve
  - POST /api/decision-policies/{id}/activate        — publish/activate
  - POST /api/decision-policies/{id}/archive         — archive
  - POST /api/decision-policies/{id}/reject          — reject
  - POST /api/decision-policies/simulate             — Section 9 simulation
  - GET  /api/unknown-findings                       — list unknown-finding reviews
  - POST /api/unknown-findings/{id}/classify         — supervisor classification
  - POST /api/unknown-findings/{id}/second-review    — second expert validation

Section 8 — technicians (`operator`) and viewers may never publish or
modify a policy; every write route below requires admin or spd_manager.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.models.lumen_decision_engine import BaselineDecisionPolicy, UnknownFindingReview
from app.services import baseline_decision_policy_service as policy_service
from app.services import lumen_decision_engine as decision_engine
from app.services import policy_simulation_service, unknown_finding_service

router = APIRouter(tags=["lumen-decision-engine"])


def _tenant_of(current_user) -> str:
    return getattr(current_user, "tenant_id", None) or "default-tenant"


@router.get("/inspections/{inspection_id}/decision")
async def get_inspection_decision(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant_of(current_user)
    row = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")
    if getattr(current_user, "role", "") != "admin" and row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Inspection not found")

    record = decision_engine.get_record_for_inspection(db, inspection_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="No Lumen Decision Engine record exists for this inspection.",
        )
    return _record_to_dict(record)


def _record_to_dict(record) -> dict:
    import json as _json

    return {
        "inspection_id": record.inspection_id,
        "observation": {
            "category": record.observation_category,
            "display_label": record.observation_display_label,
            "confidence": record.observation_confidence,
            "status": record.observation_status,
        },
        "assessment": {
            "image_quality": record.image_quality,
            "instrument_family": record.instrument_family,
            "anatomy_zone": record.anatomy_zone,
            "anatomy_zone_risk": record.anatomy_zone_risk,
            "baseline_similarity": record.baseline_similarity,
            "baseline_deviation": record.baseline_deviation,
            "baseline_source": record.baseline_source,
            "baseline_version": record.baseline_version,
            "digital_twin_trend": record.digital_twin_trend,
        },
        "policy": {
            "policy_id": record.policy_id,
            "policy_version": record.policy_version,
            "scope": record.policy_scope,
            "minimum_baseline_similarity": record.threshold_used,
        },
        "recommendation": {
            "action": record.recommended_action,
            "supervisor_required": record.supervisor_required,
            "reason": record.recommendation_reason,
            "escalation_condition": record.escalation_condition,
        },
        "limitations": _json.loads(record.limitations_json or "[]"),
        "human_decision_required": record.human_review_required,
        "human_followthrough": {
            "technician_action": record.technician_action,
            "technician_actor": record.technician_actor,
            "supervisor_action": record.supervisor_action,
            "supervisor_actor": record.supervisor_actor,
            "override_reason": record.override_reason,
            "final_human_decision": record.final_human_decision,
        },
    }


# ── Baseline Decision Policy CRUD (Section 5/8) ─────────────────────────────

class PolicyCreate(BaseModel):
    policy_id: Optional[str] = None
    scope: str
    scope_value: str = ""
    policy_name: str
    version: str = "1.0"
    baseline_source_requirement: str = "any_approved"
    pass_threshold: float = 0.90
    technician_review_threshold: float = 0.70
    supervisor_attention_threshold: float = 0.70
    supervisor_approval_threshold: float = 0.0
    approving_role: str = ""
    rationale: str = ""
    supporting_reference: str = ""
    previous_version_id: Optional[int] = None


def _actor_of(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


@router.post("/decision-policies", status_code=201)
async def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant_of(current_user)
    try:
        policy = policy_service.create_draft_policy(
            db, tenant_id=tenant_id, actor=_actor_of(current_user),
            actor_role=getattr(current_user, "role", "viewer"), fields=body.model_dump(),
        )
    except policy_service.PolicyGovernanceError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return _policy_dict(policy)


def _policy_dict(policy: BaselineDecisionPolicy) -> dict:
    return {
        "id": policy.id,
        "policy_id": policy.policy_id,
        "organization_id": policy.organization_id,
        "scope": policy.scope,
        "scope_value": policy.scope_value,
        "policy_name": policy.policy_name,
        "version": policy.version,
        "pass_threshold": policy.pass_threshold,
        "technician_review_threshold": policy.technician_review_threshold,
        "supervisor_attention_threshold": policy.supervisor_attention_threshold,
        "supervisor_approval_threshold": policy.supervisor_approval_threshold,
        "status": policy.status,
        "author": policy.author,
        "approved_by": policy.approved_by,
        "rationale": policy.rationale,
        "previous_version_id": policy.previous_version_id,
    }


@router.get("/decision-policies")
async def list_policies(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = _tenant_of(current_user)
    return [_policy_dict(p) for p in policy_service.list_policies(db, tenant_id=tenant_id)]


def _get_owned_policy(db: Session, policy_id: int, current_user) -> BaselineDecisionPolicy:
    tenant_id = _tenant_of(current_user)
    policy = db.query(BaselineDecisionPolicy).filter(BaselineDecisionPolicy.id == policy_id).first()
    if not policy or (getattr(current_user, "role", "") != "admin" and policy.organization_id != tenant_id):
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("/decision-policies/{policy_id}/submit")
async def submit_policy(
    policy_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    policy = _get_owned_policy(db, policy_id, current_user)
    try:
        policy = policy_service.submit_for_approval(db, policy, actor_role=getattr(current_user, "role", "viewer"))
    except policy_service.PolicyGovernanceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _policy_dict(policy)


@router.post("/decision-policies/{policy_id}/approve")
async def approve_policy_route(
    policy_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    policy = _get_owned_policy(db, policy_id, current_user)
    try:
        policy = policy_service.approve_policy(
            db, policy, actor=_actor_of(current_user), actor_role=getattr(current_user, "role", "viewer"),
        )
    except policy_service.PolicyGovernanceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _policy_dict(policy)


@router.post("/decision-policies/{policy_id}/activate")
async def activate_policy_route(
    policy_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    policy = _get_owned_policy(db, policy_id, current_user)
    try:
        policy = policy_service.activate_policy(db, policy, actor_role=getattr(current_user, "role", "viewer"))
    except policy_service.PolicyGovernanceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _policy_dict(policy)


@router.post("/decision-policies/{policy_id}/archive")
async def archive_policy_route(
    policy_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    policy = _get_owned_policy(db, policy_id, current_user)
    policy = policy_service.archive_policy(db, policy, actor_role=getattr(current_user, "role", "viewer"))
    return _policy_dict(policy)


@router.post("/decision-policies/{policy_id}/reject")
async def reject_policy_route(
    policy_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    policy = _get_owned_policy(db, policy_id, current_user)
    try:
        policy = policy_service.reject_policy(db, policy, actor_role=getattr(current_user, "role", "viewer"))
    except policy_service.PolicyGovernanceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _policy_dict(policy)


# ── Policy Simulation (Section 9) ───────────────────────────────────────────

class SimulationRequest(BaseModel):
    pass_threshold: float = 0.90
    technician_review_threshold: float = 0.70
    instrument_family: str = ""
    anatomy_zone: str = ""
    facility: str = ""


@router.post("/decision-policies/simulate")
async def simulate_policy_route(
    body: SimulationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant_of(current_user)
    return policy_simulation_service.simulate_policy(
        db, tenant_id=tenant_id, candidate=body.model_dump(),
        instrument_family=body.instrument_family, anatomy_zone=body.anatomy_zone, facility=body.facility,
    )


# ── Unknown-Finding Learning Loop (Section 13) ──────────────────────────────

@router.get("/unknown-findings")
async def list_unknown_findings(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant_of(current_user)
    reviews = unknown_finding_service.list_reviews(db, tenant_id=tenant_id, status=status)
    return [_unknown_finding_dict(r) for r in reviews]


def _unknown_finding_dict(review: UnknownFindingReview) -> dict:
    return {
        "id": review.id,
        "inspection_id": review.inspection_id,
        "instrument_family": review.instrument_family,
        "anatomy_zone": review.anatomy_zone,
        "model_confidence": review.model_confidence,
        "baseline_similarity": review.baseline_similarity,
        "status": review.status,
        "supervisor_classification": review.supervisor_classification,
        "adjudicated_label": review.adjudicated_label,
        "dataset_eligible": review.dataset_eligible,
    }


class UnknownFindingClassification(BaseModel):
    classification: str
    comments: str = ""


@router.post("/unknown-findings/{review_id}/classify")
async def classify_unknown_finding(
    review_id: int, body: UnknownFindingClassification,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant_of(current_user)
    review = db.query(UnknownFindingReview).filter(UnknownFindingReview.id == review_id).first()
    if not review or review.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Unknown-finding review not found")
    try:
        review = unknown_finding_service.classify_finding(
            db, review, actor=_actor_of(current_user), actor_role=getattr(current_user, "role", "viewer"),
            classification=body.classification, comments=body.comments,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return _unknown_finding_dict(review)


class UnknownFindingSecondReview(BaseModel):
    adjudicated_label: str
    dataset_eligible: bool = False
    usage_rights: str = ""


@router.post("/unknown-findings/{review_id}/second-review")
async def second_review_unknown_finding(
    review_id: int, body: UnknownFindingSecondReview,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant_of(current_user)
    review = db.query(UnknownFindingReview).filter(UnknownFindingReview.id == review_id).first()
    if not review or review.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Unknown-finding review not found")
    try:
        review = unknown_finding_service.record_second_review(
            db, review, adjudicated_label=body.adjudicated_label,
            dataset_eligible=body.dataset_eligible, usage_rights=body.usage_rights,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _unknown_finding_dict(review)
