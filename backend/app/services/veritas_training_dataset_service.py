"""Project Veritas, Section 15: Training Dataset Assurance.

Gates a real `RetainedImage`/`ImageLabel` pair into a training-dataset
status -- mirrors Sage's `SageEducationImageEntry` reference-by-ID pattern,
extended with the training-specific checks this section names (confirmed
finding/severity, image quality threshold, duplicate detection). Never
allows an unvalidated inspection image into `approved_for_training`.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.retained_image import ImageLabel, RetainedImage
from app.models.veritas_evidence import (
    DATASET_APPROVED_FOR_TRAINING,
    DATASET_EXCLUDED,
    DATASET_PENDING_VALIDATION,
    DATASET_QUARANTINED,
    VeritasTrainingDatasetEntry,
)


def _is_duplicate(db: Session, tenant_id: str, sha256: str, exclude_image_id: int) -> bool:
    if not sha256:
        return False
    return (
        db.query(RetainedImage)
        .filter(RetainedImage.tenant_id == tenant_id, RetainedImage.sha256 == sha256, RetainedImage.id != exclude_image_id)
        .first()
        is not None
    )


def evaluate_for_training(
    db: Session, tenant_id: str, retained_image_id: int, *, instrument_family: str = "", anatomy_zone: str = "",
    usage_rights: str = "", image_quality_threshold_met: bool = False,
) -> VeritasTrainingDatasetEntry:
    """Section 15: evaluate one image against every named gate and persist
    the resulting dataset status + reason."""
    image = db.query(RetainedImage).filter(RetainedImage.id == retained_image_id, RetainedImage.tenant_id == tenant_id).first()
    if image is None:
        raise ValueError("Retained image not found for this tenant")

    label = (
        db.query(ImageLabel)
        .filter(ImageLabel.image_id == retained_image_id, ImageLabel.tenant_id == tenant_id)
        .order_by(ImageLabel.is_gold.desc(), ImageLabel.created_at.desc())
        .first()
    )

    is_duplicate = _is_duplicate(db, tenant_id, image.sha256, retained_image_id)
    supervisor_validated = bool(label and label.is_gold)
    phi_review_status = "cleared" if image.exif_stripped and image.consent_recorded else "pending"
    provenance_complete = bool(image.sha256 and image.consent_recorded and image.uploaded_by)
    finding_confirmed = bool(label and label.finding_type)
    severity_labeled = bool(label and label.severity)

    reasons = []
    if is_duplicate:
        reasons.append("duplicate image detected")
    if not supervisor_validated:
        reasons.append("not supervisor-validated (gold label required)")
    if phi_review_status != "cleared":
        reasons.append("PHI review not cleared")
    if not usage_rights:
        reasons.append("usage rights not declared")
    if not image_quality_threshold_met:
        reasons.append("image quality threshold not met")
    if not finding_confirmed:
        reasons.append("finding not confirmed")
    if not severity_labeled:
        reasons.append("severity not labeled")
    if not provenance_complete:
        reasons.append("provenance incomplete")

    if is_duplicate:
        status = DATASET_QUARANTINED
    elif not image.consent_recorded:
        status = DATASET_EXCLUDED
    elif reasons:
        status = DATASET_PENDING_VALIDATION
    else:
        status = DATASET_APPROVED_FOR_TRAINING

    row = VeritasTrainingDatasetEntry(
        tenant_id=tenant_id, retained_image_id=retained_image_id, image_label_id=label.id if label else None,
        instrument_family=instrument_family or image.instrument_type, anatomy_zone=anatomy_zone,
        finding_category=label.finding_type if label else "", severity=label.severity if label else "",
        supervisor_validated=supervisor_validated, image_quality_threshold_met=image_quality_threshold_met,
        usage_rights=usage_rights, phi_review_status=phi_review_status, is_duplicate=is_duplicate,
        provenance_complete=provenance_complete, dataset_status=status,
        status_reason="; ".join(reasons) if reasons else "All training-readiness checks passed.",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: VeritasTrainingDatasetEntry) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "retained_image_id": row.retained_image_id,
        "image_label_id": row.image_label_id,
        "instrument_family": row.instrument_family,
        "anatomy_zone": row.anatomy_zone,
        "finding_category": row.finding_category,
        "severity": row.severity,
        "supervisor_validated": row.supervisor_validated,
        "image_quality_threshold_met": row.image_quality_threshold_met,
        "usage_rights": row.usage_rights,
        "dataset_version": row.dataset_version,
        "phi_review_status": row.phi_review_status,
        "is_duplicate": row.is_duplicate,
        "provenance_complete": row.provenance_complete,
        "dataset_status": row.dataset_status,
        "status_reason": row.status_reason,
    }


def list_dataset_entries(db: Session, tenant_id: str, *, dataset_status: str = "") -> list[dict]:
    q = db.query(VeritasTrainingDatasetEntry).filter(VeritasTrainingDatasetEntry.tenant_id == tenant_id)
    if dataset_status:
        q = q.filter(VeritasTrainingDatasetEntry.dataset_status == dataset_status)
    return [to_dict(r) for r in q.order_by(VeritasTrainingDatasetEntry.created_at.desc()).all()]
