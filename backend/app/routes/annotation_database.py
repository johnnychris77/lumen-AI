"""Annotation Database & Storage System — REST surface.

RBAC (Section 14) — `role` columns are free-form strings; the two new role
values used here (`clinical_reviewer`, `ai_researcher`) require no change
to core auth infrastructure, only that a tenant admin assigns them via the
existing role-assignment path:

| Spec role | Enforced role string |
|---|---|
| Administrator | `admin` |
| Clinical Reviewer | `clinical_reviewer` |
| Reviewer | `spd_manager` |
| Annotator | `operator` |
| AI Researcher | `ai_researcher` |
| Viewer | `viewer` |

Only `admin`/`clinical_reviewer` may finalize Ground Truth or adjudicate.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.annotation_database import (
    ROLES_MAY_ANNOTATE,
    ROLES_MAY_EXPORT,
    ROLES_MAY_FINALIZE_GROUND_TRUTH,
    ROLES_MAY_REVIEW,
    ROLES_MAY_VIEW,
    Annotation,
    AnnotationReview,
)
from app.services import annotation_analytics_service, annotation_export_service, annotation_ground_truth_service
from app.services import annotation_review_service, annotation_service

router = APIRouter(tags=["annotation-database"])

_ADMIN = "admin"


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _actor_role(user) -> str:
    return getattr(user, "role", "viewer")


class AnnotationCreateIn(BaseModel):
    retained_image_id: int
    inspection_id: Optional[int] = None
    instrument_family: str = Field("", max_length=100)
    instrument_model: str = Field("", max_length=100)
    manufacturer: str = Field("", max_length=100)
    instrument_barcode: str = Field("", max_length=255)
    instrument_udi: str = Field("", max_length=255)
    dataset_version_id: Optional[int] = None
    model_version: str = Field("", max_length=50)
    primary_observation: str = Field("", max_length=80)
    secondary_observation: str = Field("", max_length=80)
    appearance_attributes: list[str] = Field(default_factory=list)
    severity: str = Field("", max_length=20)
    location: str = Field("", max_length=100)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reviewer_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    comments: str = Field("", max_length=2000)
    recommendation: str = Field("", max_length=60)
    supervisor_required: bool = False
    unknown_flag: bool = False
    image_quality: str = Field("", max_length=20)
    region_type: str = Field("whole_image_classification", max_length=30)
    region_coordinates: list = Field(default_factory=list)
    baseline_type: str = Field("", max_length=30)
    baseline_version: str = Field("", max_length=50)
    baseline_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    baseline_deviation: Optional[float] = Field(None, ge=0.0, le=1.0)


def _annotation_view(a: Annotation) -> dict:
    import json

    return {
        "id": a.id, "ann_id": a.ann_id, "retained_image_id": a.retained_image_id,
        "inspection_id": a.inspection_id, "instrument_family": a.instrument_family,
        "instrument_model": a.instrument_model, "manufacturer": a.manufacturer,
        "digital_twin_id": a.digital_twin_id, "baseline_id": a.baseline_id,
        "reviewer": a.reviewer, "dataset_version_id": a.dataset_version_id,
        "ground_truth_version": a.ground_truth_version, "model_version": a.model_version,
        "primary_observation": a.primary_observation, "secondary_observation": a.secondary_observation,
        "appearance_attributes": json.loads(a.appearance_attributes_json or "[]"),
        "severity": a.severity, "location": a.location, "confidence": a.confidence,
        "reviewer_confidence": a.reviewer_confidence, "comments": a.comments,
        "recommendation": a.recommendation, "supervisor_required": a.supervisor_required,
        "unknown_flag": a.unknown_flag, "image_quality": a.image_quality,
        "region_type": a.region_type, "region_coordinates": json.loads(a.region_coordinates_json or "[]"),
        "review_status": a.review_status, "ground_truth_status": a.ground_truth_status,
        "current_version": a.current_version, "baseline_type": a.baseline_type,
        "baseline_version": a.baseline_version, "baseline_similarity": a.baseline_similarity,
        "baseline_deviation": a.baseline_deviation,
        "supervisor_classification": a.supervisor_classification,
        "clinical_review_status": a.clinical_review_status, "candidate_label": a.candidate_label,
        "promotion_status": a.promotion_status,
    }


@router.post("/annotations", status_code=201)
def create_annotation(
    body: AnnotationCreateIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_ANNOTATE)),
):
    tenant_id = _tenant(current_user, request)
    try:
        annotation = annotation_service.create_annotation(
            db, tenant_id=tenant_id, actor=_actor(current_user), actor_role=_actor_role(current_user),
            **body.model_dump(),
        )
    except annotation_service.InvalidRegionTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _annotation_view(annotation)


@router.get("/annotations")
def list_annotations(
    request: Request, retained_image_id: Optional[int] = None, ground_truth_status: Optional[str] = None,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*ROLES_MAY_VIEW)),
):
    tenant_id = _tenant(current_user, request)
    rows = annotation_service.list_annotations(
        db, tenant_id=tenant_id, retained_image_id=retained_image_id, ground_truth_status=ground_truth_status,
    )
    return {"count": len(rows), "annotations": [_annotation_view(r) for r in rows]}


def _get_owned_annotation(db: Session, annotation_id: int, tenant_id: str) -> Annotation:
    annotation = annotation_service.get_annotation(db, tenant_id=tenant_id, annotation_id=annotation_id)
    if annotation is None:
        raise HTTPException(status_code=404, detail="Annotation not found")
    return annotation


@router.get("/annotations/{annotation_id}")
def get_annotation(
    annotation_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_VIEW)),
):
    tenant_id = _tenant(current_user, request)
    return _annotation_view(_get_owned_annotation(db, annotation_id, tenant_id))


@router.get("/annotations/{annotation_id}/versions")
def get_annotation_versions(
    annotation_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_VIEW)),
):
    tenant_id = _tenant(current_user, request)
    _get_owned_annotation(db, annotation_id, tenant_id)
    versions = annotation_service.version_history(db, annotation_id=annotation_id)
    return {
        "count": len(versions),
        "versions": [
            {
                "version_number": v.version_number, "editor": v.editor, "reason": v.reason,
                "timestamp": v.created_at, "previous_version_id": v.previous_version_id,
            }
            for v in versions
        ],
    }


class AnnotationUpdateIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)
    primary_observation: Optional[str] = None
    secondary_observation: Optional[str] = None
    severity: Optional[str] = None
    location: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    comments: Optional[str] = None
    recommendation: Optional[str] = None
    supervisor_required: Optional[bool] = None


@router.patch("/annotations/{annotation_id}")
def update_annotation(
    annotation_id: int, body: AnnotationUpdateIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_ANNOTATE)),
):
    tenant_id = _tenant(current_user, request)
    annotation = _get_owned_annotation(db, annotation_id, tenant_id)
    changes = {k: v for k, v in body.model_dump(exclude={"reason"}).items() if v is not None}
    annotation = annotation_service.update_annotation(
        db, annotation, editor=_actor(current_user), actor_role=_actor_role(current_user),
        reason=body.reason, **changes,
    )
    return _annotation_view(annotation)


# ── Multi-reviewer workflow (Section 5) ─────────────────────────────────────

class ReviewSubmitIn(BaseModel):
    label: str = Field(..., max_length=80)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    comments: str = Field("", max_length=2000)


@router.post("/annotations/{annotation_id}/review/primary", status_code=201)
def submit_primary_review(
    annotation_id: int, body: ReviewSubmitIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_REVIEW)),
):
    tenant_id = _tenant(current_user, request)
    _get_owned_annotation(db, annotation_id, tenant_id)
    review = annotation_review_service.start_review(db, tenant_id=tenant_id, annotation_id=annotation_id)
    try:
        review = annotation_review_service.submit_primary(
            db, review, reviewer=_actor(current_user), actor_role=_actor_role(current_user),
            label=body.label, confidence=body.confidence, comments=body.comments,
        )
    except annotation_review_service.ReviewAlreadySubmittedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _review_view(review)


@router.post("/annotations/{annotation_id}/review/secondary", status_code=201)
def submit_secondary_review(
    annotation_id: int, body: ReviewSubmitIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_REVIEW)),
):
    tenant_id = _tenant(current_user, request)
    _get_owned_annotation(db, annotation_id, tenant_id)
    review = annotation_review_service.start_review(db, tenant_id=tenant_id, annotation_id=annotation_id)
    try:
        review = annotation_review_service.submit_secondary(
            db, review, reviewer=_actor(current_user), actor_role=_actor_role(current_user),
            label=body.label, confidence=body.confidence, comments=body.comments,
        )
    except (
        annotation_review_service.ReviewAlreadySubmittedError,
        annotation_review_service.ReviewerCannotSelfSecondaryError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _review_view(review)


def _review_view(review: AnnotationReview) -> dict:
    return {
        "id": review.id, "annotation_id": review.annotation_id,
        "primary_reviewer": review.primary_reviewer, "primary_label": review.primary_label,
        "secondary_reviewer": review.secondary_reviewer, "secondary_label": review.secondary_label,
        "agreement": review.agreement, "disagreement_reason": review.disagreement_reason,
        "adjudicator": review.adjudicator, "resolution": review.resolution,
        "resolved_at": review.resolved_at,
    }


class AdjudicateIn(BaseModel):
    resolution: str = Field(..., max_length=80)
    reason: str = Field(..., min_length=1, max_length=2000)


@router.post("/annotations/{annotation_id}/review/adjudicate")
def adjudicate_review(
    annotation_id: int, body: AdjudicateIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_FINALIZE_GROUND_TRUTH)),
):
    tenant_id = _tenant(current_user, request)
    _get_owned_annotation(db, annotation_id, tenant_id)
    review = annotation_review_service.get_review(db, tenant_id=tenant_id, annotation_id=annotation_id)
    if review is None:
        raise HTTPException(status_code=404, detail="No review record exists for this annotation")
    try:
        review = annotation_review_service.adjudicate(
            db, review, adjudicator=_actor(current_user), actor_role=_actor_role(current_user),
            resolution=body.resolution, reason=body.reason,
        )
    except (
        annotation_review_service.PermissionDeniedError,
    ) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (
        annotation_review_service.AdjudicationNotRequiredError,
        annotation_review_service.AdjudicationReasonRequiredError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _review_view(review)


@router.get("/annotations/{annotation_id}/review")
def get_annotation_review(
    annotation_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_FINALIZE_GROUND_TRUTH)),
):
    """Project Canvas Sections 11-13 — non-blind review detail for
    disagreement comparison, adjudication, and Ground Truth eligibility
    display. Restricted to the adjudicator/Ground-Truth-finalizer roles
    (never `ROLES_MAY_REVIEW`'s plain Reviewer role), so a reviewer who
    hasn't yet submitted their own independent review can never use this
    endpoint to see the other side early — Section 10's blindness guarantee
    is enforced by role, not by trusting the frontend to hide a link."""
    tenant_id = _tenant(current_user, request)
    _get_owned_annotation(db, annotation_id, tenant_id)
    review = annotation_review_service.get_review(db, tenant_id=tenant_id, annotation_id=annotation_id)
    if review is None:
        raise HTTPException(status_code=404, detail="No review record exists for this annotation.")
    return _review_view(review)


# ── Ground Truth (Section 6) ─────────────────────────────────────────────────

@router.post("/annotations/{annotation_id}/promote-ground-truth")
def promote_ground_truth(
    annotation_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_FINALIZE_GROUND_TRUTH)),
):
    tenant_id = _tenant(current_user, request)
    annotation = _get_owned_annotation(db, annotation_id, tenant_id)
    review = annotation_review_service.get_review(db, tenant_id=tenant_id, annotation_id=annotation_id)
    try:
        annotation = annotation_ground_truth_service.promote_to_ground_truth(
            db, annotation, review, actor=_actor(current_user), actor_role=_actor_role(current_user),
        )
    except annotation_ground_truth_service.PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except annotation_ground_truth_service.GroundTruthNotEligibleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _annotation_view(annotation)


# ── Analytics (Section 11) ───────────────────────────────────────────────────

@router.get("/annotations/analytics/summary")
def analytics_summary(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*ROLES_MAY_VIEW)),
):
    tenant_id = _tenant(current_user, request)
    return {
        "reviewer_agreement": annotation_analytics_service.reviewer_agreement(db, tenant_id=tenant_id),
        "reviewer_accuracy": annotation_analytics_service.reviewer_accuracy(db, tenant_id=tenant_id),
        "common_findings": annotation_analytics_service.common_findings(db, tenant_id=tenant_id),
        "finding_distribution": annotation_analytics_service.finding_distribution(db, tenant_id=tenant_id),
        "unknown_frequency": annotation_analytics_service.unknown_frequency(db, tenant_id=tenant_id),
        "class_balance": annotation_analytics_service.class_balance(db, tenant_id=tenant_id),
        "dataset_growth": annotation_analytics_service.dataset_growth(db, tenant_id=tenant_id),
        "annotation_velocity": annotation_analytics_service.annotation_velocity(db, tenant_id=tenant_id),
    }


# ── Export (Section 12) ──────────────────────────────────────────────────────

class ExportIn(BaseModel):
    export_format: str = Field(..., description=f"One of {annotation_export_service.EXPORT_FORMATS}")
    ground_truth_only: bool = True


@router.post("/annotations/export")
def export_annotations(
    body: ExportIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*ROLES_MAY_EXPORT)),
):
    tenant_id = _tenant(current_user, request)
    try:
        manifest = annotation_export_service.export_annotations(
            db, tenant_id=tenant_id, export_format=body.export_format, ground_truth_only=body.ground_truth_only,
        )
    except annotation_export_service.UnsupportedExportFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return manifest
