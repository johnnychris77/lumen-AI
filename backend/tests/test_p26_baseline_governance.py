"""Phase 14 — Inspection Baseline-Governance Tests."""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}      # admin role
AUTH_MGR = {"Authorization": "Bearer manager-token"}     # spd_manager role
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}   # viewer role (cannot override)
AUTH_TECH = AUTH_VIEWER  # alias: no dedicated technician token; viewer represents restricted role


INSPECTION_WITH_IMAGE = {
    "instrument_type": "scissors",
    "site_name": "Test Hospital",
    "has_image": True,
    "image_sha256": "abc123def456" + "0" * 52,
    "file_name": "scope_image.jpg",
}

INSPECTION_NO_IMAGE = {
    "instrument_type": "scissors",
    "material_type": "stainless_steel",
    "stain_detected": False,
    "detected_issue": "none",
    "site_name": "Test Hospital",
    "has_image": False,
}


def _make_approved_baseline(instrument_type: str = "scissors"):
    db = SessionLocal()
    try:
        entry = BaselineLibraryEntry(
            udi=f"test-udi-{instrument_type}",
            instrument_category=instrument_type,
            manufacturer_name="TestMfg",
            model_name="Model-X",
            baseline_type="manufacturer",
            approval_status="approved",
        )
        db.add(entry)
        db.commit()
        return entry.id
    finally:
        db.close()


def _remove_approved_baselines(instrument_type: str = "scissors"):
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == instrument_type,
            BaselineLibraryEntry.baseline_type == "manufacturer",
            BaselineLibraryEntry.approval_status == "approved",
        ).delete()
        db.commit()
    finally:
        db.close()


class TestInspectionWithImageNoFindings:
    def test_create_inspection_with_image_and_no_findings(self):
        """Inspection can be created with image and no findings (findings optional when has_image=True)."""
        resp = client.post("/api/inspections", json=INSPECTION_WITH_IMAGE, headers=AUTH_TECH)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["has_image"] is True
        assert data["instrument_type"] == "scissors"

    def test_create_inspection_no_image_requires_findings(self):
        """When has_image=False, material_type/detected_issue/stain_detected are required."""
        resp = client.post("/api/inspections", json={
            "instrument_type": "scissors",
            "site_name": "Test Hospital",
            "has_image": False,
        }, headers=AUTH_TECH)
        assert resp.status_code == 422


class TestMissingBaselineSupervisorReview:
    def setup_method(self):
        _remove_approved_baselines("scissors")

    def test_missing_baseline_sets_supervisor_review_required(self):
        """When no approved manufacturer baseline exists, inspection is flagged for supervisor review."""
        resp = client.post("/api/inspections", json=INSPECTION_WITH_IMAGE, headers=AUTH_TECH)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["supervisor_review_required"] is True
        assert data["score_status"] == "supervisor_review_required"
        assert data["baseline_status"] == "no_approved_baseline"
        assert data["risk_score"] == 0

    def test_approved_baseline_scores_normally(self):
        """When approved baseline exists, inspection is scored normally."""
        _make_approved_baseline("scissors")
        try:
            resp = client.post("/api/inspections", json=INSPECTION_WITH_IMAGE, headers=AUTH_TECH)
            assert resp.status_code == 201, resp.text
            data = resp.json()
            assert data["supervisor_review_required"] is False
            assert data["score_status"] == "scored"
            assert data["baseline_status"] == "approved_baseline_found"
        finally:
            _remove_approved_baselines("scissors")


class TestTechnicianCannotOverride:
    def setup_method(self):
        _remove_approved_baselines("scissors")

    def test_technician_cannot_override_baseline(self):
        """spd_technician role cannot apply baseline override (403)."""
        # Create an inspection needing supervisor review
        resp = client.post("/api/inspections", json=INSPECTION_WITH_IMAGE, headers=AUTH_TECH)
        assert resp.status_code == 201, resp.text
        inspection_id = resp.json()["id"]

        override_resp = client.post(
            f"/api/inspections/{inspection_id}/baseline-override",
            json={"baseline_source": "vendor", "override_reason": "Vendor baseline is current and verified."},
            headers=AUTH_TECH,
        )
        assert override_resp.status_code == 403


class TestSupervisorCanOverride:
    def setup_method(self):
        _remove_approved_baselines("scissors")

    def test_supervisor_can_override_with_reason(self):
        """spd_manager can apply baseline override with a valid reason."""
        resp = client.post("/api/inspections", json=INSPECTION_WITH_IMAGE, headers=AUTH_MGR)
        assert resp.status_code == 201, resp.text
        inspection_id = resp.json()["id"]

        override_resp = client.post(
            f"/api/inspections/{inspection_id}/baseline-override",
            json={"baseline_source": "vendor", "override_reason": "Vendor baseline approved by QA committee."},
            headers=AUTH_MGR,
        )
        assert override_resp.status_code == 200, override_resp.text
        data = override_resp.json()
        assert data["supervisor_review_required"] is False
        assert "override_applied" in data["baseline_status"]
        assert data["score_status"] == "scored_after_override"
        assert data["override_reason"] == "Vendor baseline approved by QA committee."
        assert data["override_by"] is not None

    def test_override_requires_reason_min_length(self):
        """Override reason must be at least 10 characters."""
        resp = client.post("/api/inspections", json=INSPECTION_WITH_IMAGE, headers=AUTH_MGR)
        assert resp.status_code == 201
        inspection_id = resp.json()["id"]

        override_resp = client.post(
            f"/api/inspections/{inspection_id}/baseline-override",
            json={"baseline_source": "vendor", "override_reason": "short"},
            headers=AUTH_MGR,
        )
        assert override_resp.status_code == 422


class TestOverrideCreatesAuditEvent:
    def setup_method(self):
        _remove_approved_baselines("scissors")

    def test_override_creates_audit_event(self):
        """Applying a baseline override creates a baseline_override_applied audit event."""
        resp = client.post("/api/inspections", json=INSPECTION_WITH_IMAGE, headers=AUTH_MGR)
        assert resp.status_code == 201
        inspection_id = resp.json()["id"]

        client.post(
            f"/api/inspections/{inspection_id}/baseline-override",
            json={"baseline_source": "hospital", "override_reason": "Hospital has validated equivalent baseline."},
            headers=AUTH_MGR,
        )

        # Verify audit event was created
        from app.db.session import SessionLocal
        from app.models.audit_log import AuditLog
        db = SessionLocal()
        try:
            event = db.query(AuditLog).filter(
                AuditLog.action_type == "baseline_override_applied",
                AuditLog.resource_type == "inspection",
                AuditLog.resource_id == str(inspection_id),
            ).first()
            assert event is not None, "Expected audit event 'baseline_override_applied' not found"
        finally:
            db.close()


class TestScoreNotFinalWithoutBaseline:
    def setup_method(self):
        _remove_approved_baselines("scissors")

    def test_score_not_final_without_approved_baseline(self):
        """Without approved baseline or override, score_status is not 'scored'."""
        resp = client.post("/api/inspections", json=INSPECTION_WITH_IMAGE, headers=AUTH_TECH)
        assert resp.status_code == 201
        data = resp.json()
        assert data["score_status"] != "scored", (
            f"Expected score_status != 'scored' but got '{data['score_status']}'"
        )
        assert data["risk_score"] == 0
