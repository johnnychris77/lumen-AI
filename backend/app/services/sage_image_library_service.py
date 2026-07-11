"""Project Sage, Section 8: Image-Based Learning Library.

Curates real, already-governed `RetainedImage`/`ImageLabel` rows
(`app/models/retained_image.py` -- EXIF-stripped, consent-gated, gold-label
lifecycle) into education-ready entries. Never duplicates image bytes or the
ML-training label lifecycle; only adds the education-specific curation
fields those tables don't carry.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.retained_image import ImageLabel, RetainedImage
from app.models.sage_education import SageEducationImageEntry


def curate_image_for_education(
    db: Session, tenant_id: str, retained_image_id: int, *, anatomy_zone: str = "",
    usage_rights: str = "internal_education_use", dataset_version: str = "1.0.0",
) -> SageEducationImageEntry | None:
    """Curate one `RetainedImage` (with its best gold `ImageLabel`, if any)
    into the education library. Requires the image to already be gold-
    labeled and consent-recorded -- Sage never surfaces an unvalidated or
    non-consented image for education use."""
    image = db.query(RetainedImage).filter(RetainedImage.id == retained_image_id, RetainedImage.tenant_id == tenant_id).first()
    if image is None or not image.consent_recorded:
        return None

    label = (
        db.query(ImageLabel)
        .filter(ImageLabel.image_id == retained_image_id, ImageLabel.tenant_id == tenant_id, ImageLabel.is_gold.is_(True))
        .first()
    )
    if label is None:
        return None

    row = SageEducationImageEntry(
        tenant_id=tenant_id, retained_image_id=retained_image_id, image_label_id=label.id,
        instrument_family=image.instrument_type, anatomy_zone=anatomy_zone,
        finding_category=label.finding_type, severity=label.severity,
        supervisor_validated=bool(label.reviewer), usage_rights=usage_rights, dataset_version=dataset_version,
        phi_review_status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def mark_phi_reviewed(db: Session, tenant_id: str, entry_id: int, *, cleared: bool) -> SageEducationImageEntry | None:
    row = db.query(SageEducationImageEntry).filter(SageEducationImageEntry.id == entry_id, SageEducationImageEntry.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.phi_review_status = "cleared" if cleared else "flagged"
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: SageEducationImageEntry) -> dict:
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
        "usage_rights": row.usage_rights,
        "dataset_version": row.dataset_version,
        "phi_review_status": row.phi_review_status,
    }


def list_education_images(
    db: Session, tenant_id: str, *, instrument_family: str = "", anatomy_zone: str = "",
    finding_category: str = "", phi_cleared_only: bool = True,
) -> list[dict]:
    q = db.query(SageEducationImageEntry).filter(SageEducationImageEntry.tenant_id == tenant_id)
    if instrument_family:
        q = q.filter(SageEducationImageEntry.instrument_family == instrument_family)
    if anatomy_zone:
        q = q.filter(SageEducationImageEntry.anatomy_zone == anatomy_zone)
    if finding_category:
        q = q.filter(SageEducationImageEntry.finding_category == finding_category)
    if phi_cleared_only:
        q = q.filter(SageEducationImageEntry.phi_review_status == "cleared")
    return [to_dict(r) for r in q.order_by(SageEducationImageEntry.created_at.desc()).all()]
