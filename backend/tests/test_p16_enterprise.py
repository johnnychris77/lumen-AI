"""P16 Enterprise Expansion tests — hierarchy, onboarding, baselines, dashboards, readiness."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token"}

# Unique suffix per test run to avoid DB collisions
TS = str(int(time.time()))[-6:]


def uid(prefix: str) -> str:
    return f"{prefix}-{TS}"


# ---------------------------------------------------------------------------
# Phase 1: Health System hierarchy
# ---------------------------------------------------------------------------

class TestHealthSystem:
    SYS_ID = uid("sys-test")

    def test_create_health_system(self):
        res = client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID,
            "system_name": "Test Health System",
            "hq_region": "north_america",
            "contract_tier": "enterprise",
            "admin_email": "admin@testsystem.org",
        }, headers=AUTH)
        assert res.status_code == 201
        assert res.json()["system_id"] == self.SYS_ID

    def test_duplicate_system_returns_409(self):
        client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID, "system_name": "Test", "admin_email": "a@b.com",
        }, headers=AUTH)
        res = client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID, "system_name": "Test", "admin_email": "a@b.com",
        }, headers=AUTH)
        assert res.status_code == 409

    def test_invalid_system_id_rejected(self):
        res = client.post("/api/enterprise/systems", json={
            "system_id": "UPPER_CASE", "system_name": "Bad", "admin_email": "x@x.com",
        }, headers=AUTH)
        assert res.status_code == 422

    def test_invalid_contract_tier_rejected(self):
        res = client.post("/api/enterprise/systems", json={
            "system_id": uid("sys-bad-tier"), "system_name": "Bad",
            "admin_email": "x@x.com", "contract_tier": "diamond",
        }, headers=AUTH)
        assert res.status_code == 422

    def test_list_health_systems(self):
        res = client.get("/api/enterprise/systems", headers=AUTH)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_health_system(self):
        # Create first
        sid = uid("sys-get")
        client.post("/api/enterprise/systems", json={
            "system_id": sid, "system_name": "Get Test", "admin_email": "g@g.com",
        }, headers=AUTH)
        res = client.get(f"/api/enterprise/systems/{sid}", headers=AUTH)
        assert res.status_code == 200
        assert res.json()["system_id"] == sid

    def test_get_nonexistent_returns_404(self):
        res = client.get("/api/enterprise/systems/does-not-exist", headers=AUTH)
        assert res.status_code == 404

    def test_unauthenticated_rejected(self):
        res = client.get("/api/enterprise/systems")
        assert res.status_code in (401, 403)


class TestMarkets:
    SYS_ID = uid("sys-mkt")

    @pytest.fixture(autouse=True)
    def _setup(self):
        client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID, "system_name": "Market Test System", "admin_email": "m@m.com",
        }, headers=AUTH)

    def test_create_market(self):
        res = client.post("/api/enterprise/markets", json={
            "market_id": uid("mkt"), "market_name": "Southwest Market",
            "system_id": self.SYS_ID, "region": "north_america",
        }, headers=AUTH)
        assert res.status_code == 201
        assert res.json()["system_id"] == self.SYS_ID

    def test_market_nonexistent_system_returns_404(self):
        res = client.post("/api/enterprise/markets", json={
            "market_id": uid("mkt-x"), "market_name": "No System",
            "system_id": "no-such-system",
        }, headers=AUTH)
        assert res.status_code == 404

    def test_duplicate_market_returns_409(self):
        mid = uid("mkt-dup")
        payload = {"market_id": mid, "market_name": "Dup", "system_id": self.SYS_ID}
        client.post("/api/enterprise/markets", json=payload, headers=AUTH)
        res = client.post("/api/enterprise/markets", json=payload, headers=AUTH)
        assert res.status_code == 409

    def test_list_markets(self):
        res = client.get(f"/api/enterprise/systems/{self.SYS_ID}/markets", headers=AUTH)
        assert res.status_code == 200
        assert isinstance(res.json(), list)


class TestFacilities:
    SYS_ID = uid("sys-fac")
    MKT_ID = uid("mkt-fac")
    RGN_ID = uid("rgn-fac")

    @pytest.fixture(autouse=True)
    def _setup(self):
        client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID, "system_name": "Facility Test System", "admin_email": "f@f.com",
        }, headers=AUTH)
        client.post("/api/enterprise/markets", json={
            "market_id": self.MKT_ID, "market_name": "Test Market", "system_id": self.SYS_ID,
        }, headers=AUTH)
        client.post("/api/enterprise/regions", json={
            "region_id": self.RGN_ID, "region_name": "Test Region",
            "market_id": self.MKT_ID, "system_id": self.SYS_ID,
        }, headers=AUTH)

    def test_create_facility(self):
        fid = uid("fac")
        res = client.post("/api/enterprise/facilities", json={
            "facility_id": fid, "facility_name": "Test Hospital",
            "region_id": self.RGN_ID, "market_id": self.MKT_ID,
            "system_id": self.SYS_ID, "tenant_id": uid("tenant"),
            "facility_type": "hospital", "bed_count": 350,
        }, headers=AUTH)
        assert res.status_code == 201
        assert res.json()["onboarding_status"] == "pending"

    def test_invalid_facility_type_rejected(self):
        res = client.post("/api/enterprise/facilities", json={
            "facility_id": uid("fac-bad"), "facility_name": "Bad",
            "region_id": self.RGN_ID, "market_id": self.MKT_ID,
            "system_id": self.SYS_ID, "tenant_id": uid("t"),
            "facility_type": "spaceship",
        }, headers=AUTH)
        assert res.status_code == 422

    def test_duplicate_facility_returns_409(self):
        fid = uid("fac-dup")
        payload = {
            "facility_id": fid, "facility_name": "Dup",
            "region_id": self.RGN_ID, "market_id": self.MKT_ID,
            "system_id": self.SYS_ID, "tenant_id": uid("td"),
        }
        client.post("/api/enterprise/facilities", json=payload, headers=AUTH)
        res = client.post("/api/enterprise/facilities", json=payload, headers=AUTH)
        assert res.status_code == 409

    def test_list_facilities(self):
        res = client.get(f"/api/enterprise/systems/{self.SYS_ID}/facilities", headers=AUTH)
        assert res.status_code == 200
        assert isinstance(res.json(), list)


class TestDepartments:
    SYS_ID = uid("sys-dep")
    FAC_ID = uid("fac-dep")

    @pytest.fixture(autouse=True)
    def _setup(self):
        client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID, "system_name": "Dept Test System", "admin_email": "d@d.com",
        }, headers=AUTH)
        mkt = uid("mkt-dep")
        rgn = uid("rgn-dep")
        client.post("/api/enterprise/markets", json={
            "market_id": mkt, "market_name": "M", "system_id": self.SYS_ID,
        }, headers=AUTH)
        client.post("/api/enterprise/regions", json={
            "region_id": rgn, "region_name": "R", "market_id": mkt, "system_id": self.SYS_ID,
        }, headers=AUTH)
        client.post("/api/enterprise/facilities", json={
            "facility_id": self.FAC_ID, "facility_name": "Dept Hospital",
            "region_id": rgn, "market_id": mkt,
            "system_id": self.SYS_ID, "tenant_id": uid("t-dep"),
        }, headers=AUTH)

    def test_create_department(self):
        res = client.post("/api/enterprise/departments", json={
            "department_id": uid("dept"), "department_name": "SPD Unit A",
            "facility_id": self.FAC_ID, "department_type": "spd",
        }, headers=AUTH)
        assert res.status_code == 201
        assert res.json()["department_type"] == "spd"

    def test_invalid_department_type_rejected(self):
        res = client.post("/api/enterprise/departments", json={
            "department_id": uid("dept-bad"), "department_name": "Bad",
            "facility_id": self.FAC_ID, "department_type": "cafeteria",
        }, headers=AUTH)
        assert res.status_code == 422

    def test_nonexistent_facility_returns_404(self):
        res = client.post("/api/enterprise/departments", json={
            "department_id": uid("dept-nf"), "department_name": "No Facility",
            "facility_id": "no-such-facility", "department_type": "spd",
        }, headers=AUTH)
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Phase 2: Onboarding Workflows
# ---------------------------------------------------------------------------

class TestOnboarding:
    SYS_ID = uid("sys-wf")

    @pytest.fixture(autouse=True)
    def _setup(self):
        client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID, "system_name": "WF Test", "admin_email": "wf@wf.com",
        }, headers=AUTH)

    def test_start_site_onboarding(self):
        res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "site", "target_id": "hospital-alpha",
            "system_id": self.SYS_ID,
        }, headers=AUTH)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "in_progress"
        assert "workflow_id" in data
        assert data["current_step"] == "initiated"

    def test_start_user_onboarding(self):
        res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "user", "target_id": "nurse.jones@hospital.org",
            "system_id": self.SYS_ID,
        }, headers=AUTH)
        assert res.status_code == 201
        assert res.json()["workflow_type"] == "user"

    def test_start_vendor_onboarding(self):
        res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "vendor", "target_id": "acme-surgical",
            "system_id": self.SYS_ID,
        }, headers=AUTH)
        assert res.status_code == 201

    def test_start_baseline_onboarding(self):
        res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "baseline", "target_id": "scissors-v2",
            "system_id": self.SYS_ID,
        }, headers=AUTH)
        assert res.status_code == 201

    def test_invalid_workflow_type_rejected(self):
        res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "magic", "target_id": "x", "system_id": self.SYS_ID,
        }, headers=AUTH)
        assert res.status_code == 422

    def test_advance_onboarding_step(self):
        # Start
        start_res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "site", "target_id": "hospital-beta",
            "system_id": self.SYS_ID,
        }, headers=AUTH)
        wf_id = start_res.json()["workflow_id"]

        # Advance
        res = client.patch(f"/api/enterprise/onboarding/{wf_id}/advance", json={
            "completed_step": "initiated", "notes": "Kickoff complete",
        }, headers=AUTH)
        assert res.status_code == 200
        assert "documents_collected" in res.json()["current_step"] or res.json()["steps_completed"]

    def test_advance_invalid_step_rejected(self):
        start_res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "site", "target_id": "hospital-gamma",
            "system_id": self.SYS_ID,
        }, headers=AUTH)
        wf_id = start_res.json()["workflow_id"]
        res = client.patch(f"/api/enterprise/onboarding/{wf_id}/advance", json={
            "completed_step": "magic_step",
        }, headers=AUTH)
        assert res.status_code == 422

    def test_get_onboarding_workflow(self):
        start_res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "user", "target_id": "staff@hosp.org",
            "system_id": self.SYS_ID,
        }, headers=AUTH)
        wf_id = start_res.json()["workflow_id"]
        res = client.get(f"/api/enterprise/onboarding/{wf_id}", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert data["workflow_id"] == wf_id
        assert "progress_pct" in data
        assert "steps_remaining" in data

    def test_get_nonexistent_workflow_404(self):
        res = client.get("/api/enterprise/onboarding/wf-does-not-exist", headers=AUTH)
        assert res.status_code == 404

    def test_list_workflows(self):
        res = client.get(f"/api/enterprise/systems/{self.SYS_ID}/onboarding", headers=AUTH)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_complete_full_site_workflow(self):
        """Advance through all site onboarding steps and reach completed."""
        start_res = client.post("/api/enterprise/onboarding", json={
            "workflow_type": "site", "target_id": "hospital-delta",
            "system_id": self.SYS_ID,
        }, headers=AUTH)
        wf_id = start_res.json()["workflow_id"]
        steps = ["initiated", "documents_collected", "tenant_provisioned",
                 "users_invited", "baseline_assigned", "training_complete", "go_live", "completed"]
        for step in steps:
            client.patch(f"/api/enterprise/onboarding/{wf_id}/advance",
                         json={"completed_step": step}, headers=AUTH)

        res = client.get(f"/api/enterprise/onboarding/{wf_id}", headers=AUTH)
        assert res.json()["status"] == "completed"
        assert res.json()["progress_pct"] == 100


# ---------------------------------------------------------------------------
# Phase 3: Enterprise Baseline Distribution
# ---------------------------------------------------------------------------

class TestEnterpriseBaselines:
    SYS_ID = uid("sys-bl")

    @pytest.fixture(autouse=True)
    def _setup(self):
        client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID, "system_name": "Baseline Test", "admin_email": "bl@bl.com",
        }, headers=AUTH)

    def test_create_baseline(self):
        res = client.post("/api/enterprise/baselines", json={
            "baseline_id": uid("bl"), "system_id": self.SYS_ID,
            "instrument_type": "scissors", "material_type": "stainless_steel",
            "acceptance_criteria": {"max_contamination_score": 30},
            "created_by": "quality.manager@hospital.org",
            "change_summary": "Initial scissors baseline",
        }, headers=AUTH)
        assert res.status_code == 201
        assert res.json()["approval_status"] == "draft"

    def test_duplicate_baseline_version_returns_409(self):
        bid = uid("bl-dup")
        payload = {
            "baseline_id": bid, "system_id": self.SYS_ID,
            "instrument_type": "forceps", "material_type": "stainless_steel",
            "created_by": "qm@h.org",
        }
        client.post("/api/enterprise/baselines", json=payload, headers=AUTH)
        res = client.post("/api/enterprise/baselines", json=payload, headers=AUTH)
        assert res.status_code == 409

    def test_approve_baseline(self):
        bid = uid("bl-apr")
        client.post("/api/enterprise/baselines", json={
            "baseline_id": bid, "system_id": self.SYS_ID,
            "instrument_type": "needle_holder", "material_type": "stainless_steel",
            "created_by": "qm@h.org",
        }, headers=AUTH)
        res = client.post(f"/api/enterprise/baselines/{bid}/approve?version=1.0.0", headers=AUTH)
        assert res.status_code == 200
        assert res.json()["approval_status"] == "approved"

    def test_approve_nonexistent_baseline_returns_404(self):
        res = client.post("/api/enterprise/baselines/no-such-baseline/approve?version=1.0.0", headers=AUTH)
        assert res.status_code == 404

    def test_publish_without_approval_returns_422(self):
        bid = uid("bl-pub-unap")
        client.post("/api/enterprise/baselines", json={
            "baseline_id": bid, "system_id": self.SYS_ID,
            "instrument_type": "retractor", "material_type": "titanium",
            "created_by": "qm@h.org",
        }, headers=AUTH)
        res = client.post(
            f"/api/enterprise/baselines/{bid}/publish?version=1.0.0&facility_ids=fac-001",
            headers=AUTH,
        )
        assert res.status_code == 422

    def test_approve_then_publish(self):
        bid = uid("bl-pub")
        client.post("/api/enterprise/baselines", json={
            "baseline_id": bid, "system_id": self.SYS_ID,
            "instrument_type": "grasper", "material_type": "stainless_steel",
            "created_by": "qm@h.org",
        }, headers=AUTH)
        client.post(f"/api/enterprise/baselines/{bid}/approve?version=1.0.0", headers=AUTH)
        res = client.post(
            f"/api/enterprise/baselines/{bid}/publish?version=1.0.0&facility_ids=fac-001&facility_ids=fac-002",
            headers=AUTH,
        )
        assert res.status_code == 200
        assert res.json()["published_to_count"] == 2

    def test_list_baselines(self):
        res = client.get(f"/api/enterprise/baselines?system_id={self.SYS_ID}", headers=AUTH)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_baseline_version_history(self):
        bid = uid("bl-hist")
        client.post("/api/enterprise/baselines", json={
            "baseline_id": bid, "system_id": self.SYS_ID,
            "instrument_type": "dilator", "material_type": "stainless_steel",
            "created_by": "qm@h.org",
        }, headers=AUTH)
        res = client.get(f"/api/enterprise/baselines/{bid}/history", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert data["baseline_id"] == bid
        assert data["version_count"] >= 1
        assert "versions" in data

    def test_version_history_nonexistent_returns_404(self):
        res = client.get("/api/enterprise/baselines/no-such-baseline/history", headers=AUTH)
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Phase 4-6: Dashboards, Adoption, Readiness
# ---------------------------------------------------------------------------

class TestEnterpriseDashboards:
    SYS_ID = uid("sys-dash")

    @pytest.fixture(autouse=True)
    def _setup(self):
        client.post("/api/enterprise/systems", json={
            "system_id": self.SYS_ID, "system_name": "Dashboard Test", "admin_email": "da@da.com",
        }, headers=AUTH)

    def test_system_quality_dashboard(self):
        res = client.get(f"/api/enterprise/dashboards/system-quality/{self.SYS_ID}", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert "kpis" in data
        assert "facility_breakdown" in data
        assert data["human_review_required"] is True

    def test_market_director_dashboard(self):
        mid = uid("mkt-dash")
        client.post("/api/enterprise/markets", json={
            "market_id": mid, "market_name": "Test Market", "system_id": self.SYS_ID,
        }, headers=AUTH)
        res = client.get(f"/api/enterprise/dashboards/market/{mid}", headers=AUTH)
        assert res.status_code == 200
        assert "facility_count" in res.json()

    def test_enterprise_scorecard(self):
        res = client.get(f"/api/enterprise/dashboards/executive-scorecard/{self.SYS_ID}", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert "overall_status" in data
        assert "kpis" in data
        assert data["overall_status"] in ("green", "amber", "red")
        assert data["human_review_required"] is True

    def test_benchmarking_dashboard(self):
        res = client.get(f"/api/enterprise/dashboards/benchmarking/{self.SYS_ID}", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert "system_averages" in data
        assert "external_benchmarks" in data
        assert data["human_review_required"] is True

    def test_adoption_analytics(self):
        res = client.get(f"/api/enterprise/dashboards/adoption/{self.SYS_ID}", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert "system_summary" in data
        assert "facility_adoption" in data
        assert "onboarding_pipeline" in data

    def test_readiness_scores(self):
        res = client.get(f"/api/enterprise/dashboards/readiness/{self.SYS_ID}", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert "readiness_scores" in data
        assert "summary" in data
        assert "expansion_candidate_facilities" in data
        assert data["human_review_required"] is True

    def test_readiness_weights_sum_to_one(self):
        res = client.get(f"/api/enterprise/dashboards/readiness/{self.SYS_ID}", headers=AUTH)
        weights = res.json()["weights_used"]
        total = round(sum(weights.values()), 2)
        assert total == 1.00

    def test_facility_readiness_detail_404(self):
        res = client.get(
            f"/api/enterprise/dashboards/readiness/{self.SYS_ID}/facility/no-such-facility",
            headers=AUTH,
        )
        assert res.status_code == 404

    def test_unauthenticated_rejected(self):
        res = client.get(f"/api/enterprise/dashboards/system-quality/{self.SYS_ID}")
        assert res.status_code in (401, 403)
