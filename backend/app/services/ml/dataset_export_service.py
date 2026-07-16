"""LCID Sprint 1 — Section 11: Dataset Export.

Exports a dataset version's eligible entries (reusing
`dataset_builder.eligible_entries` rather than re-deriving eligibility) to a
real manifest file under `/dataset/exports/`, preserving every metadata
field Section 3 requires. Four formats are supported per the spec:
classification, object_detection, segmentation, multi_label.

Honesty constraint: this registry has never stored a real bounding box or
pixel mask (no annotation tool for either exists in this codebase). The
object_detection and segmentation exports include the field the format
expects (`bounding_boxes`/`masks`) but leave it an empty list with an
explicit `"annotation_available": false` note rather than fabricate a box
or mask — see `docs/lcid/DATASET_SPECIFICATION.md`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset_governance import DatasetRegistryEntry
from app.services.ml.dataset_builder import eligible_entries

EXPORT_FORMATS = ("classification", "object_detection", "segmentation", "multi_label")

# Resolved relative to the repository root (three levels up from
# backend/app/services/ml/).
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_EXPORT_DIR = _REPO_ROOT / "dataset" / "exports"


class UnsupportedExportFormatError(ValueError):
    pass


def _entry_record(entry: DatasetRegistryEntry, export_format: str) -> dict[str, Any]:
    base = {
        "lcid": entry.lcid,
        "dataset_entry_id": entry.id,
        "retained_image_id": entry.retained_image_id,
        "inspection_id": entry.inspection_id,
        "instrument_family": entry.instrument_family,
        "instrument_model": entry.instrument_model,
        "manufacturer": entry.manufacturer,
        "anatomy_zone": entry.anatomy_zone,
        "image_quality": entry.image_quality,
        "label": entry.current_label or "unlabeled",
        "review_status": entry.review_status,
        "split_assignment": entry.split_assignment or "unassigned",
        "usage_rights": entry.usage_rights,
        "digital_twin_id": entry.digital_twin_id,
        "baseline_id": entry.baseline_id,
        "image_sha256": entry.image_sha256,
    }
    if export_format == "object_detection":
        base["bounding_boxes"] = []
        base["annotation_available"] = False
    elif export_format == "segmentation":
        base["masks"] = []
        base["annotation_available"] = False
    elif export_format == "multi_label":
        base["labels"] = [entry.current_label] if entry.current_label else []
    return base


def export_dataset(
    db: Session, *, tenant_id: str, dataset_version_id: int, export_format: str,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    if export_format not in EXPORT_FORMATS:
        raise UnsupportedExportFormatError(f"Unknown export format '{export_format}'. Known: {EXPORT_FORMATS}")

    entries, excluded = eligible_entries(db, tenant_id=tenant_id, dataset_version_id=dataset_version_id)
    records = [_entry_record(e, export_format) for e in entries]

    manifest = {
        "dataset_version_id": dataset_version_id,
        "export_format": export_format,
        "record_count": len(records),
        "excluded": excluded,
        "records": records,
    }

    target_dir = output_dir or DEFAULT_EXPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / f"dataset_v{dataset_version_id}_{export_format}.json"
    out_path.write_text(json.dumps(manifest, indent=2, default=str))
    manifest["export_path"] = str(out_path)
    return manifest
