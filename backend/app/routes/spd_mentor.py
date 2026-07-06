"""v1.4 — SPD Mentor Engine API surface.

- GET  /api/mentor/education                      — Educational Knowledge Library (all articles)
- GET  /api/mentor/education/{finding_type}        — single article
- POST /api/mentor/education/{finding_type}/complete — mark an article completed (competency tracking)
- GET  /api/mentor/competency/{technician}         — technician competency summary
- GET  /api/inspections/{inspection_id}/mentor     — re-derive the SPD Mentor payload for a past inspection
- GET  /api/mentor/coaching-queue                  — Supervisor Coaching Dashboard: inspections awaiting review
- POST /api/inspections/{inspection_id}/coaching-review — approve/edit/comment on the AI's coaching
- GET  /api/mentor/coaching-effectiveness          — aggregate coaching-review stats
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.mentor_coaching_review import MentorCoachingReview
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.competency_service import competency_summary, record_education_completed
from app.services.education_library import get_article, list_articles

router = APIRouter(tags=["spd-mentor"])


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


# ── Educational Knowledge Library ────────────────────────────────────────────
@router.get("/mentor/education")
def get_education_library(
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    return {"articles": list_articles()}


@router.get("/mentor/education/{finding_type}")
def get_education_article(
    finding_type: str,
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    article = get_article(finding_type)
    if article is None:
        raise HTTPException(status_code=404, detail=f"No education article for '{finding_type}'.")
    return article


@router.post("/mentor/education/{finding_type}/complete", status_code=201)
def complete_education_article(
    finding_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator")),
):
    article = get_article(finding_type)
    if article is None:
        raise HTTPException(status_code=404, detail=f"No education article for '{finding_type}'.")

    technician = _actor(current_user)
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    record_education_completed(db, tenant_id=tenant_id, technician=technician, finding_type=finding_type)
    db.commit()
    return competency_summary(db, technician)


# ── Competency Support ────────────────────────────────────────────────────────
@router.get("/mentor/competency/{technician}")
def get_competency_summary(
    technician: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator")),
):
    role = getattr(current_user, "role", "viewer")
    if role not in ("admin", "spd_manager") and _actor(current_user) != technician:
        raise HTTPException(status_code=403, detail="You may only view your own competency summary.")
    return competency_summary(db, technician)


# ── Per-inspection mentor re-derivation (Training Mode viewer) ───────────────
@router.get("/inspections/{inspection_id}/mentor")
def get_inspection_mentor(
    inspection_id: int,
    request: Request,
    training_mode: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Re-derive the SPD Mentor payload for a previously-submitted inspection.

    Mirrors the clinical-report.pdf endpoint's pattern: analysis is
    deterministic from the stored inspection's identity, so re-running it
    reproduces the same findings — this lets a technician revisit an
    inspection with Training Mode on without re-uploading images.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    query = db.query(models.Inspection).filter(models.Inspection.id == inspection_id)
    if tenant_id and getattr(current_user, "role", "") != "admin":
        query = query.filter(models.Inspection.tenant_id == tenant_id)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Not Found")

    analysis = analyze_inspection(
        db,
        instrument_type=row.instrument_type,
        tenant_id=row.tenant_id,
        has_image=bool(row.has_image),
        image_sha256=row.image_sha256,
        instrument_barcode=row.instrument_barcode,
        instrument_udi=row.instrument_udi,
        training_mode=training_mode,
    )
    return analysis["clinical_decision"]["spd_mentor"]


# ── Supervisor Coaching Dashboard ─────────────────────────────────────────────
class CoachingReviewIn(BaseModel):
    approved: bool = Field(True)
    edited_recommendation: str = Field("", max_length=1000)
    educational_comment: str = Field("", max_length=2000)


@router.get("/mentor/coaching-queue")
def get_coaching_queue(
    request: Request,
    limit: int = 25,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Recent inspections whose AI coaching has not yet been reviewed by a
    supervisor, most recent first."""
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    query = db.query(models.Inspection).filter(models.Inspection.has_image.is_(True))
    if tenant_id and getattr(current_user, "role", "") != "admin":
        query = query.filter(models.Inspection.tenant_id == tenant_id)
    rows = query.order_by(models.Inspection.id.desc()).limit(max(1, min(limit, 100))).all()

    reviewed_ids = {
        r.inspection_id
        for r in db.query(MentorCoachingReview.inspection_id)
        .filter(MentorCoachingReview.inspection_id.in_([row.id for row in rows]))
        .all()
    } if rows else set()

    return {
        "queue": [
            {
                "inspection_id": row.id,
                "instrument_type": row.instrument_type,
                "technician": row.technician,
                "risk_level": row.risk_level,
                "recommended_action": row.recommended_action,
                "coaching_reviewed": row.id in reviewed_ids,
            }
            for row in rows
        ],
    }


@router.post("/inspections/{inspection_id}/coaching-review", status_code=201)
def submit_coaching_review(
    inspection_id: int,
    body: CoachingReviewIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    inspection = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    review = MentorCoachingReview(
        inspection_id=inspection_id,
        tenant_id=tenant_id,
        reviewer_name=_actor(current_user),
        reviewer_role=getattr(current_user, "role", "spd_manager"),
        approved=body.approved,
        edited_recommendation=body.edited_recommendation.strip(),
        educational_comment=body.educational_comment.strip(),
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id,
        actor_email=_actor(current_user), actor_role=getattr(current_user, "role", "spd_manager"),
        action_type="mentor_coaching_review", resource_type="inspection",
        resource_id=str(inspection_id),
    )
    return {
        "id": review.id,
        "inspection_id": inspection_id,
        "approved": review.approved,
        "edited_recommendation": review.edited_recommendation,
        "educational_comment": review.educational_comment,
    }


@router.get("/mentor/coaching-effectiveness")
def get_coaching_effectiveness(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Aggregate stats on how often supervisors approve the AI's coaching
    unchanged vs. edit or add educational comments — derived only from
    recorded reviews, empty when there are none yet."""
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    query = db.query(MentorCoachingReview)
    if tenant_id and getattr(current_user, "role", "") != "admin":
        query = query.filter(MentorCoachingReview.tenant_id == tenant_id)
    reviews = query.all()

    total = len(reviews)
    approved_unchanged = sum(1 for r in reviews if r.approved and not r.edited_recommendation)
    edited = sum(1 for r in reviews if r.edited_recommendation)
    with_comment = sum(1 for r in reviews if r.educational_comment)

    return {
        "total_reviews": total,
        "approved_unchanged": approved_unchanged,
        "edited": edited,
        "with_educational_comment": with_comment,
        "approved_unchanged_pct": round(100 * approved_unchanged / total) if total else None,
    }
