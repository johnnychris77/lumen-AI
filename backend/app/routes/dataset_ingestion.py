"""Project Canvas — Sections 2 & 4: Image Ingestion REST surface.

Thin HTTP layer over `app.services.dataset_ingestion_service`. Mirrors the
accepted-type/size policy and multipart conventions already established by
`app.routes.ml_images` — this is not a second upload policy, just the
dataset-registration-aware wrapper around the same rules.
"""
from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.annotation_database import ROLES_MAY_ANNOTATE
from app.services import dataset_ingestion_service
from app.services.enterprise_audit_service import record_enterprise_audit_event
from app.services.ml import dataset_registry

router = APIRouter(tags=["dataset-ingestion"])

_INGEST_ROLES = tuple(ROLES_MAY_ANNOTATE)


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _handle_ingestion_error(exc: Exception) -> HTTPException:
    if isinstance(exc, dataset_ingestion_service.IngestionDisabledError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, dataset_ingestion_service.EmptyFileError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, dataset_ingestion_service.UnsupportedFileTypeError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, dataset_ingestion_service.FileTooLargeError):
        return HTTPException(status_code=413, detail=str(exc))
    if isinstance(exc, dataset_ingestion_service.ConsentRequiredError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, dataset_ingestion_service.UsageRightsRequiredError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, dataset_registry.DatasetVersionNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, dataset_registry.DatasetVersionFrozenError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, dataset_registry.MetadataValidationError):
        return HTTPException(status_code=422, detail={"message": str(exc), "missing_fields": exc.missing_fields})
    if isinstance(exc, dataset_registry.DuplicateImageError):
        return HTTPException(status_code=409, detail=str(exc))
    raise exc


def _entry_view(row) -> dict:
    return {
        "id": row.id, "lcid": row.lcid, "digital_twin_id": row.digital_twin_id, "baseline_id": row.baseline_id,
        "dataset_version_id": row.dataset_version_id, "instrument_family": row.instrument_family,
        "instrument_model": row.instrument_model, "manufacturer": row.manufacturer,
        "instrument_id": row.instrument_id, "catalog_number": row.catalog_number,
        "anatomy_zone": row.anatomy_zone, "inspection_region": row.inspection_region,
        "image_type": row.image_type, "image_quality": row.image_quality,
        "review_status": row.review_status, "usage_rights": row.usage_rights,
        "phi_verification": row.phi_verification, "reviewer_notes": row.reviewer_notes,
    }


@router.post("/dataset-ingestion/images", status_code=201)
async def ingest_single_image(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_INGEST_ROLES)),
    image: UploadFile = File(...),
    consent: bool = Form(False),
    dataset_version_id: int = Form(...),
    usage_rights: str = Form(""),
    instrument_id: str = Form(""),
    instrument_family: str = Form(""),
    instrument_model: str = Form(""),
    manufacturer: str = Form(""),
    catalog_number: str = Form(""),
    anatomy_zone: str = Form(""),
    inspection_region: str = Form(""),
    capture_device: str = Form(""),
    image_resolution: str = Form(""),
    facility: str = Form(""),
    operator: str = Form(""),
    image_type: str = Form(""),
    image_quality: str = Form(""),
    phi_verification: str = Form("pending"),
    digital_twin_id: str = Form(""),
    reviewer_notes: str = Form(""),
    instrument_barcode: str = Form(""),
    instrument_udi: str = Form(""),
):
    """Section 2/3 — single-image upload plus the minimum registration form.
    Returns a clear duplicate-warning response (HTTP 200) distinct from a
    hard validation error (4xx) — never a silent overwrite."""
    tenant_id = _tenant(current_user, request)
    content_type = image.content_type or ""
    data = await image.read()

    try:
        outcome = dataset_ingestion_service.ingest_image(
            db, tenant_id=tenant_id, data=data, content_type=content_type,
            actor=_actor(current_user), consent=consent, dataset_version_id=dataset_version_id,
            usage_rights=usage_rights, instrument_id=instrument_id, instrument_family=instrument_family,
            instrument_model=instrument_model, manufacturer=manufacturer, catalog_number=catalog_number,
            anatomy_zone=anatomy_zone, inspection_region=inspection_region, capture_device=capture_device,
            image_resolution=image_resolution, facility=facility, operator=operator, image_type=image_type,
            image_quality=image_quality, phi_verification=phi_verification, digital_twin_id=digital_twin_id,
            reviewer_notes=reviewer_notes, instrument_barcode=instrument_barcode, instrument_udi=instrument_udi,
        )
    except Exception as exc:  # noqa: BLE001 - narrowed by _handle_ingestion_error, re-raised if unrecognized
        raise _handle_ingestion_error(exc) from exc

    if outcome["duplicate"]:
        existing = outcome["existing_entry"]
        return {
            "duplicate": True,
            "message": f"This image is already registered as dataset entry {existing.id} (LCID {existing.lcid}).",
            "existing_entry": _entry_view(existing),
        }

    entry = outcome["entry"]
    record_enterprise_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
        actor_role=getattr(current_user, "role", ""), action_type="dataset_image_registered",
        resource_type="dataset_entry", resource_id=entry.id,
    )
    return {"duplicate": False, "entry": _entry_view(entry)}


@router.post("/dataset-ingestion/images/bulk", status_code=201)
async def ingest_bulk_images(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_INGEST_ROLES)),
    images: List[UploadFile] = File(...),
    consent: bool = Form(False),
    dataset_version_id: int = Form(...),
    shared_metadata: str = Form("{}"),
    csv_metadata: UploadFile | None = File(None),
):
    """Section 4 — bulk ingestion. `shared_metadata` is a JSON object applied
    to every file; an optional `csv_metadata` file supplies per-filename
    overrides (Section 4's CSV metadata import). Partial success is
    reported row-by-row — one bad file never fails the whole batch."""
    tenant_id = _tenant(current_user, request)
    try:
        shared = json.loads(shared_metadata) if shared_metadata else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"shared_metadata is not valid JSON: {exc}") from exc

    per_file_overrides: dict[str, dict] = {}
    if csv_metadata is not None:
        csv_bytes = await csv_metadata.read()
        per_file_overrides = dataset_ingestion_service.parse_csv_metadata(csv_bytes.decode("utf-8", errors="replace"))

    files = []
    for img in images:
        data = await img.read()
        files.append({
            "filename": img.filename or "unknown",
            "data": data,
            "content_type": img.content_type or "",
            "metadata": per_file_overrides.get(img.filename or "", {}),
        })

    result = dataset_ingestion_service.bulk_ingest(
        db, tenant_id=tenant_id, actor=_actor(current_user), consent=consent,
        dataset_version_id=dataset_version_id, files=files, shared_metadata=shared,
    )

    if result.success_count:
        record_enterprise_audit_event(
            db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user),
            actor_role=getattr(current_user, "role", ""), action_type="dataset_bulk_ingested",
            resource_type="dataset_version", resource_id=dataset_version_id,
            details={"success_count": result.success_count, "error_count": result.error_count,
                     "duplicate_count": result.duplicate_count},
        )

    return {
        "success_count": result.success_count,
        "error_count": result.error_count,
        "duplicate_count": result.duplicate_count,
        "rows": [
            {
                "filename": r.filename, "success": r.success, "duplicate": r.duplicate,
                "error": r.error, "lcid": r.lcid, "entry_id": r.entry_id,
            }
            for r in result.rows
        ],
    }
