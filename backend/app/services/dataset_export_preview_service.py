"""Project Canvas — Section 18: Export Preview.

Wraps the already-governed `app.services.annotation_export_service.
export_annotations` (7 formats: classification/yolo/coco/pascal_voc/
segmentation/csv/json, honest `annotation_available: false` for
region-dependent formats with no real region data) with the summary
Section 18 asks a reviewer to see before committing to a release: record
count, excluded count, class distribution, missing-data warnings, the
dataset version(s) and Ground Truth version(s) the export draws from, and
an export timestamp. No new export format or fabricated region data is
introduced here.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_database import GROUND_TRUTH_ACTIVE, Annotation
from app.services import annotation_export_service


def preview_export(
    db: Session, *, tenant_id: str, export_format: str, output_dir: Path | None = None,
) -> dict[str, Any]:
    all_ground_truth = (
        db.query(Annotation)
        .filter(Annotation.tenant_id == tenant_id, Annotation.ground_truth_status == GROUND_TRUTH_ACTIVE)
        .all()
    )
    total_annotations = (
        db.query(Annotation).filter(Annotation.tenant_id == tenant_id).count()
    )

    result = annotation_export_service.export_annotations(
        db, tenant_id=tenant_id, export_format=export_format, ground_truth_only=True, output_dir=output_dir,
    )

    class_distribution = dict(Counter(a.primary_observation or "unlabeled" for a in all_ground_truth))
    missing_region_count = sum(
        1 for rec in _records_from_payload(result["payload"])
        if rec.get("annotation_available") is False
    )

    return {
        "export_format": result["export_format"],
        "record_count": result["record_count"],
        "excluded_count": max(total_annotations - result["record_count"], 0),
        "class_distribution": class_distribution,
        "missing_data_warnings": (
            [f"{missing_region_count} record(s) have no stored region data for this format; "
             "exported with annotation_available: false rather than a fabricated region."]
            if missing_region_count else []
        ),
        "dataset_versions": sorted({a.dataset_version_id for a in all_ground_truth if a.dataset_version_id is not None}),
        "ground_truth_versions": sorted({a.ground_truth_version for a in all_ground_truth}),
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "export_path": result["export_path"],
    }


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "records" in payload:
        return payload["records"]
    if isinstance(payload, dict) and "annotations" in payload:
        return payload["annotations"]
    return []
