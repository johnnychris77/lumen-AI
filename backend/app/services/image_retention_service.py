"""Opt-in image retention for model training.

Retention is a deliberate, access-controlled capability — NOT a default. The
platform normally stores only SHA-256 hashes. This service persists actual image
bytes ONLY when:

  1. ``RETAIN_INSPECTION_IMAGES`` is enabled (env), AND
  2. consent is recorded for the action.

Before any bytes are stored, EXIF/metadata is stripped (no GPS, device, or
embedded thumbnails) to avoid PHI/identifying metadata. Images must be of
instruments only — callers are responsible for rejecting frames containing PHI.
"""
from __future__ import annotations

import hashlib
import io
import os

from sqlalchemy.orm import Session

from app.models.retained_image import RetainedImage

_TRUTHY = {"1", "true", "yes", "on", "enabled"}


def retention_enabled() -> bool:
    """Whether opt-in image retention is turned on for this deployment."""
    return os.getenv("RETAIN_INSPECTION_IMAGES", "").strip().lower() in _TRUTHY


def strip_exif(data: bytes, content_type: str = "") -> tuple[bytes, bool]:
    """Return (clean_bytes, stripped). Re-encodes the image WITHOUT EXIF/metadata.

    Degrades gracefully: if Pillow is unavailable or the bytes are not a
    decodable image, returns the original bytes with ``stripped=False`` so the
    caller can decide. We never want metadata stripping to crash an upload.
    """
    try:
        from PIL import Image  # local import — optional/heavy dependency
    except Exception:
        return data, False

    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format or _format_from_content_type(content_type)
            # Re-create the image from pixel data only — drops EXIF, GPS, ICC, etc.
            clean = Image.new(img.mode, img.size)
            clean.paste(img)
            out = io.BytesIO()
            save_fmt = fmt if fmt in {"JPEG", "PNG", "WEBP", "BMP"} else "PNG"
            clean.save(out, format=save_fmt)
            return out.getvalue(), True
    except Exception:
        return data, False


_PIL_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "BMP": "image/bmp",
    "TIFF": "image/tiff", "GIF": "image/gif",
}


def _detect_content_type(data: bytes, fallback: str = "") -> str:
    """Return the real MIME type of the encoded bytes (what they actually are
    now, after any re-encode), falling back to the provided type if undetectable."""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as img:
            return _PIL_FORMAT_TO_MIME.get((img.format or "").upper(), fallback)
    except Exception:
        return fallback


def _format_from_content_type(content_type: str) -> str:
    ct = (content_type or "").lower()
    if "jpeg" in ct or "jpg" in ct:
        return "JPEG"
    if "png" in ct:
        return "PNG"
    if "webp" in ct:
        return "WEBP"
    return "PNG"


def retain_image(
    db: Session,
    *,
    data: bytes,
    tenant_id: str,
    instrument_type: str = "unknown",
    content_type: str = "",
    source: str = "inspection",
    uploaded_by: str = "",
    consent: bool = False,
    seq: int | None = None,
) -> RetainedImage | None:
    """Persist an EXIF-stripped image IF retention is enabled and consent given.

    Returns the created ``RetainedImage`` row, or ``None`` when retention is
    disabled or consent is absent (the no-op default path).
    """
    if not retention_enabled() or not consent:
        return None

    clean_bytes, stripped = strip_exif(data, content_type)
    sha256 = hashlib.sha256(clean_bytes).hexdigest()

    # Upload retries (same bytes re-submitted) must not create a duplicate
    # retained-image record for the same tenant.
    existing = (
        db.query(RetainedImage)
        .filter(RetainedImage.tenant_id == tenant_id, RetainedImage.sha256 == sha256)
        .first()
    )
    if existing is not None:
        existing._lumenai_dedup_hit = True
        return existing

    if seq is None:
        seq = (
            db.query(RetainedImage)
            .filter(RetainedImage.tenant_id == tenant_id)
            .count()
            + 1
        )
    deident_name = f"{(instrument_type or 'unknown').replace(' ', '_')}_{seq}"

    row = RetainedImage(
        tenant_id=tenant_id,
        deident_name=deident_name,
        instrument_type=instrument_type or "unknown",
        content_type=content_type,
        size_bytes=len(clean_bytes),
        sha256=sha256,
        exif_stripped=stripped,
        source=source,
        consent_recorded=True,
        uploaded_by=uploaded_by,
        image_bytes=clean_bytes,
        label_status="unlabeled",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def retain_reference_image(
    db: Session,
    *,
    data: bytes,
    tenant_id: str,
    instrument_type: str = "unknown",
    content_type: str = "",
    uploaded_by: str = "",
    usage_rights_attested: bool,
) -> RetainedImage:
    """Persist a GOVERNED baseline *reference* image's bytes.

    Distinct from ``retain_image``: a manufacturer/organization baseline
    reference photograph is reference evidence the organization asserts it has
    the rights to store, NOT a patient-derived inspection frame retained for
    training. It is therefore governed by an explicit usage-rights attestation
    on upload rather than the ``RETAIN_INSPECTION_IMAGES`` training-retention
    flag — without stored bytes no real comparison is ever possible, so this is
    the one honest way to make an uploaded baseline image genuinely usable.

    Reuses the same RetainedImage store (no duplicate storage), the same EXIF
    strip, and the same per-tenant dedup. Raises when rights are not attested;
    never fabricates or reconstructs bytes.
    """
    if not usage_rights_attested:
        raise PermissionError(
            "A baseline reference image can only be stored when the uploader attests usage rights for it."
        )
    if not data:
        raise ValueError("No image bytes provided for the baseline reference image.")

    clean_bytes, stripped = strip_exif(data, content_type)
    sha256 = hashlib.sha256(clean_bytes).hexdigest()
    # strip_exif may re-encode to a different format (e.g. TIFF -> PNG), so the
    # stored content type must describe the ACTUAL retained bytes — a download
    # endpoint serves them under this media type.
    effective_content_type = _detect_content_type(clean_bytes, fallback=content_type) if stripped else content_type

    existing = (
        db.query(RetainedImage)
        .filter(RetainedImage.tenant_id == tenant_id, RetainedImage.sha256 == sha256)
        .first()
    )
    if existing is not None:
        existing._lumenai_dedup_hit = True
        return existing

    seq = (
        db.query(RetainedImage).filter(RetainedImage.tenant_id == tenant_id).count() + 1
    )
    row = RetainedImage(
        tenant_id=tenant_id,
        deident_name=f"baseline_{(instrument_type or 'unknown').replace(' ', '_')}_{seq}",
        instrument_type=instrument_type or "unknown",
        content_type=effective_content_type,
        size_bytes=len(clean_bytes),
        sha256=sha256,
        exif_stripped=stripped,
        source="baseline_reference",
        consent_recorded=True,
        uploaded_by=uploaded_by,
        image_bytes=clean_bytes,
        label_status="unlabeled",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
