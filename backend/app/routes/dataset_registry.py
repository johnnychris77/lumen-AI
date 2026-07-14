"""Dataset Registry & AI Model Development Foundation — REST surface.

Dataset versioning, per-image registration, the 7-state annotation
lifecycle, double-blind review, real image-quality assessment, and the
training-dataset builder. Complements the pre-existing ``/model-pipeline/*``
and ``/images/*`` (``app.routes.ml_images``) surfaces rather than
duplicating them.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.dataset_governance import (
    ANNOTATION_STATES,
    DatasetRegistryEntry,
    DatasetVersion,
    DoubleBlindReview,
    ImageQualityAssessment,
)
from app.models.retained_image import RetainedImage
from app.services.ml import annotation_workflow, dataset_builder, dataset_registry, double_blind_review, image_quality
from app.services.ml.candidate_training import DatasetInvalidError, run_full_candidate_pipeline
from app.services.ml.training_config import TrainingConfig

router = APIRouter(tags=["dataset-registry"])

_WRITE_ROLES = ("admin", "spd_manager")
_READ_ROLES = ("admin", "spd_manager", "operator", "viewer")


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


# ── Dataset versions (Section 2) ────────────────────────────────────────────

class CreateVersionIn(BaseModel):
    version_label: str = Field(..., min_length=1, max_length=40)
    description: str = Field("", max_length=2000)
    supersedes_id: int | None = None


@router.post("/dataset-registry/versions", status_code=201)
def create_version(
    body: CreateVersionIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = dataset_registry.create_dataset_version(
        db, tenant_id=tenant_id, version_label=body.version_label,
        description=body.description, supersedes_id=body.supersedes_id,
    )
    return _version_view(row)


@router.get("/dataset-registry/versions")
def list_versions(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_READ_ROLES))):
    tenant_id = _tenant(current_user, request)
    rows = (
        db.query(DatasetVersion).filter(DatasetVersion.tenant_id == tenant_id)
        .order_by(DatasetVersion.id.desc()).all()
    )
    return {"count": len(rows), "versions": [_version_view(r) for r in rows]}


@router.post("/dataset-registry/versions/{version_id}/freeze")
def freeze_version(
    version_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        row = dataset_registry.freeze_dataset_version(
            db, tenant_id=tenant_id, dataset_version_id=version_id, frozen_by=_actor(current_user),
        )
    except dataset_registry.DatasetVersionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="dataset_version_frozen",
        resource_type="dataset_version", resource_id=str(version_id),
    )
    return _version_view(row)


def _version_view(row: DatasetVersion) -> dict:
    return {
        "id": row.id, "version_label": row.version_label, "description": row.description,
        "supersedes_id": row.supersedes_id, "frozen": row.frozen,
        "frozen_at": row.frozen_at.isoformat() if row.frozen_at else None,
        "frozen_by": row.frozen_by, "image_count_at_freeze": row.image_count_at_freeze,
    }


# ── Image registration (Section 1) ──────────────────────────────────────────

class RegisterImageIn(BaseModel):
    dataset_version_id: int
    retained_image_id: int
    image_sha256: str = Field(..., min_length=8, max_length=64)
    inspection_id: int | None = None
    instrument_family: str = Field("", max_length=100)
    instrument_model: str = Field("", max_length=100)
    manufacturer: str = Field("", max_length=100)
    anatomy_zone: str = Field("", max_length=60)
    capture_device: str = Field("", max_length=100)
    image_resolution: str = Field("", max_length=20)
    lighting_condition: str = Field("unknown", max_length=40)
    facility: str = Field("", max_length=255)
    operator: str = Field("", max_length=255)
    usage_rights: str = Field("", max_length=100)
    phi_verification: str = Field("pending", max_length=20)


@router.post("/dataset-registry/images", status_code=201)
def register_image(
    body: RegisterImageIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        row = dataset_registry.register_image(
            db, tenant_id=tenant_id, dataset_version_id=body.dataset_version_id,
            retained_image_id=body.retained_image_id, image_sha256=body.image_sha256,
            inspection_id=body.inspection_id, instrument_family=body.instrument_family,
            instrument_model=body.instrument_model, manufacturer=body.manufacturer,
            anatomy_zone=body.anatomy_zone, capture_device=body.capture_device,
            image_resolution=body.image_resolution, lighting_condition=body.lighting_condition,
            facility=body.facility, operator=body.operator, usage_rights=body.usage_rights,
            phi_verification=body.phi_verification,
        )
    except dataset_registry.DatasetVersionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except dataset_registry.DatasetVersionFrozenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except dataset_registry.MetadataValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "missing_fields": exc.missing_fields}) from exc
    except dataset_registry.DuplicateImageError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="dataset_image_registered",
        resource_type="dataset_entry", resource_id=str(row.id),
    )
    return _entry_view(row)


@router.get("/dataset-registry/images")
def list_images(
    request: Request, dataset_version_id: int | None = None, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    rows = dataset_registry.list_entries(db, tenant_id=tenant_id, dataset_version_id=dataset_version_id)
    return {"count": len(rows), "images": [_entry_view(r) for r in rows]}


def _entry_view(row: DatasetRegistryEntry) -> dict:
    return {
        "id": row.id, "dataset_version_id": row.dataset_version_id,
        "dataset_version_label": row.dataset_version_label,
        "retained_image_id": row.retained_image_id, "inspection_id": row.inspection_id,
        "instrument_family": row.instrument_family, "instrument_model": row.instrument_model,
        "manufacturer": row.manufacturer, "anatomy_zone": row.anatomy_zone,
        "capture_device": row.capture_device, "image_resolution": row.image_resolution,
        "lighting_condition": row.lighting_condition, "image_quality": row.image_quality,
        "facility": row.facility, "operator": row.operator,
        "current_label": row.current_label, "reviewer": row.reviewer,
        "review_status": row.review_status, "annotation_version": row.annotation_version,
        "split_assignment": row.split_assignment, "usage_rights": row.usage_rights,
        "phi_verification": row.phi_verification, "training_eligibility": row.training_eligibility,
        "retention_status": row.retention_status,
    }


# ── Annotation lifecycle (Section 3) ────────────────────────────────────────

class TransitionIn(BaseModel):
    to_state: str = Field(..., description=f"One of {ANNOTATION_STATES}")
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    comments: str = Field("", max_length=2000)


@router.post("/dataset-registry/images/{entry_id}/annotation-transition", status_code=201)
def annotation_transition(
    entry_id: int, body: TransitionIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        event = annotation_workflow.transition(
            db, tenant_id=tenant_id, dataset_entry_id=entry_id, to_state=body.to_state,
            reviewer=_actor(current_user), confidence=body.confidence, comments=body.comments,
        )
    except annotation_workflow.UnknownStateError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except annotation_workflow.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "id": event.id, "dataset_entry_id": event.dataset_entry_id,
        "from_state": event.from_state, "to_state": event.to_state,
        "reviewer": event.reviewer, "confidence": event.confidence, "comments": event.comments,
    }


@router.get("/dataset-registry/images/{entry_id}/annotation-history")
def annotation_history(
    entry_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_READ_ROLES)),
):
    events = annotation_workflow.history(db, entry_id)
    return {
        "current_state": annotation_workflow.current_state(db, entry_id),
        "events": [
            {"id": e.id, "from_state": e.from_state, "to_state": e.to_state, "reviewer": e.reviewer,
             "confidence": e.confidence, "comments": e.comments, "created_at": e.created_at.isoformat()}
            for e in events
        ],
    }


# ── Double-blind review (Section 4) ─────────────────────────────────────────

class PrimaryReviewIn(BaseModel):
    label: str = Field(..., max_length=60)
    confidence: float | None = Field(None, ge=0.0, le=1.0)


class IndependentReviewIn(BaseModel):
    label: str = Field(..., max_length=60)
    confidence: float | None = Field(None, ge=0.0, le=1.0)


class AdjudicateIn(BaseModel):
    resolution: str = Field(..., max_length=60)
    reason: str = Field(..., max_length=2000)


@router.post("/dataset-registry/images/{entry_id}/double-blind/primary", status_code=201)
def submit_primary(
    entry_id: int, body: PrimaryReviewIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    review = double_blind_review.start_review(db, tenant_id=tenant_id, dataset_entry_id=entry_id)
    try:
        review = double_blind_review.submit_primary(
            db, review=review, reviewer=_actor(current_user), label=body.label, confidence=body.confidence,
        )
    except double_blind_review.ReviewAlreadySubmittedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _review_view(review)


@router.post("/dataset-registry/images/{entry_id}/double-blind/independent", status_code=201)
def submit_independent(
    entry_id: int, body: IndependentReviewIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    review = double_blind_review.start_review(db, tenant_id=tenant_id, dataset_entry_id=entry_id)
    try:
        review = double_blind_review.submit_independent(
            db, review=review, reviewer=_actor(current_user), label=body.label, confidence=body.confidence,
        )
    except (double_blind_review.ReviewAlreadySubmittedError, double_blind_review.ReviewerCannotSelfIndependentError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _review_view(review)


@router.post("/dataset-registry/images/{entry_id}/double-blind/adjudicate")
def adjudicate_review(
    entry_id: int, body: AdjudicateIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    review = (
        db.query(DoubleBlindReview)
        .filter(DoubleBlindReview.tenant_id == tenant_id, DoubleBlindReview.dataset_entry_id == entry_id)
        .first()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="No double-blind review found for this image.")
    try:
        review = double_blind_review.adjudicate(
            db, review=review, adjudicator=_actor(current_user), resolution=body.resolution, reason=body.reason,
        )
    except double_blind_review.AdjudicationNotRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except double_blind_review.ReasonRequiredError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="double_blind_review_adjudicated",
        resource_type="dataset_entry", resource_id=str(entry_id),
    )
    return _review_view(review)


def _review_view(row: DoubleBlindReview) -> dict:
    return {
        "id": row.id, "dataset_entry_id": row.dataset_entry_id,
        "primary_reviewer": row.primary_reviewer, "primary_label": row.primary_label,
        "independent_reviewer": row.independent_reviewer, "independent_label": row.independent_label,
        "agreement": row.agreement, "adjudicator": row.adjudicator,
        "resolution": row.resolution, "reason": row.reason,
    }


# ── Image quality assessment (Section 5) ────────────────────────────────────

@router.post("/dataset-registry/images/{entry_id}/quality-assessment", status_code=201)
def assess_quality(
    entry_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    """Compute a real, pixel-based quality assessment from the entry's
    retained image bytes and persist it, updating the entry's
    ``image_quality`` field."""
    tenant_id = _tenant(current_user, request)
    entry = (
        db.query(DatasetRegistryEntry)
        .filter(DatasetRegistryEntry.id == entry_id, DatasetRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Dataset entry not found.")
    retained = (
        db.query(RetainedImage)
        .filter(RetainedImage.id == entry.retained_image_id, RetainedImage.tenant_id == tenant_id)
        .first()
    )
    if retained is None or not retained.image_bytes:
        raise HTTPException(status_code=422, detail="No retained image bytes available for this entry.")

    result = image_quality.assess_image_bytes(retained.image_bytes)
    row = ImageQualityAssessment(
        tenant_id=tenant_id, dataset_entry_id=entry_id, retained_image_id=retained.id,
        width=result["width"], height=result["height"],
        brightness_mean=result["brightness_mean"], sharpness_score=result["sharpness_score"],
        blur_flag=result["blur_flag"], lighting_flag=result["lighting_flag"],
        exposure_flag=result["exposure_flag"], focus_flag=result["focus_flag"],
        cropping_flag=result["cropping_flag"], visibility_flag=result["visibility_flag"],
        overall_quality=result["overall_quality"], notes=result["notes"],
    )
    db.add(row)
    entry.image_quality = result["overall_quality"]
    db.commit()
    db.refresh(row)
    return {
        "id": row.id, "overall_quality": row.overall_quality, "notes": row.notes,
        "width": row.width, "height": row.height,
        "brightness_mean": row.brightness_mean, "sharpness_score": row.sharpness_score,
        "flags": {
            "blur": row.blur_flag, "lighting": row.lighting_flag, "exposure": row.exposure_flag,
            "focus": row.focus_flag, "cropping": row.cropping_flag, "visibility": row.visibility_flag,
        },
    }


# ── Training dataset builder (Sections 6 & 7) ───────────────────────────────

@router.post("/dataset-registry/versions/{version_id}/build-training-dataset")
def build_training_dataset(
    version_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = dataset_builder.build_training_dataset(db, tenant_id=tenant_id, dataset_version_id=version_id)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="training_dataset_built",
        resource_type="dataset_version", resource_id=str(version_id),
    )
    return result


# ── Genesis: candidate model training (Sections 1-3) ────────────────────────

class RunCandidateTrainingIn(BaseModel):
    model_id: str = Field(..., min_length=1, max_length=100)
    model_version: str = Field(..., min_length=1, max_length=50)
    seed: int = Field(42)
    epochs: int = Field(500, ge=1, le=5000)
    learning_rate: float = Field(0.3, gt=0, le=5.0)


def _sample_from_entry(db: Session, entry: DatasetRegistryEntry, retained: RetainedImage) -> dict:
    quality = (
        db.query(ImageQualityAssessment)
        .filter(ImageQualityAssessment.dataset_entry_id == entry.id)
        .order_by(ImageQualityAssessment.id.desc())
        .first()
    )
    review = (
        db.query(DoubleBlindReview)
        .filter(DoubleBlindReview.dataset_entry_id == entry.id)
        .order_by(DoubleBlindReview.id.desc())
        .first()
    )
    return {
        "id": entry.id,
        "image_bytes": retained.image_bytes,
        "label": entry.current_label,
        "inspection_id": entry.inspection_id,
        "instrument_family": entry.instrument_family,
        "manufacturer": entry.manufacturer,
        "facility": entry.facility,
        "anatomy_zone": entry.anatomy_zone,
        "image_sha256": entry.image_sha256,
        "blur_flag": quality.blur_flag if quality else None,
        "focus_flag": quality.focus_flag if quality else None,
        "lighting_flag": quality.lighting_flag if quality else None,
        "exposure_flag": quality.exposure_flag if quality else None,
        "cropping_flag": quality.cropping_flag if quality else None,
        "annotation_disagreement": (review.agreement is False) if review else False,
    }


@router.post("/dataset-registry/versions/{version_id}/run-candidate-training", status_code=201)
def run_candidate_training_endpoint(
    version_id: int, body: RunCandidateTrainingIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_WRITE_ROLES)),
):
    """Genesis Section 3 — the full candidate training pipeline, triggered
    over the real dataset registry: eligible entries -> real retained image
    bytes -> dataset validation -> training -> evaluation -> error analysis
    -> calibration -> artifact export -> registration -> model card. One
    call; no manual intervention after it starts."""
    tenant_id = _tenant(current_user, request)
    eligible, _excluded = dataset_builder.eligible_entries(db, tenant_id=tenant_id, dataset_version_id=version_id)

    samples = []
    for entry in eligible:
        retained = db.query(RetainedImage).filter(RetainedImage.id == entry.retained_image_id).first()
        if retained is not None and retained.image_bytes:
            samples.append(_sample_from_entry(db, entry, retained))

    config = TrainingConfig(seed=body.seed, epochs=body.epochs, learning_rate=body.learning_rate)
    try:
        model = run_full_candidate_pipeline(
            db, tenant_id=tenant_id, samples=samples, config=config,
            model_id=body.model_id, model_version=body.model_version, dataset_version_id=version_id,
        )
    except DatasetInvalidError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "report": exc.report}) from exc

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="candidate_model_trained",
        resource_type="model", resource_id=f"{model.model_id}:{model.model_version}",
        details={"training_status": model.training_status, "candidate_stage": model.candidate_stage},
    )
    return {
        "id": model.id, "model_id": model.model_id, "model_version": model.model_version,
        "training_status": model.training_status, "candidate_stage": model.candidate_stage,
        "artifact_path": model.artifact_path, "training_run_id": model.training_run_id,
        "evaluation_metrics": json.loads(model.evaluation_metrics or "{}"),
        "error_analysis_report": json.loads(model.error_analysis_report or "{}"),
        "calibration_report": json.loads(model.calibration_report or "{}"),
    }
