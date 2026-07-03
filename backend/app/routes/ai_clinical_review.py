"""Supervisor AI-review capture + model-performance summary.

- POST /api/inspections/{id}/supervisor-review — admin/spd_manager record whether
  they agree with the AI, with a required comment for partial/disagree/override.
- GET  /api/model-performance/ai-summary — aggregate agreement/override metrics
  from real supervisor reviews (no fabricated production numbers).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.cios.decision_ledger import record_decision
from app.enterprise_auth import get_request_tenant_id
from app.models.supervisor_review import SupervisorReview
from app.services.pilot_validation_service import build_case_from_supervisor_review

router = APIRouter(tags=["ai-clinical-review"])

_AGREEMENT_VALUES = {"agree", "partially_agree", "disagree"}
# Comment is mandatory for anything other than a clean agreement.
_COMMENT_REQUIRED = {"partially_agree", "disagree"}


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


class SupervisorReviewIn(BaseModel):
    agreement: str = Field(..., description="agree | partially_agree | disagree")
    rationale: str = Field("", max_length=2000)
    override_action: str = Field("", max_length=50)
    # Zone-aware feedback → labeled training data.
    finding_correct: bool | None = None
    zone_correct: bool | None = None
    # Anatomy-family feedback → labeled training data for instrument classification.
    instrument_family_correct: bool | None = None
    corrected_instrument_family: str = Field("", max_length=60)
    corrected_zone: str = Field("", max_length=60)
    # v1.1 — image-view and missing-zone feedback (Inspection Coverage Engine).
    image_view_correct: bool | None = None
    corrected_image_view: str = Field("", max_length=60)
    missing_zone_correct: bool | None = None
    corrected_missing_zone: str = Field("", max_length=60)
    corrected_severity: str = Field("", max_length=30)
    corrected_recommendation: str = Field("", max_length=50)
    final_disposition: str = Field("", max_length=50)


@router.post("/inspections/{inspection_id}/supervisor-review", status_code=201)
def submit_supervisor_review(
    inspection_id: int,
    body: SupervisorReviewIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Record a supervisor's agreement with the AI clinical review.

    Role-gated to admin/spd_manager (viewers/operators cannot submit). A comment
    is required for partial agreement, disagreement, or any override.
    """
    agreement = body.agreement.strip().lower()
    if agreement not in _AGREEMENT_VALUES:
        raise HTTPException(
            status_code=422,
            detail=f"agreement must be one of {sorted(_AGREEMENT_VALUES)}",
        )
    needs_comment = agreement in _COMMENT_REQUIRED or bool(body.override_action.strip())
    if needs_comment and not body.rationale.strip():
        raise HTTPException(
            status_code=422,
            detail="A rationale comment is required for partial agreement, disagreement, or override.",
        )

    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    review = SupervisorReview(
        inspection_id=inspection_id,
        tenant_id=tenant_id,
        reviewer_name=_actor(current_user),
        reviewer_role=getattr(current_user, "role", "spd_manager"),
        agreement=agreement,
        rationale=body.rationale.strip(),
        override_action=body.override_action.strip(),
        ai_recommendation=inspection.recommended_action or "",
        ai_score=(100 - inspection.risk_score) if inspection.score_status == "scored" else None,
        finding_correct=body.finding_correct,
        zone_correct=body.zone_correct,
        instrument_family_correct=body.instrument_family_correct,
        corrected_instrument_family=body.corrected_instrument_family.strip(),
        corrected_zone=body.corrected_zone.strip(),
        image_view_correct=body.image_view_correct,
        corrected_image_view=body.corrected_image_view.strip(),
        missing_zone_correct=body.missing_zone_correct,
        corrected_missing_zone=body.corrected_missing_zone.strip(),
        corrected_severity=body.corrected_severity.strip(),
        corrected_recommendation=body.corrected_recommendation.strip(),
        final_disposition=body.final_disposition.strip(),
    )
    db.add(review)
    db.flush()  # populate review.id so the linked pilot validation case can reference it

    # Every supervisor review is also a pilot validation ground-truth case —
    # one form, one submission, no duplicate data entry for the reviewer.
    case = build_case_from_supervisor_review(inspection, review)
    db.add(case)

    # Reflect the override on the inspection when the supervisor applies one.
    if body.override_action.strip():
        inspection.override_reason = body.rationale.strip()
        inspection.override_by = _actor(current_user)
        inspection.override_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    db.refresh(case)

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id,
        actor_email=_actor(current_user), actor_role=getattr(current_user, "role", "spd_manager"),
        action_type="supervisor_ai_review", resource_type="inspection",
        resource_id=str(inspection_id),
    )
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id,
        actor_email=_actor(current_user), actor_role=getattr(current_user, "role", "spd_manager"),
        action_type="pilot_validation_case_reviewed", resource_type="pilot_validation_case",
        resource_id=str(case.id),
        details={"ground_truth_label": case.ground_truth_label, "is_critical_finding": case.is_critical_finding},
        compliance_flag=True,
    )

    # Phase 23 §5 — every supervisor decision is also recorded in the
    # permanent Clinical Decision Ledger, alongside the AI's own recorded
    # recommendation (see app/cios/orchestrator.py).
    record_decision(
        db, tenant_id, inspection_id,
        decision_type="supervisor_override" if review.override_action else "supervisor_approval",
        made_by=review.reviewer_name,
        rationale=review.rationale,
        evidence={"agreement": agreement, "corrected_zone": review.corrected_zone, "final_disposition": review.final_disposition},
    )

    return {
        "id": review.id,
        "inspection_id": inspection_id,
        "agreement": agreement,
        "override_action": review.override_action,
        "reviewer": review.reviewer_name,
        "pilot_validation_case_id": case.id,
        "ground_truth_label": case.ground_truth_label,
    }


@router.get("/inspections/{inspection_id}/supervisor-reviews")
def list_supervisor_reviews(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    rows = (
        db.query(SupervisorReview)
        .filter(SupervisorReview.inspection_id == inspection_id)
        .order_by(SupervisorReview.id.desc())
        .all()
    )
    return {
        "inspection_id": inspection_id,
        "count": len(rows),
        "reviews": [
            {
                "id": r.id, "agreement": r.agreement, "rationale": r.rationale,
                "override_action": r.override_action, "reviewer": r.reviewer_name,
                "reviewer_role": r.reviewer_role,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/model-performance/ai-summary")
def ai_performance_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Aggregate real supervisor-agreement metrics.

    Computed only from actual reviews/inspections — no fabricated production
    numbers. Fields are zero/None until real reviews exist.
    """
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)

    inspections = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id)
    total_predictions = inspections.filter(models.Inspection.has_image.is_(True)).count()
    cases_requiring_review = inspections.filter(
        models.Inspection.supervisor_review_required.is_(True)
    ).count()
    scored = inspections.filter(models.Inspection.score_status == "scored").all()
    avg_conf = round(sum((r.confidence or 0) for r in scored) / len(scored), 2) if scored else None

    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    n = len(reviews)
    agree = sum(1 for r in reviews if r.agreement == "agree")
    overrides = sum(1 for r in reviews if r.override_action)
    disagree = sum(1 for r in reviews if r.agreement == "disagree")

    return {
        "model_version": "baseline-comparison-pilot-1",
        "dataset_version": "v0-pilot",
        "total_ai_predictions": total_predictions,
        "supervisor_reviews": n,
        "supervisor_agreement_rate": round(agree / n, 4) if n else None,
        "override_rate": round(overrides / n, 4) if n else None,
        # False +/- require adjudicated ground truth; surfaced but not fabricated.
        "false_positive_count": None,
        "false_negative_count": None,
        "disagreement_count": disagree,
        "average_confidence": avg_conf,
        "cases_requiring_review": cases_requiring_review,
        "note": (
            "Agreement/override rates are computed from real supervisor reviews. "
            "False positive/negative counts require adjudicated ground truth and "
            "are not fabricated."
        ),
    }
