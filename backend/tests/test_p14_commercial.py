"""P14 Commercial Launch — executive dashboard endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}

ROLES = [
    "spd_director",
    "market_director",
    "infection_prevention",
    "quality_leadership",
    "coo",
    "cno",
    "cfo",
]


class TestExecutiveDashboard:
    """Tests for /api/executive/dashboard/{role}"""

    @pytest.mark.parametrize("role", ROLES)
    def test_each_role_returns_200(self, role: str) -> None:
        resp = client.get(f"/api/executive/dashboard/{role}", headers=HEADERS)
        assert resp.status_code == 200, f"Role {role} returned {resp.status_code}"

    @pytest.mark.parametrize("role", ROLES)
    def test_each_role_has_required_base_fields(self, role: str) -> None:
        resp = client.get(f"/api/executive/dashboard/{role}", headers=HEADERS)
        data = resp.json()
        assert "tenant_id" in data
        assert "role" in data
        assert "generated_at" in data
        assert "data_source" in data
        assert "inspection_volume" in data
        assert data["role"] == role

    def test_invalid_role_returns_400(self) -> None:
        resp = client.get("/api/executive/dashboard/invalid_role", headers=HEADERS)
        assert resp.status_code == 400

    def test_auth_required(self) -> None:
        resp = client.get("/api/executive/dashboard/coo")
        assert resp.status_code == 401

    def test_period_param_accepted(self) -> None:
        resp = client.get(
            "/api/executive/dashboard/coo?period=90d", headers=HEADERS
        )
        assert resp.status_code == 200
        assert resp.json()["period"] == "90d"

    def test_facility_id_param_accepted(self) -> None:
        resp = client.get(
            "/api/executive/dashboard/cfo?facility_id=facility-abc", headers=HEADERS
        )
        assert resp.status_code == 200
        assert resp.json()["facility_id"] == "facility-abc"

    def test_data_source_is_mock(self) -> None:
        resp = client.get("/api/executive/dashboard/coo", headers=HEADERS)
        assert resp.json()["data_source"] == "mock"


class TestExecutiveSummary:
    """Tests for /api/executive/summary"""

    def test_summary_returns_200(self) -> None:
        resp = client.get("/api/executive/summary", headers=HEADERS)
        assert resp.status_code == 200

    def test_summary_has_headline_kpis(self) -> None:
        resp = client.get("/api/executive/summary", headers=HEADERS)
        data = resp.json()
        assert "headline_kpis" in data
        kpis = data["headline_kpis"]
        assert "inspection_volume_30d" in kpis
        assert "jc_readiness_score" in kpis
        assert "total_roi_usd_ytd" in kpis

    def test_summary_has_available_roles(self) -> None:
        resp = client.get("/api/executive/summary", headers=HEADERS)
        data = resp.json()
        assert "available_roles" in data

    def test_summary_available_roles_contains_all_seven(self) -> None:
        resp = client.get("/api/executive/summary", headers=HEADERS)
        available = resp.json()["available_roles"]
        for role in ROLES:
            assert role in available, f"Role {role} missing from available_roles"

    def test_summary_data_source_present(self) -> None:
        resp = client.get("/api/executive/summary", headers=HEADERS)
        assert "data_source" in resp.json()

    def test_summary_facility_id_param_accepted(self) -> None:
        resp = client.get(
            "/api/executive/summary?facility_id=fac-001", headers=HEADERS
        )
        assert resp.status_code == 200
        assert resp.json()["facility_id"] == "fac-001"

    def test_summary_auth_required(self) -> None:
        resp = client.get("/api/executive/summary")
        assert resp.status_code == 401


class TestRoleSpecificKPIs:
    """Tests for role-specific KPI fields in dashboard responses."""

    def test_cfo_dashboard_has_labor_savings_usd(self) -> None:
        resp = client.get("/api/executive/dashboard/cfo", headers=HEADERS)
        data = resp.json()
        assert "labor_savings_usd" in data
        assert isinstance(data["labor_savings_usd"], (int, float))

    def test_coo_dashboard_has_bottleneck_station(self) -> None:
        resp = client.get("/api/executive/dashboard/coo", headers=HEADERS)
        data = resp.json()
        assert "bottleneck_station" in data
        assert isinstance(data["bottleneck_station"], str)

    def test_infection_prevention_has_critical_fn_rate_pct(self) -> None:
        resp = client.get(
            "/api/executive/dashboard/infection_prevention", headers=HEADERS
        )
        data = resp.json()
        assert "critical_fn_rate_pct" in data
        assert isinstance(data["critical_fn_rate_pct"], (int, float))

    def test_quality_leadership_has_jc_readiness_score(self) -> None:
        resp = client.get(
            "/api/executive/dashboard/quality_leadership", headers=HEADERS
        )
        data = resp.json()
        assert "jc_readiness_score" in data
        assert isinstance(data["jc_readiness_score"], (int, float))

    def test_cno_dashboard_has_staff_adoption_pct(self) -> None:
        resp = client.get("/api/executive/dashboard/cno", headers=HEADERS)
        data = resp.json()
        assert "staff_adoption_pct" in data
        assert isinstance(data["staff_adoption_pct"], (int, float))
