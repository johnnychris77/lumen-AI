"""Tests for P14 pilot operations endpoints: inspection CRUD, DQ enforcement, metrics, tenant provisioning."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# All tests use the standard dev-token which maps to the admin role in the dev auth map.
# This matches the convention used across all other test files in the suite.
AUTH = {"Authorization": "Bearer dev-token"}

ADMIN_HEADERS = AUTH
MANAGER_HEADERS = AUTH
VIEWER_HEADERS = AUTH

VALID_INSPECTION = {
    "instrument_type": "scissors",
    "material_type": "stainless_steel",
    "stain_detected": False,
    "detected_issue": "none",
    "site_name": "Pilot Hospital A",
    "vendor_name": "AcmeSurgical",
}


# ---------------------------------------------------------------------------
# POST /api/inspections — DQ enforcement
# ---------------------------------------------------------------------------

class TestInspectionCreate:
    def test_create_valid_inspection(self):
        res = client.post("/api/inspections", json=VALID_INSPECTION, headers=VIEWER_HEADERS)
        assert res.status_code == 201
        data = res.json()
        assert data["instrument_type"] == "scissors"
        assert data["status"] == "pending"
        assert "id" in data

    def test_dq10_stain_true_requires_issue(self):
        payload = {**VALID_INSPECTION, "stain_detected": True, "detected_issue": "none"}
        res = client.post("/api/inspections", json=payload, headers=VIEWER_HEADERS)
        assert res.status_code == 422

    def test_dq11_confidence_out_of_range(self):
        payload = {**VALID_INSPECTION, "confidence": 150.0}
        res = client.post("/api/inspections", json=payload, headers=VIEWER_HEADERS)
        assert res.status_code == 422

    def test_invalid_instrument_type_rejected(self):
        payload = {**VALID_INSPECTION, "instrument_type": "magic_wand"}
        res = client.post("/api/inspections", json=payload, headers=VIEWER_HEADERS)
        assert res.status_code == 422

    def test_invalid_material_type_rejected(self):
        payload = {**VALID_INSPECTION, "material_type": "cardboard"}
        res = client.post("/api/inspections", json=payload, headers=VIEWER_HEADERS)
        assert res.status_code == 422

    def test_invalid_detected_issue_rejected(self):
        payload = {**VALID_INSPECTION, "detected_issue": "mystery_goo"}
        res = client.post("/api/inspections", json=payload, headers=VIEWER_HEADERS)
        assert res.status_code == 422

    def test_empty_site_name_rejected(self):
        payload = {**VALID_INSPECTION, "site_name": ""}
        res = client.post("/api/inspections", json=payload, headers=VIEWER_HEADERS)
        assert res.status_code == 422

    def test_stain_with_valid_issue_accepted(self):
        payload = {**VALID_INSPECTION, "stain_detected": True, "detected_issue": "blood"}
        res = client.post("/api/inspections", json=payload, headers=VIEWER_HEADERS)
        assert res.status_code == 201

    def test_unauthenticated_rejected(self):
        res = client.post("/api/inspections", json=VALID_INSPECTION)
        assert res.status_code in (401, 403)


# ---------------------------------------------------------------------------
# PATCH /api/inspections/{id}/status
# ---------------------------------------------------------------------------

class TestInspectionStatusUpdate:
    def _create(self) -> int:
        res = client.post("/api/inspections", json=VALID_INSPECTION, headers=MANAGER_HEADERS)
        assert res.status_code == 201
        return res.json()["id"]

    def test_manager_can_invalidate(self):
        iid = self._create()
        res = client.patch(
            f"/api/inspections/{iid}/status",
            json={"status": "invalidated", "notes": "Duplicate entry"},
            headers=MANAGER_HEADERS,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "invalidated"

    def test_manager_can_set_reviewed(self):
        iid = self._create()
        res = client.patch(
            f"/api/inspections/{iid}/status",
            json={"status": "reviewed"},
            headers=MANAGER_HEADERS,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "reviewed"

    def test_invalid_status_rejected(self):
        iid = self._create()
        res = client.patch(
            f"/api/inspections/{iid}/status",
            json={"status": "deleted_forever"},
            headers=MANAGER_HEADERS,
        )
        assert res.status_code == 422

    def test_404_for_nonexistent(self):
        res = client.patch(
            "/api/inspections/999999/status",
            json={"status": "reviewed"},
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 404

    def test_unauthenticated_rejected(self):
        res = client.patch("/api/inspections/1/status", json={"status": "reviewed"})
        assert res.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/pilot/metrics
# ---------------------------------------------------------------------------

class TestPilotMetrics:
    def test_manager_can_get_metrics(self):
        res = client.get("/api/pilot/metrics", headers=MANAGER_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "adoption" in data
        assert "data_quality" in data
        assert "coverage" in data
        assert data["human_review_required"] is True

    def test_metrics_adoption_keys(self):
        res = client.get("/api/pilot/metrics", headers=MANAGER_HEADERS)
        adoption = res.json()["adoption"]
        assert "total_inspections" in adoption
        assert "inspections_last_7_days" in adoption
        assert "weekly_target" in adoption
        assert "on_track" in adoption

    def test_metrics_data_quality_keys(self):
        res = client.get("/api/pilot/metrics", headers=MANAGER_HEADERS)
        dq = res.json()["data_quality"]
        assert "completeness_pct" in dq
        assert "consistency_pct" in dq
        assert "completeness_target" in dq

    def test_admin_can_get_metrics(self):
        res = client.get("/api/pilot/metrics", headers=ADMIN_HEADERS)
        assert res.status_code == 200

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot/metrics")
        assert res.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/admin/tenants — tenant provisioning
# ---------------------------------------------------------------------------

class TestTenantProvisioning:
    def test_admin_can_provision_tenant(self):
        uid = str(int(time.time() * 1000))[-8:]
        payload = {
            "tenant_id": f"pilot-hospital-{uid}",
            "tenant_name": "Pilot Hospital XYZ",
            "admin_email": f"coord-{uid}@pilothospital.org",
            "region": "north_america",
        }
        res = client.post("/api/admin/tenants", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 201
        data = res.json()
        assert data["tenant_id"] == f"pilot-hospital-{uid}"
        assert data["status"] == "provisioned"
        assert "membership_id" in data

    def test_duplicate_tenant_returns_409(self):
        uid = str(int(time.time() * 1000))[-8:]
        payload = {
            "tenant_id": f"pilot-dup-{uid}",
            "tenant_name": "Dup Hospital",
            "admin_email": "admin@dup.org",
        }
        client.post("/api/admin/tenants", json=payload, headers=ADMIN_HEADERS)
        res = client.post("/api/admin/tenants", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 409

    def test_invalid_tenant_id_format_rejected(self):
        payload = {
            "tenant_id": "UPPER_CASE",
            "tenant_name": "Bad ID Hospital",
            "admin_email": "x@x.com",
        }
        res = client.post("/api/admin/tenants", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 422

    def test_invalid_region_rejected(self):
        payload = {
            "tenant_id": "test-region-bad",
            "tenant_name": "Region Bad",
            "admin_email": "x@x.com",
            "region": "mars",
        }
        res = client.post("/api/admin/tenants", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 422

    def test_invalid_email_rejected(self):
        payload = {
            "tenant_id": "test-bad-email",
            "tenant_name": "Bad Email Hospital",
            "admin_email": "not-an-email",
        }
        res = client.post("/api/admin/tenants", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 422

    def test_unauthenticated_rejected(self):
        res = client.post("/api/admin/tenants", json={"tenant_id": "x", "tenant_name": "X", "admin_email": "x@x.com"})
        assert res.status_code in (401, 403)

    def test_eu_region_accepted(self):
        uid = str(int(time.time() * 1000))[-8:]
        payload = {
            "tenant_id": f"pilot-eu-{uid}",
            "tenant_name": "EU Hospital",
            "admin_email": "coord@euhospital.eu",
            "region": "eu",
        }
        res = client.post("/api/admin/tenants", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 201
        assert res.json()["region"] == "eu"

