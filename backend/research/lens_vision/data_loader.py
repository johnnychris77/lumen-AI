"""Tenant-scoped, usage-authorized, ground-truth-aware research sample loader.

Loads samples for a research experiment from the GOVERNED dataset registry +
retained-image store. A sample is included only when it passes the full Project
Canvas usage authorization (``governance.authorize_research_entry`` — tenant,
provenance, rights/quality/PHI/archival, retention, and clinical research-use
scope) and carries an authoritative ground-truth status. Ground truth is read
from the Annotation Database and is NEVER defaulted — an unlabeled image is
labeled ``unlabeled``, not silently treated as normal.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.dataset_governance import DatasetRegistryEntry
from app.models.retained_image import RetainedImage
from app.services.ml.lcid_service import is_untracked_twin
from research.lens_vision.governance import (
    GT_UNLABELED,
    GT_VERIFIED_NORMAL,
    authorize_research_entry,
    ground_truth_status,
)


def load_research_samples(
    db: Session, *, tenant_id: str, dataset_version_id: int | None = None,
    allow_approved_clinical: bool = False, limit: int = 1000, require_ground_truth: bool = True,
) -> list[dict]:
    """Return usage-authorized, tenant-scoped, ground-truth-aware research samples.

    ``require_ground_truth`` (default True) drops images with no ACTIVE
    annotation, so an unlabeled image can never enter a labeled research cohort.
    """
    q = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.tenant_id == tenant_id)
    if dataset_version_id is not None:
        q = q.filter(DatasetRegistryEntry.dataset_version_id == dataset_version_id)
    entries = q.order_by(DatasetRegistryEntry.id.asc()).limit(limit).all()

    samples: list[dict] = []
    for entry in entries:
        if authorize_research_entry(
            db, entry, tenant_id=tenant_id, allow_approved_clinical=allow_approved_clinical,
        ) is not None:
            continue
        retained = (
            db.query(RetainedImage)
            .filter(
                RetainedImage.id == entry.retained_image_id,
                RetainedImage.tenant_id == tenant_id,  # tenant-scoped: no cross-tenant bytes
            )
            .first()
        )
        if retained is None or not retained.image_bytes:
            continue

        gt_status, gt_label = ground_truth_status(
            db, tenant_id=tenant_id, retained_image_id=entry.retained_image_id,
        )
        if require_ground_truth and gt_status == GT_UNLABELED:
            continue  # never fabricate a label for an unlabeled image

        # Reject an untracked digital twin as a reliable physical-instrument serial.
        twin = entry.digital_twin_id or ""
        serial = twin if (twin and not is_untracked_twin(twin)) else None

        samples.append({
            "id": entry.id,
            "label": gt_label,                 # None for unknown/unlabeled — never defaulted
            "ground_truth_status": gt_status,
            "image_bytes": retained.image_bytes,
            "image_sha256": entry.image_sha256,
            "tenant_id": tenant_id,
            "data_provenance_class": entry.data_provenance_class,
            "provenance_approval_status": entry.provenance_approval_status,
            "instrument_family": entry.instrument_family,
            "manufacturer": entry.manufacturer,
            "anatomy_zone": entry.anatomy_zone,
            "image_quality": entry.image_quality or "unknown",
            "inspection_id": entry.inspection_id,
            "specimen_id": entry.provenance_specimen_id or entry.instrument_id or "",
            "instrument_serial": serial,
        })
    return samples


def verified_normal_only(samples: list[dict]) -> list[dict]:
    """Keep only VERIFIED-NORMAL images — the only images admissible as the
    'normal' class for normal-only anomaly training/evaluation. Unlabeled,
    unknown, and abnormal images are excluded (never contaminate the normal set).
    """
    return [s for s in samples if s.get("ground_truth_status") == GT_VERIFIED_NORMAL]
