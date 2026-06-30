"""Inspection role permissions.

  viewer    → read-only; cannot upload, run AI analysis, or submit (clear 403)
  operator  → can upload + run AI analysis + submit; cannot override baseline
  spd_manager / admin → can run + override baseline
"""
import io

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}        # admin
AUTH_MGR = {"Authorization": "Bearer manager-token"}      # spd_manager
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}  # operator
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}    # viewer

SHA = "ab12cd34" + "0" * 56
VIEWER_MSG = "Viewer access is read-only"


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"perm-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _inspection_payload(itype="scissors"):
    return {"instrument_type": itype, "site_name": "H", "has_image": True,
            "image_sha256": SHA, "file_name": "i.jpg"}


def _png_upload():
    return {"images": ("i.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 64), "image/png")}


# ── Viewer: read-only ────────────────────────────────────────────────────────

class TestViewerReadOnly:
    def test_viewer_cannot_submit_inspection(self):
        r = client.post("/api/inspections", json=_inspection_payload(), headers=AUTH_VIEWER)
        assert r.status_code == 403
        assert VIEWER_MSG in r.json()["detail"]

    def test_viewer_cannot_upload_image(self):
        r = client.post("/api/inspections/upload-images", files=_png_upload(), headers=AUTH_VIEWER)
        assert r.status_code == 403
        assert VIEWER_MSG in r.json()["detail"]

    def test_viewer_403_message_is_actionable(self):
        r = client.post("/api/inspections", json=_inspection_payload(), headers=AUTH_VIEWER)
        assert "Operator or SPD Manager" in r.json()["detail"]


# ── Operator: can run, cannot override ───────────────────────────────────────

class TestOperator:
    def test_operator_can_submit_and_get_score(self):
        _baseline("scissors")
        r = client.post("/api/inspections", json=_inspection_payload("scissors"), headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        assert r.json()["analysis"]["analysis_status"] == "completed"

    def test_operator_can_upload_image(self):
        r = client.post("/api/inspections/upload-images", files=_png_upload(), headers=AUTH_OPERATOR)
        assert r.status_code == 200, r.text

    def test_operator_cannot_override_baseline(self):
        # Create an inspection needing review first (no baseline)
        db = SessionLocal()
        try:
            db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == "trocar").delete()
            db.commit()
        finally:
            db.close()
        ins = client.post("/api/inspections", json=_inspection_payload("trocar"), headers=AUTH_OPERATOR)
        iid = ins.json()["id"]
        r = client.post(f"/api/inspections/{iid}/baseline-override",
                        json={"baseline_source": "hospital", "override_reason": "valid reason here"},
                        headers=AUTH_OPERATOR)
        assert r.status_code == 403


# ── SPD manager / admin: can override ────────────────────────────────────────

class TestManagerAdminOverride:
    def _pending_inspection(self) -> int:
        db = SessionLocal()
        try:
            db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == "clip_applier").delete()
            db.commit()
        finally:
            db.close()
        ins = client.post("/api/inspections", json=_inspection_payload("clip_applier"), headers=AUTH_OPERATOR)
        return ins.json()["id"]

    def test_spd_manager_can_override(self):
        iid = self._pending_inspection()
        r = client.post(f"/api/inspections/{iid}/baseline-override",
                        json={"baseline_source": "hospital", "override_reason": "manager reviewed baseline"},
                        headers=AUTH_MGR)
        assert r.status_code == 200, r.text

    def test_admin_can_override(self):
        iid = self._pending_inspection()
        r = client.post(f"/api/inspections/{iid}/baseline-override",
                        json={"baseline_source": "manufacturer", "override_reason": "admin reviewed baseline"},
                        headers=AUTH_ADMIN)
        assert r.status_code == 200, r.text
