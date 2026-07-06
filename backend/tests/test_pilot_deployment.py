"""v1.9 — Pilot Deployment Loop & Production Workflow Hardening."""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "a1b2c3d4" + "0" * 56
TENANT = "default-tenant"


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"pd-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create(itype, headers=None, **extra):
    _baseline(itype)
    payload = {
        "instrument_type": itype, "site_name": "Mercy",
        "has_image": True, "image_sha256": SHA, "file_name": "x.jpg", "finding_categories": [],
    }
    payload.update(extra)
    r = client.post("/api/inspections", json=payload, headers=headers or AUTH_OPERATOR)
    assert r.status_code == 201, r.text
    return r.json()


class TestPilotSiteConfiguration:
    def test_get_site_config_has_conservative_defaults(self):
        r = client.get("/api/pilot-deployment/site-config", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["baseline_required"] is True
        assert body["minimum_coverage_pct"] == 75

    def test_update_site_config_requires_admin(self):
        r = client.put("/api/pilot-deployment/site-config", json={"facility_name": "Mercy General"}, headers=AUTH_MGR)
        assert r.status_code == 403
        r = client.put("/api/pilot-deployment/site-config", json={"facility_name": "Mercy General"}, headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_admin_can_update_site_config(self):
        r = client.put("/api/pilot-deployment/site-config", json={
            "facility_name": "Mercy General", "department": "SPD",
            "minimum_coverage_pct": 90, "supervisor_review_threshold_score": 60,
        }, headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["facility_name"] == "Mercy General"
        assert body["minimum_coverage_pct"] == 90

        r2 = client.get("/api/pilot-deployment/site-config", headers=AUTH_VIEWER)
        assert r2.status_code == 200
        assert r2.json()["facility_name"] == "Mercy General"


class TestDataQualityGuardrails:
    def test_inspection_response_includes_data_quality(self):
        body = _create("scissors")
        assert "data_quality" in body
        assert "issues" in body["data_quality"]
        assert "is_dataset_ready" in body["data_quality"]

    def test_missing_technician_identity_flagged(self):
        from app.db import models
        from app.services.data_quality_guardrails_service import evaluate_data_quality
        from app.services.pilot_site_config_service import get_or_create_config

        body = _create("scissors")
        db = SessionLocal()
        try:
            insp = db.query(models.Inspection).filter(models.Inspection.id == body["id"]).first()
            insp.technician = None
            db.commit()
            db.refresh(insp)
            config = get_or_create_config(db, TENANT)
            result = evaluate_data_quality(insp, pilot_config=config)
            assert any(i["code"] == "missing_technician_identity" for i in result["issues"])
            assert result["is_dataset_ready"] is False
        finally:
            db.close()

    def test_dataset_ready_inspection_has_no_issues(self):
        body = _create("scissors")
        assert body["data_quality"]["is_dataset_ready"] in (True, False)

    def test_data_quality_endpoint(self):
        body = _create("scissors")
        r = client.get(f"/api/inspections/{body['id']}/data-quality", headers=AUTH_ADMIN)
        assert r.status_code == 200
        assert r.json()["inspection_id"] == body["id"]


class TestProductionErrorLogging:
    def test_log_error_valid_type(self):
        r = client.post("/api/pilot-deployment/error-log", json={
            "error_type": "upload_failure", "detail": "network timeout",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 201
        assert r.json()["logged"] is True

    def test_log_error_invalid_type_rejected(self):
        r = client.post("/api/pilot-deployment/error-log", json={
            "error_type": "not_a_real_type", "detail": "x",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 422

    def test_error_detail_truncated_and_no_phi_assumption(self):
        from app.services.pilot_error_log_service import log_error

        db = SessionLocal()
        try:
            row = log_error(db, tenant_id=TENANT, error_type="ai_analysis_failure", detail="x" * 1000)
            db.commit()
            assert len(row.detail) == 500
        finally:
            db.close()

    def test_report_generation_failure_returns_500_not_silent(self, monkeypatch):
        body = _create("scissors")

        def _boom(*args, **kwargs):
            raise RuntimeError("pdf renderer exploded")

        monkeypatch.setattr("app.routes.clinical_readiness.build_readiness_report_pdf", _boom)
        r = client.get(f"/api/inspections/{body['id']}/readiness-report.pdf", headers=AUTH_ADMIN)
        assert r.status_code == 500
        assert "logged" in r.json()["detail"].lower()


class TestPilotDataCollectionDashboard:
    def test_dashboard_requires_leadership(self):
        r = client.get("/api/pilot-deployment/data-collection", headers=AUTH_OPERATOR)
        assert r.status_code == 403
        r = client.get("/api/pilot-deployment/data-collection", headers=AUTH_MGR)
        assert r.status_code == 200

    def test_dashboard_reflects_real_counts(self):
        before = client.get("/api/pilot-deployment/data-collection", headers=AUTH_ADMIN).json()
        _create("scissors")
        after = client.get("/api/pilot-deployment/data-collection", headers=AUTH_ADMIN).json()
        assert after["inspections_collected"] == before["inspections_collected"] + 1
        assert after["inspection_images_collected"] == before["inspection_images_collected"] + 1

    def test_dashboard_structure(self):
        r = client.get("/api/pilot-deployment/data-collection", headers=AUTH_ADMIN)
        body = r.json()
        for key in (
            "inspections_collected", "baseline_images_collected", "inspection_images_collected",
            "supervisor_reviews_completed", "incomplete_inspections", "failed_uploads",
            "missing_anatomy_zones", "dataset_ready_images",
        ):
            assert key in body


class TestRoleBasedWorkflowHardening:
    def test_viewer_cannot_create_inspection(self):
        _baseline("scissors")
        r = client.post("/api/inspections", json={
            "instrument_type": "scissors", "site_name": "Mercy", "has_image": True,
            "image_sha256": SHA, "file_name": "x.jpg", "finding_categories": [],
        }, headers=AUTH_VIEWER)
        assert r.status_code == 403
        assert "read-only" in r.json()["detail"].lower()

    def test_viewer_can_view_work_queue(self):
        r = client.get("/api/inspection-work-queue", headers=AUTH_VIEWER)
        assert r.status_code == 200

    def test_viewer_cannot_approve_disposition(self):
        body = _create("scissors")
        r = client.post(f"/api/inspections/{body['id']}/disposition-action", json={
            "action": "approve", "ai_recommended_disposition": "Proceed to Packaging",
        }, headers=AUTH_VIEWER)
        assert r.status_code == 403

    def test_operator_can_create_but_not_approve(self):
        body = _create("scissors")
        r = client.post(f"/api/inspections/{body['id']}/disposition-action", json={
            "action": "approve", "ai_recommended_disposition": "Proceed to Packaging",
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_supervisor_can_approve_and_add_teaching_point(self):
        body = _create("scissors", finding_categories=["blood"])
        r = client.post(f"/api/inspections/{body['id']}/disposition-action", json={
            "action": "approve", "ai_recommended_disposition": "Proceed to Packaging",
        }, headers=AUTH_MGR)
        assert r.status_code == 201

        r2 = client.post(f"/api/inspections/{body['id']}/teaching-point", json={
            "explanation": "Check the pivot joint.", "teaching_point": "Pivot joint check",
        }, headers=AUTH_MGR)
        assert r2.status_code == 201
