"""Annotation Database — Section 12: Dataset Export.

Exports Ground-Truth-eligible annotations (ACTIVE only, per Section 6/"no
model may be trained using annotations outside this governed system") to
real files under `/dataset/exports/annotations/`, preserving every
metadata relationship. Formats: classification, yolo, coco, pascal_voc,
segmentation, csv, json.

Honesty constraint (same discipline as
`app.services.ml.dataset_export_service`): a region-dependent format
(yolo/coco/pascal_voc/segmentation) only emits real coordinates when the
annotation's `region_type` and `region_coordinates_json` actually contain
them. Nothing is fabricated — an annotation with no region data is
reported with `annotation_available: false` for that format rather than
a synthesized box or mask.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_database import (
    GROUND_TRUTH_ACTIVE,
    REGION_BOUNDING_BOX,
    REGION_POLYGON,
    REGION_SEGMENTATION_MASK,
    Annotation,
)

EXPORT_FORMATS = ("classification", "yolo", "coco", "pascal_voc", "segmentation", "csv", "json")

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXPORT_DIR = _REPO_ROOT / "dataset" / "exports" / "annotations"


class UnsupportedExportFormatError(ValueError):
    pass


def _eligible(db: Session, *, tenant_id: str, ground_truth_only: bool) -> list[Annotation]:
    query = db.query(Annotation).filter(Annotation.tenant_id == tenant_id)
    if ground_truth_only:
        query = query.filter(Annotation.ground_truth_status == GROUND_TRUTH_ACTIVE)
    return query.order_by(Annotation.id.asc()).all()


def _has_region(a: Annotation) -> bool:
    try:
        coords = json.loads(a.region_coordinates_json or "[]")
    except json.JSONDecodeError:
        coords = []
    return bool(coords) and a.region_type in (REGION_BOUNDING_BOX, REGION_POLYGON, REGION_SEGMENTATION_MASK)


def _base_record(a: Annotation) -> dict[str, Any]:
    return {
        "ann_id": a.ann_id,
        "retained_image_id": a.retained_image_id,
        "inspection_id": a.inspection_id,
        "instrument_family": a.instrument_family,
        "manufacturer": a.manufacturer,
        "digital_twin_id": a.digital_twin_id,
        "baseline_id": a.baseline_id,
        "dataset_version_id": a.dataset_version_id,
        "label": a.primary_observation or "unlabeled",
        "severity": a.severity,
        "confidence": a.confidence,
        "ground_truth_status": a.ground_truth_status,
        "ground_truth_version": a.ground_truth_version,
    }


def _classification_records(annotations: list[Annotation]) -> list[dict[str, Any]]:
    return [_base_record(a) for a in annotations]


def _yolo_records(annotations: list[Annotation]) -> list[dict[str, Any]]:
    records = []
    for a in annotations:
        rec = _base_record(a)
        if a.region_type == REGION_BOUNDING_BOX and _has_region(a):
            coords = json.loads(a.region_coordinates_json)
            rec["yolo_line"] = f"{rec['label']} " + " ".join(str(c) for c in coords)
            rec["annotation_available"] = True
        else:
            rec["yolo_line"] = None
            rec["annotation_available"] = False
        records.append(rec)
    return records


def _coco_manifest(annotations: list[Annotation]) -> dict[str, Any]:
    images, coco_annotations, categories = [], [], {}
    for a in annotations:
        images.append({"id": a.retained_image_id, "ann_id": a.ann_id})
        label = a.primary_observation or "unlabeled"
        if label not in categories:
            categories[label] = len(categories) + 1
        if a.region_type in (REGION_BOUNDING_BOX, REGION_POLYGON) and _has_region(a):
            coords = json.loads(a.region_coordinates_json)
            entry: dict[str, Any] = {
                "id": a.id, "image_id": a.retained_image_id, "category_id": categories[label],
                "annotation_available": True,
            }
            if a.region_type == REGION_BOUNDING_BOX:
                entry["bbox"] = coords
            else:
                entry["segmentation"] = [coords]
            coco_annotations.append(entry)
        else:
            coco_annotations.append({
                "id": a.id, "image_id": a.retained_image_id, "category_id": categories[label],
                "annotation_available": False,
            })
    return {
        "images": images,
        "annotations": coco_annotations,
        "categories": [{"id": i, "name": name} for name, i in categories.items()],
    }


def _pascal_voc_records(annotations: list[Annotation]) -> list[dict[str, Any]]:
    records = []
    for a in annotations:
        rec = _base_record(a)
        if a.region_type == REGION_BOUNDING_BOX and _has_region(a):
            coords = json.loads(a.region_coordinates_json)
            xmin, ymin, xmax, ymax = (coords + [0, 0, 0, 0])[:4]
            rec["xml"] = (
                f"<annotation><object><name>{rec['label']}</name>"
                f"<bndbox><xmin>{xmin}</xmin><ymin>{ymin}</ymin>"
                f"<xmax>{xmax}</xmax><ymax>{ymax}</ymax></bndbox></object></annotation>"
            )
            rec["annotation_available"] = True
        else:
            rec["xml"] = None
            rec["annotation_available"] = False
        records.append(rec)
    return records


def _segmentation_records(annotations: list[Annotation]) -> list[dict[str, Any]]:
    records = []
    for a in annotations:
        rec = _base_record(a)
        if a.region_type == REGION_SEGMENTATION_MASK and _has_region(a):
            rec["mask"] = json.loads(a.region_coordinates_json)
            rec["annotation_available"] = True
        else:
            rec["mask"] = None
            rec["annotation_available"] = False
        records.append(rec)
    return records


def export_annotations(
    db: Session, *, tenant_id: str, export_format: str, ground_truth_only: bool = True,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    if export_format not in EXPORT_FORMATS:
        raise UnsupportedExportFormatError(f"Unknown export format '{export_format}'. Known: {EXPORT_FORMATS}")

    annotations = _eligible(db, tenant_id=tenant_id, ground_truth_only=ground_truth_only)
    target_dir = output_dir or DEFAULT_EXPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    if export_format == "classification":
        payload: Any = {"records": _classification_records(annotations)}
        out_path = target_dir / f"annotations_{tenant_id}_classification.json"
        out_path.write_text(json.dumps(payload, indent=2, default=str))
    elif export_format == "yolo":
        payload = {"records": _yolo_records(annotations)}
        out_path = target_dir / f"annotations_{tenant_id}_yolo.json"
        out_path.write_text(json.dumps(payload, indent=2, default=str))
    elif export_format == "coco":
        payload = _coco_manifest(annotations)
        out_path = target_dir / f"annotations_{tenant_id}_coco.json"
        out_path.write_text(json.dumps(payload, indent=2, default=str))
    elif export_format == "pascal_voc":
        payload = {"records": _pascal_voc_records(annotations)}
        out_path = target_dir / f"annotations_{tenant_id}_pascal_voc.json"
        out_path.write_text(json.dumps(payload, indent=2, default=str))
    elif export_format == "segmentation":
        payload = {"records": _segmentation_records(annotations)}
        out_path = target_dir / f"annotations_{tenant_id}_segmentation.json"
        out_path.write_text(json.dumps(payload, indent=2, default=str))
    elif export_format == "csv":
        records = _classification_records(annotations)
        _csv_fieldnames = [
            "ann_id", "retained_image_id", "inspection_id", "instrument_family", "manufacturer",
            "digital_twin_id", "baseline_id", "dataset_version_id", "label", "severity",
            "confidence", "ground_truth_status", "ground_truth_version",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_csv_fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)
        out_path = target_dir / f"annotations_{tenant_id}.csv"
        out_path.write_text(buf.getvalue())
        payload = {"records": records}
    else:  # json
        payload = {"records": [_base_record(a) for a in annotations]}
        out_path = target_dir / f"annotations_{tenant_id}.json"
        out_path.write_text(json.dumps(payload, indent=2, default=str))

    return {
        "export_format": export_format,
        "record_count": len(annotations),
        "export_path": str(out_path),
        "ground_truth_only": ground_truth_only,
        "payload": payload,
    }
