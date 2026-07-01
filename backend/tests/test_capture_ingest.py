"""Borescope capture-device registration + direct ingestion."""
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}


def _png():
    img = Image.new("RGB", (10, 10), (30, 30, 30))
    out = io.BytesIO()
    img.save(out, format="PNG")
    out.seek(0)
    return out


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"cap-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _register_device():
    r = client.post(
        "/api/capture/devices",
        json={"name": "OR-3 Bridge", "location": "SPD Room 3", "role": "operator"},
        headers=AUTH_ADMIN,
    )
    assert r.status_code == 201, r.text
    return r.json()


class TestDeviceRegistration:
    def test_register_returns_key_once(self):
        d = _register_device()
        assert d["device_key"]
        assert len(d["device_key"]) > 20
        # Listing never returns the key again.
        lst = client.get("/api/capture/devices", headers=AUTH_ADMIN).json()
        assert all("device_key" not in dev for dev in lst["devices"])

    def test_viewer_cannot_register(self):
        r = client.post(
            "/api/capture/devices",
            json={"name": "x", "role": "operator"},
            headers=AUTH_VIEWER,
        )
        assert r.status_code == 403

    def test_invalid_role_rejected(self):
        r = client.post(
            "/api/capture/devices",
            json={"name": "x", "role": "admin"},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 422


class TestIngest:
    def test_ingest_requires_device_key(self):
        r = client.post(
            "/api/capture/ingest",
            files={"image": ("f.png", _png(), "image/png")},
            data={"instrument_type": "scissors"},
        )
        assert r.status_code == 401

    def test_ingest_rejects_bad_key(self):
        r = client.post(
            "/api/capture/ingest",
            files={"image": ("f.png", _png(), "image/png")},
            data={"instrument_type": "scissors"},
            headers={"X-Device-Key": "not-a-real-key"},
        )
        assert r.status_code == 401

    def test_ingest_creates_scored_inspection(self):
        _baseline("scissors")
        key = _register_device()["device_key"]
        r = client.post(
            "/api/capture/ingest",
            files={"image": ("frame.png", _png(), "image/png")},
            data={"instrument_type": "scissors", "facility_name": "Mercy"},
            headers={"X-Device-Key": key},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["inspection_id"]
        assert body["analysis"]["analysis_status"] == "completed"
        assert body["analysis"]["risk_level"] in ("low", "medium", "high", "critical")

    def test_revoked_device_cannot_ingest(self):
        reg = _register_device()
        key, did = reg["device_key"], reg["id"]
        assert client.post(f"/api/capture/devices/{did}/revoke", headers=AUTH_ADMIN).status_code == 200
        r = client.post(
            "/api/capture/ingest",
            files={"image": ("f.png", _png(), "image/png")},
            data={"instrument_type": "scissors"},
            headers={"X-Device-Key": key},
        )
        assert r.status_code == 401
