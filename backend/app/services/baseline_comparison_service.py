"""Project Canvas — Section 14: Baseline Comparison.

Resolves whichever of the four baseline types the codebase already tracks
for one dataset image, without inventing a new baseline concept:

  * manufacturer/vendor — `BaselineLibraryEntry` via the same `baseline_id`
    `app.services.ml.dataset_registry.register_image` already resolved
    (`app.services.ml.lcid_service.resolve_baseline_id`).
  * organization (hospital-contributed) — the same `BaselineLibraryEntry`
    table, filtered to `baseline_type == "network_contributed"`.
  * Digital Twin historical baseline — a sibling `DatasetRegistryEntry`
    sharing `digital_twin_id` with `image_type == baseline_reference`.
  * approved research baseline — a sibling `DatasetRegistryEntry` with
    `image_type == research_reference` and Ground-Truth-approved
    (`review_status == APPROVED`), matching instrument family + manufacturer.

Any bucket that resolves to nothing is reported as unavailable with a
concrete reason — never presented as an authoritative baseline.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.baseline_library import BaselineLibraryEntry
from app.models.dataset_governance import APPROVED, IMAGE_TYPE_BASELINE_REFERENCE, IMAGE_TYPE_RESEARCH_REFERENCE, DatasetRegistryEntry


def _library_entry_view(row: BaselineLibraryEntry) -> dict[str, Any]:
    return {
        "id": row.id, "manufacturer_name": row.manufacturer_name, "model_name": row.model_name,
        "baseline_type": row.baseline_type, "baseline_version": row.baseline_version,
        "approval_status": row.approval_status, "approved_by": row.approved_by,
        "contributing_facilities": row.contributing_facilities,
    }


def _entry_view(row: DatasetRegistryEntry) -> dict[str, Any]:
    return {
        "id": row.id, "lcid": row.lcid, "image_type": row.image_type,
        "review_status": row.review_status, "digital_twin_id": row.digital_twin_id,
        "retained_image_id": row.retained_image_id,
    }


def compare_to_baselines(db: Session, *, tenant_id: str, entry_id: int) -> dict[str, Any]:
    entry = (
        db.query(DatasetRegistryEntry)
        .filter(DatasetRegistryEntry.id == entry_id, DatasetRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if entry is None:
        return {"found": False, "reason": "Dataset entry not found."}

    baselines: dict[str, Any] = {}

    manufacturer_baseline = None
    if entry.baseline_id is not None:
        manufacturer_baseline = db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.id == entry.baseline_id).first()
    if manufacturer_baseline is not None and manufacturer_baseline.approval_status == "approved":
        baselines["manufacturer"] = {"available": True, "source": _library_entry_view(manufacturer_baseline)}
    else:
        baselines["manufacturer"] = {"available": False, "reason": "No approved manufacturer/vendor baseline resolved for this instrument."}

    organization_baseline = (
        db.query(BaselineLibraryEntry)
        .filter(
            BaselineLibraryEntry.instrument_category == entry.instrument_family,
            BaselineLibraryEntry.baseline_type == "network_contributed",
            BaselineLibraryEntry.approval_status == "approved",
        )
        .first()
    )
    if organization_baseline is not None:
        baselines["organization"] = {"available": True, "source": _library_entry_view(organization_baseline)}
    else:
        baselines["organization"] = {"available": False, "reason": "No approved organization-contributed baseline exists for this instrument category."}

    digital_twin_baseline = None
    if entry.digital_twin_id:
        digital_twin_baseline = (
            db.query(DatasetRegistryEntry)
            .filter(
                DatasetRegistryEntry.tenant_id == tenant_id,
                DatasetRegistryEntry.digital_twin_id == entry.digital_twin_id,
                DatasetRegistryEntry.image_type == IMAGE_TYPE_BASELINE_REFERENCE,
                DatasetRegistryEntry.id != entry.id,
            )
            .order_by(DatasetRegistryEntry.created_at.asc())
            .first()
        )
    if digital_twin_baseline is not None:
        baselines["digital_twin"] = {"available": True, "source": _entry_view(digital_twin_baseline)}
    else:
        baselines["digital_twin"] = {"available": False, "reason": "No baseline-reference image is linked to this instrument's Digital Twin history."}

    research_baseline = (
        db.query(DatasetRegistryEntry)
        .filter(
            DatasetRegistryEntry.tenant_id == tenant_id,
            DatasetRegistryEntry.image_type == IMAGE_TYPE_RESEARCH_REFERENCE,
            DatasetRegistryEntry.review_status == APPROVED,
            DatasetRegistryEntry.instrument_family == entry.instrument_family,
            DatasetRegistryEntry.manufacturer == entry.manufacturer,
            DatasetRegistryEntry.id != entry.id,
        )
        .first()
    )
    if research_baseline is not None:
        baselines["research"] = {"available": True, "source": _entry_view(research_baseline)}
    else:
        baselines["research"] = {"available": False, "reason": "No Ground-Truth-approved research-reference baseline matches this instrument family and manufacturer."}

    return {
        "found": True,
        "current_entry": _entry_view(entry),
        "baselines": baselines,
        "any_baseline_available": any(b["available"] for b in baselines.values()),
    }
