"""Bounded, tenant-scoped temporary store for inspection pixels used to run the
comparison the user requested — decoupled from opt-in training retention.

Lifecycle:  store (on upload)  ->  load+verify (at analysis)  ->  consume (null
the bytes once used)  ->  purge (expired rows reclaimed).

Guarantees:
  * EXIF-stripped before storage (no GPS/device metadata).
  * Strict tenant scope on every read (cross-tenant access impossible).
  * Hash-verified on load — bytes that no longer match their registered identity
    are never returned.
  * Bytes are nulled the moment they are consumed, and expired rows are deleted.
  * Nothing in the training/dataset pipeline reads this table, so a processing
    image is NEVER enrolled in a training dataset.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection_processing_image import InspectionProcessingImage
from app.services.image_retention_service import _detect_content_type, strip_exif

# How long an uploaded-but-unprocessed inspection image stays available. Short:
# it only needs to survive from the upload call to the inspection-create call.
PROCESSING_TTL_MINUTES = 60

STATUS_PENDING = "pending"
STATUS_CONSUMED = "consumed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    """Treat a naive datetime (SQLite drops tzinfo on round-trip) as UTC so it
    can be compared against timezone-aware ``_now()``."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def purge_expired(db: Session) -> int:
    """Delete every processing image past its expiry (consumed or not). Returns
    the number removed. Cheap and safe to call opportunistically."""
    now = _now()
    expired = [
        row for row in db.query(InspectionProcessingImage).all()
        if _as_aware(row.expires_at) is not None and _as_aware(row.expires_at) < now
    ]
    for row in expired:
        db.delete(row)
    if expired:
        db.commit()
    return len(expired)


def store_processing_image(
    db: Session,
    *,
    tenant_id: str,
    data: bytes,
    content_type: str = "",
    uploaded_by: str = "",
    ttl_minutes: int = PROCESSING_TTL_MINUTES,
) -> InspectionProcessingImage:
    """Persist EXIF-stripped inspection pixels for near-term processing only.

    This is NOT training retention: it is governed by the inspection request
    itself (the user uploaded the image to be inspected), bounded by ``ttl``, and
    never read by the training pipeline. A re-upload of the same bytes for the
    same tenant refreshes the existing pending row rather than duplicating it."""
    if not data:
        raise ValueError("No image bytes provided for processing.")

    purge_expired(db)

    # Key on the ORIGINAL file's hash — that is what the client submits as the
    # inspection's image_sha256. Store the EXIF-stripped bytes, with their own
    # hash recorded separately for integrity verification on load.
    original_sha = hashlib.sha256(data).hexdigest()
    clean_bytes, stripped = strip_exif(data, content_type)
    stored_sha = hashlib.sha256(clean_bytes).hexdigest()
    effective_ct = _detect_content_type(clean_bytes, fallback=content_type) if stripped else content_type
    expires_at = _now() + timedelta(minutes=max(1, ttl_minutes))

    existing = (
        db.query(InspectionProcessingImage)
        .filter(
            InspectionProcessingImage.tenant_id == tenant_id,
            InspectionProcessingImage.image_sha256 == original_sha,
            InspectionProcessingImage.status == STATUS_PENDING,
        )
        .order_by(InspectionProcessingImage.id.desc())
        .first()
    )
    if existing is not None:
        existing.image_bytes = clean_bytes
        existing.stored_sha256 = stored_sha
        existing.content_type = effective_ct
        existing.size_bytes = len(clean_bytes)
        existing.expires_at = expires_at
        db.commit()
        db.refresh(existing)
        return existing

    row = InspectionProcessingImage(
        tenant_id=tenant_id, image_sha256=original_sha, stored_sha256=stored_sha,
        content_type=effective_ct, size_bytes=len(clean_bytes), image_bytes=clean_bytes,
        uploaded_by=uploaded_by, status=STATUS_PENDING, expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def load_processing_bytes(
    db: Session, *, tenant_id: str, image_sha256: str,
) -> tuple[bytes | None, InspectionProcessingImage | None]:
    """Return (bytes, row) for a tenant's pending, non-expired, hash-verified
    processing image, or (None, None). Strictly tenant-scoped — a different
    tenant's bytes can never be returned."""
    if not image_sha256:
        return None, None
    row = (
        db.query(InspectionProcessingImage)
        .filter(
            InspectionProcessingImage.tenant_id == tenant_id,
            InspectionProcessingImage.image_sha256 == image_sha256,
            InspectionProcessingImage.status == STATUS_PENDING,
        )
        .order_by(InspectionProcessingImage.id.desc())
        .first()
    )
    if row is None or row.image_bytes is None:
        return None, None
    if _as_aware(row.expires_at) < _now():
        return None, None
    # Integrity: the stored (EXIF-stripped) bytes must still hash to the
    # identity recorded at store time — never return mismatched/corrupted bytes.
    recomputed = hashlib.sha256(row.image_bytes).hexdigest()
    if recomputed != (row.stored_sha256 or row.image_sha256):
        return None, None
    return row.image_bytes, row


def consume_processing_image(
    db: Session, *, row: InspectionProcessingImage, inspection_id: int | None = None,
) -> None:
    """Mark a processing image consumed and NULL its bytes — the temporary copy
    is removed the moment processing finishes."""
    if row is None:
        return
    row.status = STATUS_CONSUMED
    row.consumed_at = _now()
    row.image_bytes = None
    if inspection_id is not None:
        row.inspection_id = inspection_id
    db.commit()
