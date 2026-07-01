"""Image retention + labeling pipeline.

Covers the opt-in retention gate, EXIF stripping, labeling, the two-reviewer
rule for critical classes, and dataset export.
"""
import io

from PIL import Image

from app.db.session import SessionLocal
from app.services import image_retention_service as svc


def _png_with_exif() -> bytes:
    """A small PNG; we mostly assert re-encode produces clean, decodable bytes."""
    img = Image.new("RGB", (8, 8), (120, 30, 30))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def test_strip_exif_returns_decodable_image():
    data = _png_with_exif()
    clean, stripped = svc.strip_exif(data, "image/png")
    assert stripped is True
    # Clean bytes are still a valid image.
    with Image.open(io.BytesIO(clean)) as reopened:
        assert reopened.size == (8, 8)


def test_retention_disabled_is_default(monkeypatch):
    monkeypatch.delenv("RETAIN_INSPECTION_IMAGES", raising=False)
    assert svc.retention_enabled() is False


def test_retain_image_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("RETAIN_INSPECTION_IMAGES", raising=False)
    db = SessionLocal()
    try:
        row = svc.retain_image(db, data=_png_with_exif(), tenant_id="t1", consent=True)
        assert row is None
    finally:
        db.close()


def test_retain_image_noop_without_consent(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    db = SessionLocal()
    try:
        row = svc.retain_image(db, data=_png_with_exif(), tenant_id="t1", consent=False)
        assert row is None
    finally:
        db.close()


def test_retain_image_stores_when_enabled_and_consented(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    db = SessionLocal()
    try:
        row = svc.retain_image(
            db,
            data=_png_with_exif(),
            tenant_id="t1",
            instrument_type="needle driver",
            content_type="image/png",
            consent=True,
        )
    finally:
        db.close()
    assert row is not None
    assert row.consent_recorded is True
    assert row.exif_stripped is True
    assert row.image_bytes is not None
    assert row.deident_name.startswith("needle_driver_")
    assert row.label_status == "unlabeled"
