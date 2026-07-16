"""Annotation Database — Sections 1, 2, 3, 4, 7: creation, relationships,
observation storage, region annotation, and version history.

`generate_annotation_id()` mirrors `app.services.ml.lcid_service.generate_lcid()`
— a dedicated per-year atomic counter, never derived from row count, so an
archived/deleted annotation's ID is never reused. Digital Twin and
baseline resolution are delegated to `lcid_service` rather than
reimplemented a second time.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_database import (
    REGION_TYPES,
    Annotation,
    AnnotationSequenceCounter,
    AnnotationVersion,
)
from app.services.enterprise_audit_service import record_enterprise_audit_event
from app.services.ml.lcid_service import instrument_digital_twin_id, resolve_baseline_id

ANN_PREFIX = "ANN"
_SEQUENCE_WIDTH = 9


class InvalidRegionTypeError(ValueError):
    pass


def generate_annotation_id(db: Session, *, at: datetime | None = None) -> str:
    year = (at or datetime.now(timezone.utc)).year
    counter = db.query(AnnotationSequenceCounter).filter(AnnotationSequenceCounter.year == year).first()
    if counter is None:
        counter = AnnotationSequenceCounter(year=year, last_sequence=0)
        db.add(counter)
        db.flush()
    counter.last_sequence += 1
    db.flush()
    return f"{ANN_PREFIX}-{year}-{counter.last_sequence:0{_SEQUENCE_WIDTH}d}"


def _snapshot(annotation: Annotation) -> dict[str, Any]:
    """A full field snapshot for the version-history record — never
    partial, so history can always be reconstructed exactly."""
    return {
        col.name: getattr(annotation, col.name)
        for col in Annotation.__table__.columns
        if col.name not in ("id", "created_at", "updated_at")
    }


def _record_version(
    db: Session, annotation: Annotation, *, editor: str, reason: str, previous_version_id: int | None,
) -> AnnotationVersion:
    version = AnnotationVersion(
        tenant_id=annotation.tenant_id,
        annotation_id=annotation.id,
        version_number=annotation.current_version,
        editor=editor,
        reason=reason,
        previous_version_id=previous_version_id,
        snapshot_json=json.dumps(_snapshot(annotation), default=str),
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def create_annotation(
    db: Session,
    *,
    tenant_id: str,
    actor: str,
    actor_role: str,
    retained_image_id: int,
    inspection_id: int | None = None,
    instrument_family: str = "",
    instrument_model: str = "",
    manufacturer: str = "",
    instrument_barcode: str = "",
    instrument_udi: str = "",
    dataset_version_id: int | None = None,
    model_version: str = "",
    primary_observation: str = "",
    secondary_observation: str = "",
    appearance_attributes: list[str] | None = None,
    severity: str = "",
    location: str = "",
    confidence: float | None = None,
    reviewer_confidence: float | None = None,
    comments: str = "",
    recommendation: str = "",
    supervisor_required: bool = False,
    unknown_flag: bool = False,
    image_quality: str = "",
    region_type: str = "whole_image_classification",
    region_coordinates: list | None = None,
    baseline_type: str = "",
    baseline_version: str = "",
    baseline_similarity: float | None = None,
    baseline_deviation: float | None = None,
) -> Annotation:
    if region_type not in REGION_TYPES:
        raise InvalidRegionTypeError(f"Unknown region_type '{region_type}'. Known: {REGION_TYPES}")

    ann_id = generate_annotation_id(db)
    digital_twin_id = instrument_digital_twin_id(
        instrument_barcode=instrument_barcode, instrument_udi=instrument_udi,
        instrument_type=instrument_family, inspection_id=inspection_id,
    )
    baseline_id = resolve_baseline_id(db, instrument_type=instrument_family, manufacturer=manufacturer)

    annotation = Annotation(
        tenant_id=tenant_id,
        ann_id=ann_id,
        retained_image_id=retained_image_id,
        inspection_id=inspection_id,
        instrument_family=instrument_family,
        instrument_model=instrument_model,
        manufacturer=manufacturer,
        digital_twin_id=digital_twin_id,
        baseline_id=baseline_id,
        reviewer=actor,
        dataset_version_id=dataset_version_id,
        model_version=model_version,
        primary_observation=primary_observation,
        secondary_observation=secondary_observation,
        appearance_attributes_json=json.dumps(appearance_attributes or []),
        severity=severity,
        location=location,
        confidence=confidence,
        reviewer_confidence=reviewer_confidence,
        comments=comments,
        recommendation=recommendation,
        supervisor_required=supervisor_required,
        unknown_flag=unknown_flag,
        image_quality=image_quality,
        region_type=region_type,
        region_coordinates_json=json.dumps(region_coordinates or []),
        review_status="UNLABELED",
        current_version=1,
        baseline_type=baseline_type,
        baseline_version=baseline_version,
        baseline_similarity=baseline_similarity,
        baseline_deviation=baseline_deviation,
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)

    _record_version(db, annotation, editor=actor, reason="Initial creation", previous_version_id=None)

    record_enterprise_audit_event(
        db, action_type="annotation_created", resource_type="annotation", resource_id=annotation.ann_id,
        tenant_id=tenant_id, actor_email=actor, actor_role=actor_role,
        details={"retained_image_id": retained_image_id, "region_type": region_type},
    )
    return annotation


_MUTABLE_FIELDS = {
    "primary_observation", "secondary_observation", "appearance_attributes_json", "severity",
    "location", "confidence", "reviewer_confidence", "comments", "recommendation",
    "supervisor_required", "unknown_flag", "image_quality", "region_type",
    "region_coordinates_json", "baseline_type", "baseline_version", "baseline_similarity",
    "baseline_deviation",
}


def update_annotation(
    db: Session, annotation: Annotation, *, editor: str, actor_role: str, reason: str, **changes: Any,
) -> Annotation:
    """Section 7 — every change creates a new version; the original history
    (each prior `AnnotationVersion` snapshot) is never edited or deleted."""
    if not reason.strip():
        raise ValueError("A reason is required for every annotation update.")

    unknown_fields = set(changes) - _MUTABLE_FIELDS
    if unknown_fields:
        raise ValueError(f"Cannot update non-mutable/unknown fields: {sorted(unknown_fields)}")

    previous_version_id = (
        db.query(AnnotationVersion)
        .filter(AnnotationVersion.annotation_id == annotation.id)
        .order_by(AnnotationVersion.version_number.desc())
        .first()
    )
    previous_version_id = previous_version_id.id if previous_version_id else None

    for field, value in changes.items():
        setattr(annotation, field, value)
    annotation.current_version += 1
    annotation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(annotation)

    _record_version(db, annotation, editor=editor, reason=reason, previous_version_id=previous_version_id)

    record_enterprise_audit_event(
        db, action_type="annotation_modified", resource_type="annotation", resource_id=annotation.ann_id,
        tenant_id=annotation.tenant_id, actor_email=editor, actor_role=actor_role,
        details={"reason": reason, "version": annotation.current_version, "fields": sorted(changes)},
    )
    return annotation


def get_annotation(db: Session, *, tenant_id: str, annotation_id: int) -> Annotation | None:
    return (
        db.query(Annotation)
        .filter(Annotation.id == annotation_id, Annotation.tenant_id == tenant_id)
        .first()
    )


def list_annotations(
    db: Session, *, tenant_id: str, retained_image_id: int | None = None,
    ground_truth_status: str | None = None,
) -> list[Annotation]:
    query = db.query(Annotation).filter(Annotation.tenant_id == tenant_id)
    if retained_image_id is not None:
        query = query.filter(Annotation.retained_image_id == retained_image_id)
    if ground_truth_status is not None:
        query = query.filter(Annotation.ground_truth_status == ground_truth_status)
    return query.order_by(Annotation.id.asc()).all()


def version_history(db: Session, *, annotation_id: int) -> list[AnnotationVersion]:
    return (
        db.query(AnnotationVersion)
        .filter(AnnotationVersion.annotation_id == annotation_id)
        .order_by(AnnotationVersion.version_number.asc())
        .all()
    )
