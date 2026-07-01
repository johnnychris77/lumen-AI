"""ML image labeling + dataset-export endpoints.

Backs the training-data pipeline described in
``docs/ai/model-training-dataset-plan.md``. Retained images (opt-in, EXIF
stripped) are labeled here, reviewed/adjudicated, and exported as a manifest for
training a real image-based model that would eventually replace the pilot
Baseline Comparison Scoring Model.

Governance:
- Retention/labeling is access-controlled (operator/spd_manager/admin to label;
  spd_manager/admin to adjudicate/export).
- Critical classes (blood, crack, missing_component) require two distinct
  reviewers before a label is promoted to ``gold``.
- Every label mutation is audit-logged.
- Output remains advisory tooling — no diagnostic-accuracy/FDA claims.
"""
from __future__ import annotations

import io
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.retained_image import ImageLabel, RetainedImage
from app.routes.inspections import require_inspection_runner
from app.services.image_retention_service import (
    retain_image,
    retention_enabled,
)

router = APIRouter(prefix="/ml", tags=["ml-images"])

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024

# Classes requiring two distinct reviewers before promotion to gold.
_CRITICAL_CLASSES = {"blood", "crack", "missing_component"}

# Known finding classes (multi-label). "clean" is the negative anchor class.
_KNOWN_CLASSES = {
    "blood", "bone", "tissue", "bioburden", "debris", "other_organic_residue",
    "rust", "discoloration", "corrosion", "pitting", "crack",
    "insulation_damage", "missing_component", "clean",
}


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


@router.get("/retention/status")
def retention_status(current_user=Depends(require_inspection_runner)):
    """Report whether opt-in image retention is enabled for this deployment."""
    return {
        "retention_enabled": retention_enabled(),
        "note": (
            "Image retention is opt-in (RETAIN_INSPECTION_IMAGES) and requires "
            "recorded consent. Bytes are EXIF-stripped on ingest. Disabled by "
            "default — only SHA-256 hashes are stored otherwise."
        ),
    }


@router.post("/images", status_code=201)
async def upload_training_image(
    request: Request,
    images: List[UploadFile] = File(...),
    instrument_type: str = "unknown",
    source: str = "inspection",
    consent: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_inspection_runner),
):
    """Retain EXIF-stripped image bytes for labeling (opt-in).

    No-op (returns ``retained: false``) unless retention is enabled AND
    ``consent=true`` is passed — the safe default. Images must contain
    instruments only; PHI in frame is rejected by policy.
    """
    if not retention_enabled():
        raise HTTPException(
            status_code=409,
            detail=(
                "Image retention is disabled. Set RETAIN_INSPECTION_IMAGES to "
                "enable the opt-in training-image store."
            ),
        )
    tenant_id = get_request_tenant_id(request)
    stored = []
    for img in images:
        content_type = img.content_type or ""
        if content_type not in _ALLOWED_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"File '{img.filename}' has unsupported type '{content_type}'.",
            )
        data = await img.read()
        if len(data) > _MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{img.filename}' exceeds 10 MB limit.",
            )
        row = retain_image(
            db,
            data=data,
            tenant_id=tenant_id,
            instrument_type=instrument_type,
            content_type=content_type,
            source=source,
            uploaded_by=_actor(current_user),
            consent=consent,
        )
        if row is None:
            raise HTTPException(
                status_code=400,
                detail="Consent is required to retain images (pass consent=true).",
            )
        stored.append({
            "id": row.id,
            "deident_name": row.deident_name,
            "sha256": row.sha256,
            "exif_stripped": row.exif_stripped,
            "size_bytes": row.size_bytes,
        })
        log_audit_event(
            db,
            tenant_id=tenant_id,
            tenant_name=tenant_id,
            actor_email=_actor(current_user),
            actor_role=getattr(current_user, "role", "operator"),
            action_type="training_image_retained",
            resource_type="retained_image",
            resource_id=str(row.id),
        )
    return {"retained": True, "count": len(stored), "images": stored}


@router.get("/images")
def list_images(
    request: Request,
    label_status: Optional[str] = None,
    instrument_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_inspection_runner),
):
    """List retained-image metadata (never bytes) for the caller's tenant."""
    tenant_id = get_request_tenant_id(request)
    q = db.query(RetainedImage).filter(RetainedImage.tenant_id == tenant_id)
    if label_status:
        q = q.filter(RetainedImage.label_status == label_status)
    if instrument_type:
        q = q.filter(RetainedImage.instrument_type == instrument_type)
    rows = q.order_by(RetainedImage.id.desc()).all()
    return {
        "count": len(rows),
        "images": [
            {
                "id": r.id,
                "deident_name": r.deident_name,
                "instrument_type": r.instrument_type,
                "sha256": r.sha256,
                "size_bytes": r.size_bytes,
                "exif_stripped": r.exif_stripped,
                "source": r.source,
                "label_status": r.label_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/images/{image_id}/bytes")
def get_image_bytes(
    image_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_inspection_runner),
):
    """Download the EXIF-stripped bytes for a retained image (access-controlled)."""
    tenant_id = get_request_tenant_id(request)
    row = (
        db.query(RetainedImage)
        .filter(RetainedImage.id == image_id, RetainedImage.tenant_id == tenant_id)
        .first()
    )
    if row is None or row.image_bytes is None:
        raise HTTPException(status_code=404, detail="Retained image not found.")
    return StreamingResponse(
        io.BytesIO(row.image_bytes),
        media_type=row.content_type or "application/octet-stream",
    )


class LabelIn(BaseModel):
    finding_type: str = Field(..., min_length=1, max_length=50)
    present: bool = True
    severity: str = Field("", max_length=30)
    region: Optional[List[float]] = None  # [x, y, w, h] normalized 0..1
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    notes: str = Field("", max_length=1000)


@router.post("/images/{image_id}/labels", status_code=201)
def add_label(
    image_id: int,
    body: LabelIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_inspection_runner),
):
    """Apply a (multi-label) annotation to a retained image."""
    tenant_id = get_request_tenant_id(request)
    image = (
        db.query(RetainedImage)
        .filter(RetainedImage.id == image_id, RetainedImage.tenant_id == tenant_id)
        .first()
    )
    if image is None:
        raise HTTPException(status_code=404, detail="Retained image not found.")

    finding = body.finding_type.strip().lower().replace(" ", "_")
    if finding not in _KNOWN_CLASSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown finding_type '{finding}'. Allowed: {sorted(_KNOWN_CLASSES)}",
        )

    region_json = json.dumps(body.region) if body.region else ""
    label = ImageLabel(
        image_id=image_id,
        tenant_id=tenant_id,
        finding_type=finding,
        present=body.present,
        severity=body.severity,
        region_json=region_json,
        confidence=body.confidence,
        reviewer=_actor(current_user),
        notes=body.notes,
    )
    db.add(label)
    if image.label_status == "unlabeled":
        image.label_status = "labeled"
    db.commit()
    db.refresh(label)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", "operator"),
        action_type="image_label_added",
        resource_type="image_label",
        resource_id=str(label.id),
    )
    return {
        "id": label.id,
        "image_id": image_id,
        "finding_type": label.finding_type,
        "severity": label.severity,
        "critical_class": finding in _CRITICAL_CLASSES,
        "requires_second_reviewer": finding in _CRITICAL_CLASSES,
    }


@router.get("/images/{image_id}/labels")
def list_labels(
    image_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_inspection_runner),
):
    """Return all labels for an image."""
    tenant_id = get_request_tenant_id(request)
    labels = (
        db.query(ImageLabel)
        .filter(ImageLabel.image_id == image_id, ImageLabel.tenant_id == tenant_id)
        .order_by(ImageLabel.id)
        .all()
    )
    return {
        "image_id": image_id,
        "count": len(labels),
        "labels": [
            {
                "id": lb.id,
                "finding_type": lb.finding_type,
                "present": lb.present,
                "severity": lb.severity,
                "region": json.loads(lb.region_json) if lb.region_json else None,
                "confidence": lb.confidence,
                "reviewer": lb.reviewer,
                "adjudicated": lb.adjudicated,
                "is_gold": lb.is_gold,
            }
            for lb in labels
        ],
    }


@router.post("/images/{image_id}/labels/{label_id}/adjudicate")
def adjudicate_label(
    image_id: int,
    label_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Promote a reviewed label to ``gold``.

    Critical classes (blood, crack, missing_component) require a SECOND distinct
    reviewer on the same image+class before they can be adjudicated — enforcing
    the two-reviewer rule from the dataset plan.
    """
    tenant_id = get_request_tenant_id(request)
    label = (
        db.query(ImageLabel)
        .filter(
            ImageLabel.id == label_id,
            ImageLabel.image_id == image_id,
            ImageLabel.tenant_id == tenant_id,
        )
        .first()
    )
    if label is None:
        raise HTTPException(status_code=404, detail="Label not found.")

    if label.finding_type in _CRITICAL_CLASSES:
        distinct_reviewers = {
            lb.reviewer
            for lb in db.query(ImageLabel).filter(
                ImageLabel.image_id == image_id,
                ImageLabel.tenant_id == tenant_id,
                ImageLabel.finding_type == label.finding_type,
            )
        }
        if len(distinct_reviewers) < 2:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Critical class '{label.finding_type}' requires two distinct "
                    "reviewers before adjudication."
                ),
            )

    label.adjudicated = True
    label.is_gold = True
    image = (
        db.query(RetainedImage)
        .filter(RetainedImage.id == image_id, RetainedImage.tenant_id == tenant_id)
        .first()
    )
    if image is not None:
        image.label_status = "gold"
    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", "spd_manager"),
        action_type="image_label_adjudicated",
        resource_type="image_label",
        resource_id=str(label.id),
    )
    return {"id": label.id, "is_gold": True, "adjudicated": True}


@router.get("/dataset/export")
def export_dataset(
    request: Request,
    gold_only: bool = True,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Export a training-dataset manifest (metadata + labels, no bytes inline).

    ``gold_only`` (default) restricts to adjudicated labels — only ``gold`` data
    should enter validation/test sets per the dataset plan. Bytes are fetched
    separately via ``/ml/images/{id}/bytes`` so the manifest stays lightweight.
    """
    tenant_id = get_request_tenant_id(request)
    images = (
        db.query(RetainedImage)
        .filter(RetainedImage.tenant_id == tenant_id)
        .order_by(RetainedImage.id)
        .all()
    )
    records = []
    class_counts: dict[str, int] = {}
    for img in images:
        q = db.query(ImageLabel).filter(
            ImageLabel.image_id == img.id, ImageLabel.tenant_id == tenant_id
        )
        if gold_only:
            q = q.filter(ImageLabel.is_gold.is_(True))
        labels = q.all()
        if gold_only and not labels:
            continue
        for lb in labels:
            if lb.present:
                class_counts[lb.finding_type] = class_counts.get(lb.finding_type, 0) + 1
        records.append({
            "image_id": img.id,
            "deident_name": img.deident_name,
            "instrument_type": img.instrument_type,
            "sha256": img.sha256,
            "bytes_url": f"/api/ml/images/{img.id}/bytes",
            "source": img.source,
            "labels": [
                {
                    "finding_type": lb.finding_type,
                    "present": lb.present,
                    "severity": lb.severity,
                    "region": json.loads(lb.region_json) if lb.region_json else None,
                    "is_gold": lb.is_gold,
                }
                for lb in labels
            ],
        })
    return {
        "tenant_id": tenant_id,
        "gold_only": gold_only,
        "image_count": len(records),
        "class_counts": class_counts,
        "records": records,
        "note": (
            "Advisory training tooling. Only gold (adjudicated) labels should "
            "enter validation/test sets. No diagnostic-accuracy or FDA claims."
        ),
    }
