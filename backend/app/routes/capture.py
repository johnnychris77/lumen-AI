"""Direct borescope-to-LumenAI capture ingestion.

Two auth models feed the same pipeline:
  - Browser capture client (tablet/PC with a UVC grabber): uses the logged-in
    user's token via the existing /api/inspections/* endpoints.
  - Unattended "LumenAI Bridge" appliance: authenticates with a device key
    (X-Device-Key) and POSTs frames to /api/capture/ingest — no human login,
    no USB drive.

Everything is EXIF-stripped, identifier-decoded, scored, and audit-logged, so a
captured frame becomes an inspection the instant the tech presses capture.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.cv.identifier_decoder import decode_from_image_bytes
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.capture_device import CaptureDevice
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.image_retention_service import retain_image

router = APIRouter(prefix="/capture", tags=["capture"])

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_ASSIGNABLE_DEVICE_ROLES = {"operator", "spd_manager"}


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


# ── Device registration (admin) ──────────────────────────────────────────────

class DeviceRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field("", max_length=255)
    role: str = Field("operator", max_length=50)


@router.post("/devices", status_code=201)
def register_device(
    body: DeviceRegister,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Register a capture device and return its key ONCE (never retrievable again)."""
    if body.role not in _ASSIGNABLE_DEVICE_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"role must be one of {sorted(_ASSIGNABLE_DEVICE_ROLES)}",
        )
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)

    raw_key = secrets.token_urlsafe(40)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    device = CaptureDevice(
        tenant_id=tenant_id,
        name=body.name,
        location=body.location,
        key_hash=key_hash,
        role=body.role,
        active=True,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id,
        actor_email=_actor(current_user), actor_role=getattr(current_user, "role", "admin"),
        action_type="capture_device_registered", resource_type="capture_device",
        resource_id=str(device.id),
    )
    return {
        "id": device.id,
        "name": device.name,
        "location": device.location,
        "role": device.role,
        # Shown ONCE — store it on the device now; it can never be retrieved again.
        "device_key": raw_key,
        "note": "Store this key on the capture device now. It is not recoverable.",
    }


@router.get("/devices")
def list_devices(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    rows = (
        db.query(CaptureDevice)
        .filter(CaptureDevice.tenant_id == tenant_id)
        .order_by(CaptureDevice.id.desc())
        .all()
    )
    return {
        "count": len(rows),
        "devices": [
            {
                "id": r.id, "name": r.name, "location": r.location, "role": r.role,
                "active": r.active,
                "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.post("/devices/{device_id}/revoke")
def revoke_device(
    device_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    device = (
        db.query(CaptureDevice)
        .filter(CaptureDevice.id == device_id, CaptureDevice.tenant_id == tenant_id)
        .first()
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Capture device not found.")
    device.active = False
    db.commit()
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id,
        actor_email=_actor(current_user), actor_role=getattr(current_user, "role", "admin"),
        action_type="capture_device_revoked", resource_type="capture_device",
        resource_id=str(device.id),
    )
    return {"id": device.id, "active": False}


# ── Device authentication ─────────────────────────────────────────────────────

def authenticate_device(db: Session, device_key: Optional[str]) -> CaptureDevice:
    """Resolve an active CaptureDevice from a plaintext X-Device-Key header."""
    if not device_key:
        raise HTTPException(status_code=401, detail="Missing X-Device-Key.")
    key_hash = hashlib.sha256(device_key.encode()).hexdigest()
    device = (
        db.query(CaptureDevice)
        .filter(CaptureDevice.key_hash == key_hash, CaptureDevice.active.is_(True))
        .first()
    )
    if device is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked device key.")
    return device


# ── Ingestion (unattended appliance) ──────────────────────────────────────────

@router.post("/ingest", status_code=201)
async def ingest_capture(
    image: UploadFile = File(...),
    instrument_type: str = Form("unknown"),
    instrument_barcode: str = Form(""),
    instrument_udi: str = Form(""),
    facility_name: str = Form(""),
    captured_by: str = Form(""),
    consent: bool = Form(False),
    x_device_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    """Ingest a borescope frame from an authenticated capture device.

    Decodes identifiers, optionally retains the EXIF-stripped image, scores it
    against the approved baseline, and persists the inspection — the same
    pipeline as a manual New Inspection, but triggered by the device.
    """
    device = authenticate_device(db, x_device_key)
    tenant_id = device.tenant_id

    content_type = image.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported type '{content_type}'. Allowed: {sorted(_ALLOWED_TYPES)}",
        )
    data = await image.read()
    if len(data) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MB limit.")

    sha256 = hashlib.sha256(data).hexdigest()

    # Real identifier decode from the frame; declared values win if provided.
    decoded = decode_from_image_bytes(data)
    barcode = instrument_barcode or decoded.barcode_value
    udi = instrument_udi or decoded.qr_value or decoded.udi_value
    identifier_source = "pyzbar" if (not instrument_barcode and not instrument_udi and (decoded.barcode_value or decoded.qr_value or decoded.udi_value)) else "declared"

    # Opt-in retention (no-op unless enabled + consent).
    retain_image(
        db, data=data, tenant_id=tenant_id, instrument_type=instrument_type,
        content_type=content_type, source="capture_device",
        uploaded_by=f"device:{device.id}", consent=consent,
    )

    analysis = analyze_inspection(
        db, instrument_type=instrument_type, tenant_id=tenant_id, has_image=True,
        image_sha256=sha256, instrument_barcode=barcode or None,
        instrument_udi=udi or None, decoder_backend=identifier_source,
    )

    completed = analysis["analysis_status"] == "completed"
    row = models.Inspection(
        file_name=image.filename or "capture.jpg",
        tenant_id=tenant_id, tenant_name=tenant_id,
        instrument_type=instrument_type,
        inference_mode="borescope_capture",
        risk_score=(100 - int(analysis["inspection_score"])) if completed else 0,
        vendor_name="unknown", site_name=facility_name or "capture",
        facility_name=facility_name or None,
        instrument_barcode=barcode or None, instrument_udi=udi or None,
        inference_timestamp=datetime.now(timezone.utc),
        has_image=True, image_sha256=sha256,
        baseline_status="approved_baseline_found" if completed else "no_approved_baseline",
        baseline_source=analysis.get("baseline_source"),
        score_status="scored" if completed else "supervisor_review_required",
        supervisor_review_required=not completed,
        risk_level=analysis.get("risk_level"),
        recommended_action=analysis.get("recommended_action"),
        overall_cleaning_assessment=analysis.get("overall_cleaning_assessment"),
    )
    db.add(row)
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)

    # Attribute to the scanning tech when the station provides a badge/PIN,
    # otherwise to the device itself.
    actor = captured_by.strip() or f"device:{device.id}"
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id,
        actor_email=actor, actor_role=device.role,
        action_type="capture_ingested", resource_type="inspection",
        resource_id=str(row.id),
    )
    return {
        "inspection_id": row.id,
        "device_id": device.id,
        "captured_by": captured_by.strip(),
        "analysis": analysis,
    }
