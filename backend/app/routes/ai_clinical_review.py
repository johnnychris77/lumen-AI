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
from app.enterprise_auth import get_request_tenant_id
from app.models.supervisor_review import SupervisorReview

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
    )
    db.add(review)

    # Reflect the override on the inspection when the supervisor applies one.
    if body.override_action.strip():
        inspection.override_reason = body.rationale.strip()
        inspection.override_by = _actor(current_user)
        inspection.override_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id,
        actor_email=_actor(current_user), actor_role=getattr(current_user, "role", "spd_manager"),
        action_type="supervisor_ai_review", resource_type="inspection",
        resource_id=str(inspection_id),
    )
    return {
        "id": review.id,
        "inspection_id": inspection_id,
        "agreement": agreement,
        "override_action": review.override_action,
        "reviewer": review.reviewer_name,
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
