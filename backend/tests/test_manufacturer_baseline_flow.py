"""End-to-end: create an approved manufacturer baseline, then an inspection of
the same instrument type must produce a score + KPIs (not supervisor review).

This pins the working path the UI depends on after the baseline systems were
found disconnected and approval was blocked by role mismatches.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}       # admin
AUTH_MGR = {"Authorization": "Bearer manager-token"}      # spd_manager
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}    # viewer
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}  # operator (runs inspections)
SHA = "c0ffee00" + "0" * 56


def _clear(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype,
        ).delete()
        db.commit()
    finally:
        db.close()


class TestManufacturerBaselineCreation:
    def test_admin_can_create_approved_baseline(self):
        itype = "forceps"
        _clear(itype)
        resp = client.post("/api/baselines/manufacturer", json={
            "instrument_type": itype,
            "manufacturer_name": "Acme Surgical",
            "model_name": "AS-100",
            "image_sha256": SHA,
        }, headers=AUTH_ADMIN)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["approval_status"] == "approved"
        assert data["instrument_type"] == itype
        assert data["baseline_type"] == "manufacturer"

    def test_spd_manager_can_create(self):
        _clear("scissors")
        resp = client.post("/api/baselines/manufacturer", json={
            "instrument_type": "scissors",
            "manufacturer_name": "Acme",
        }, headers=AUTH_MGR)
        assert resp.status_code == 201, resp.text

    def test_viewer_cannot_create(self):
        resp = client.post("/api/baselines/manufacturer", json={
            "instrument_type": "scissors",
            "manufacturer_name": "Acme",
        }, headers=AUTH_VIEWER)
        assert resp.status_code == 403

    def test_invalid_instrument_type_rejected(self):
        resp = client.post("/api/baselines/manufacturer", json={
            "instrument_type": "not_a_real_type",
            "manufacturer_name": "Acme",
        }, headers=AUTH_ADMIN)
        assert resp.status_code == 422


class TestEndToEndScoring:
    def test_baseline_then_inspection_produces_score(self):
        itype = "needle_holder"
        _clear(itype)

        # 1. Create approved manufacturer baseline
        b = client.post("/api/baselines/manufacturer", json={
            "instrument_type": itype,
            "manufacturer_name": "Acme",
            "model_name": "NH-1",
            "image_sha256": SHA,
        }, headers=AUTH_ADMIN)
        assert b.status_code == 201, b.text

        # 2. Run an inspection on the same instrument type (operator runs inspections)
        ins = client.post("/api/inspections", json={
            "instrument_type": itype,
            "site_name": "Test Hospital",
            "has_image": True,
            "image_sha256": SHA,
            "file_name": "img.jpg",
        }, headers=AUTH_OPERATOR)
        assert ins.status_code == 201, ins.text
        analysis = ins.json()["analysis"]

        # 3. Scoring must complete with a real score + KPIs (not supervisor review)
        assert analysis["analysis_status"] == "completed"
        assert analysis["baseline_source"] == "manufacturer"
        assert analysis["inspection_score"] is not None
        assert 0 <= analysis["inspection_score"] <= 100
        assert analysis["risk_level"] in ("low", "medium", "high", "critical")
        assert "blood" in analysis["kpi_summary"]
        assert "rust" in analysis["kpi_summary"]
