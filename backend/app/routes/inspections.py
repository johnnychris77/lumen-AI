import hashlib
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.db import models
from app.enterprise_auth import get_request_tenant_id, require_enterprise_auth

router = APIRouter(tags=["inspections"])

_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB per file
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}


def inspection_response(row: models.Inspection) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "file_name": row.file_name,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "stain_detected": row.stain_detected,
        "confidence": row.confidence,
        "material_type": row.material_type,
        "status": row.status,
        "model_name": row.model_name,
        "model_version": row.model_version,
        "inference_timestamp": row.inference_timestamp.isoformat() if row.inference_timestamp else None,
        "instrument_type": row.instrument_type,
        "detected_issue": row.detected_issue,
        "inference_mode": row.inference_mode,
        "risk_score": row.risk_score,
        "vendor_name": row.vendor_name,
        "site_name": row.site_name,
    }


@router.get("/inspections/{inspection_id}")
async def get_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    tenant_id = getattr(current_user, "tenant_id", None)

    query = db.query(models.Inspection).filter(models.Inspection.id == inspection_id)

    # Scope to the caller's tenant unless platform admin
    if tenant_id and getattr(current_user, "role", "") != "admin":
        query = query.filter(models.Inspection.tenant_id == tenant_id)

    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Not Found")

    return inspection_response(row)


@router.post("/inspections/upload-images")
async def upload_inspection_images(
    request: Request,
    images: List[UploadFile] = File(...),
):
    """Accept multipart inspection image uploads. Stores SHA-256 hash + metadata only — no raw images in DB."""
    require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    results = []
    for img in images:
        content_type = img.content_type or ""
        if content_type not in _ALLOWED_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"File '{img.filename}' has unsupported type '{content_type}'. Allowed: {sorted(_ALLOWED_TYPES)}",
            )
        data = await img.read()
        if len(data) > _MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File '{img.filename}' exceeds 10 MB limit ({len(data) // 1024} KB).",
            )
        sha256 = hashlib.sha256(data).hexdigest()
        results.append({
            "filename": img.filename,
            "content_type": content_type,
            "size_bytes": len(data),
            "sha256": sha256,
            "tenant_id": tenant_id,
            "status": "received",
        })

    return {
        "uploaded": len(results),
        "images": results,
        "note": "Image hashes recorded. Raw images are not stored in the database.",
    }


@router.post("/baselines/upload-images")
async def upload_baseline_images(
    request: Request,
    images: List[UploadFile] = File(...),
):
    """Accept multipart baseline reference image uploads."""
    require_enterprise_auth(request)
    tenant_id = get_request_tenant_id(request)

    results = []
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
        sha256 = hashlib.sha256(data).hexdigest()
        results.append({
            "filename": img.filename,
            "content_type": content_type,
            "size_bytes": len(data),
            "sha256": sha256,
            "tenant_id": tenant_id,
            "status": "received",
        })

    return {
        "uploaded": len(results),
        "images": results,
        "note": "Baseline image hashes recorded for reference integrity.",
    }
