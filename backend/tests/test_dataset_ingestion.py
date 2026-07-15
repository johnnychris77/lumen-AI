"""Project Canvas — Sections 2 & 4: Image Ingestion API smoke tests.

Exercises the new `/api/dataset-ingestion/*` routes end-to-end through the
real auth/role surface, backed by the existing `retain_image` +
`dataset_registry.register_image` services (no duplicated storage/validation
logic).
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.ml import dataset_registry
from app.db.session import SessionLocal

client = TestClient(app)

AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
TENANT = "default-tenant"


def _png_bytes(seed=0):
    img = Image.new("RGB", (16, 16), (seed % 255, 10, 10))
    px = img.load()
    px[0, 0] = (seed % 255, 20, 30)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _make_version(label: str) -> int:
    db = SessionLocal()
    try:
        version = dataset_registry.create_dataset_version(db, tenant_id=TENANT, version_label=label)
        return version.id
    finally:
        db.close()


def _valid_form(version_id: int, **overrides):
    base = dict(
        consent="true",
        dataset_version_id=str(version_id),
        usage_rights="internal_use_approved",
        instrument_family="scissors",
        manufacturer="Acme",
        facility="Test Hospital",
        operator="tech1",
        capture_device="phone",
        image_resolution="16x16",
        image_type="after_use",
    )
    base.update(overrides)
    return base


def test_ingest_single_image_success(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    version_id = _make_version("canvas-ingest-v1")
    r = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("scope1.png", _png_bytes(1), "image/png")},
        data=_valid_form(version_id),
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["duplicate"] is False
    assert body["entry"]["lcid"]
    assert body["entry"]["image_type"] == "after_use"


def test_ingest_duplicate_returns_warning_not_error(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    version_id = _make_version("canvas-ingest-v2")
    data = _png_bytes(2)
    first = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("scope2.png", data, "image/png")},
        data=_valid_form(version_id),
        headers=AUTH_OPERATOR,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("scope2-again.png", data, "image/png")},
        data=_valid_form(version_id),
        headers=AUTH_OPERATOR,
    )
    assert second.status_code == 201
    assert second.json()["duplicate"] is True
    assert "existing_entry" in second.json()


def test_ingest_missing_metadata_rejected(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    version_id = _make_version("canvas-ingest-v3")
    r = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("scope3.png", _png_bytes(3), "image/png")},
        data=_valid_form(version_id, manufacturer="", facility=""),
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 422
    assert "missing_fields" in r.json()["detail"]


def test_ingest_missing_usage_rights_rejected(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    version_id = _make_version("canvas-ingest-v4")
    r = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("scope4.png", _png_bytes(4), "image/png")},
        data=_valid_form(version_id, usage_rights=""),
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 422


def test_ingest_unsupported_type_rejected(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    version_id = _make_version("canvas-ingest-v5")
    r = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("scope5.txt", b"not an image", "text/plain")},
        data=_valid_form(version_id),
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 422


def test_ingest_blocked_when_retention_disabled(monkeypatch):
    monkeypatch.delenv("RETAIN_INSPECTION_IMAGES", raising=False)
    version_id = _make_version("canvas-ingest-v6")
    r = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("scope6.png", _png_bytes(6), "image/png")},
        data=_valid_form(version_id),
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 409


def test_viewer_cannot_ingest(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    version_id = _make_version("canvas-ingest-v7")
    r = client.post(
        "/api/dataset-ingestion/images",
        files={"image": ("scope7.png", _png_bytes(7), "image/png")},
        data=_valid_form(version_id),
        headers=AUTH_VIEWER,
    )
    assert r.status_code == 403


def test_bulk_ingest_partial_success(monkeypatch):
    monkeypatch.setenv("RETAIN_INSPECTION_IMAGES", "true")
    version_id = _make_version("canvas-ingest-bulk-v1")
    shared = _valid_form(version_id)
    shared.pop("dataset_version_id")
    shared.pop("consent")
    import json as _json

    r = client.post(
        "/api/dataset-ingestion/images/bulk",
        files=[
            ("images", ("bulk-ok.png", _png_bytes(10), "image/png")),
            ("images", ("bulk-bad.png", b"", "image/png")),
        ],
        data={
            "consent": "true",
            "dataset_version_id": str(version_id),
            "shared_metadata": _json.dumps(shared),
        },
        headers=AUTH_OPERATOR,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["success_count"] == 1
    assert body["error_count"] == 1
    rows_by_name = {row["filename"]: row for row in body["rows"]}
    assert rows_by_name["bulk-ok.png"]["success"] is True
    assert rows_by_name["bulk-bad.png"]["success"] is False
