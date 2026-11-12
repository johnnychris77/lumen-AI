"""Tenant-scoped, research-authorized sample loader (read-only).

Loads samples for a research experiment from the GOVERNED dataset registry and
retained-image store, strictly scoped to one tenant and filtered to
research-authorized provenance. It never reaches across tenants and never pulls
clinical data unless it is explicitly approved and the caller opts in.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.dataset_governance import DatasetRegistryEntry
from app.models.retained_image import RetainedImage
from research.lens_vision.provenance import is_research_authorized


def load_research_samples(
    db: Session, *, tenant_id: str, dataset_version_id: int | None = None,
    allow_approved_clinical: bool = False, limit: int = 1000,
) -> list[dict]:
    """Return research-authorized, tenant-scoped samples in the benchmark shape.

    Both the registry query and the retained-image lookup are scoped to
    ``tenant_id`` — no other tenant's rows or image bytes can be returned.
    """
    q = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.tenant_id == tenant_id)
    if dataset_version_id is not None:
        q = q.filter(DatasetRegistryEntry.dataset_version_id == dataset_version_id)
    entries = q.order_by(DatasetRegistryEntry.id.asc()).limit(limit).all()

    samples: list[dict] = []
    for entry in entries:
        candidate = {
            "data_provenance_class": entry.data_provenance_class,
            "provenance_approval_status": entry.provenance_approval_status,
        }
        if not is_research_authorized(candidate, allow_approved_clinical=allow_approved_clinical):
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
        samples.append({
            "id": entry.id,
            "label": entry.current_label or "no_observable_abnormality",
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
            "instrument_serial": entry.digital_twin_id or None,
        })
    return samples
