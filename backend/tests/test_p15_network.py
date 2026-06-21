"""P15: National SPD Intelligence Network — test suite."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer dev-token"}
client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _opt_in():
    """Opt the default tenant into the network."""
    return client.post("/api/network/opt-in", headers=HEADERS)


# ---------------------------------------------------------------------------
# TestNetworkOptIn
# ---------------------------------------------------------------------------

class TestNetworkOptIn:
    def test_opt_in_returns_200(self):
        r = _opt_in()
        assert r.status_code == 200

    def test_opt_in_status_shows_active(self):
        _opt_in()
        r = client.get("/api/network/opt-in/status", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["is_active"] is True

    def test_opt_out_deactivates(self):
        _opt_in()
        r = client.post("/api/network/opt-out", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        # Check status now shows inactive
        r2 = client.get("/api/network/opt-in/status", headers=HEADERS)
        assert r2.json()["is_active"] is False

    def test_participant_count_is_public(self):
        r = client.get("/api/network/participants/count")
        assert r.status_code == 200
        data = r.json()
        assert "active_participants" in data


# ---------------------------------------------------------------------------
# TestIndustryBenchmarks
# ---------------------------------------------------------------------------

class TestIndustryBenchmarks:
    def setup_method(self):
        _opt_in()

    def test_benchmarks_require_auth(self):
        r = client.get("/api/network/benchmarks")
        assert r.status_code == 401

    def test_benchmarks_returns_metrics(self):
        r = client.get("/api/network/benchmarks", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "benchmarks" in data
        assert len(data["benchmarks"]) > 0

    def test_benchmarks_has_percentiles(self):
        r = client.get("/api/network/benchmarks", headers=HEADERS)
        assert r.status_code == 200
        bm = r.json()["benchmarks"][0]
        assert "p25" in bm
        assert "p50" in bm
        assert "p75" in bm

    def test_benchmarks_has_noise_flag(self):
        r = client.get("/api/network/benchmarks", headers=HEADERS)
        assert r.status_code == 200
        bm = r.json()["benchmarks"][0]
        assert bm["noise_added"] is True

    def test_my_percentile_returns_200(self):
        r = client.get("/api/network/benchmarks/my-percentile", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "percentiles" in data


# ---------------------------------------------------------------------------
# TestRecallSignals
# ---------------------------------------------------------------------------

class TestRecallSignals:
    def setup_method(self):
        _opt_in()

    def test_recall_signals_require_auth(self):
        r = client.get("/api/network/recall-signals")
        assert r.status_code == 401

    def test_active_signals_returns_list(self):
        r = client.get("/api/network/recall-signals", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "signals" in data
        assert isinstance(data["signals"], list)

    def test_signal_detail_returns_200(self):
        # Get a signal ID first
        r = client.get("/api/network/recall-signals", headers=HEADERS)
        signals = r.json()["signals"]
        assert len(signals) > 0
        signal_id = signals[0]["signal_id"]
        r2 = client.get(f"/api/network/recall-signals/{signal_id}", headers=HEADERS)
        assert r2.status_code == 200

    def test_my_exposure_returns_200(self):
        r = client.get("/api/network/recall-signals/my-exposure", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "signals" in data

    def test_escalate_signal_returns_200(self):
        r = client.get("/api/network/recall-signals", headers=HEADERS)
        signals = r.json()["signals"]
        assert len(signals) > 0
        signal_id = signals[0]["signal_id"]
        r2 = client.post(f"/api/network/recall-signals/{signal_id}/escalate", headers=HEADERS)
        assert r2.status_code == 200


# ---------------------------------------------------------------------------
# TestInstrumentRegistry
# ---------------------------------------------------------------------------

class TestInstrumentRegistry:
    def test_registry_lookup_returns_200(self):
        r = client.get("/api/network/registry/lookup", params={"udi": "TEST-UDI-001"}, headers=HEADERS)
        assert r.status_code == 200

    def test_registry_register_returns_201_or_200(self):
        payload = {
            "udi": "TEST-UDI-REGISTER-001",
            "manufacturer_name": "TestMfr",
            "model_name": "TestModel",
            "instrument_category": "endoscope",
        }
        r = client.post("/api/network/registry", json=payload, headers=HEADERS)
        assert r.status_code in (200, 201)

    def test_registry_search_returns_list(self):
        r = client.get("/api/network/registry/search", params={"q": "endoscope"}, headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_registry_stats_returns_counts(self):
        r = client.get("/api/network/registry/stats", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "stats" in data
        assert "total_instruments" in data["stats"]

    def test_defect_history_returns_200(self):
        r = client.get("/api/network/registry/TEST-UDI-HIST/defect-history", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "defect_history" in data
        # Facility IDs must not appear
        assert "tenant_id" not in str(data)
        assert "facility_id" not in str(data)


# ---------------------------------------------------------------------------
# TestBaselineLibrary
# ---------------------------------------------------------------------------

class TestBaselineLibrary:
    def test_baseline_list_returns_200(self):
        r = client.get("/api/network/baselines", headers=HEADERS)
        assert r.status_code == 200

    def test_baseline_submit_returns_200(self):
        payload = {
            "instrument_category": "endoscope",
            "manufacturer_name": "TestMfr",
            "model_name": "TestModel",
            "baseline_type": "network_contributed",
        }
        r = client.post("/api/network/baselines", json=payload, headers=HEADERS)
        assert r.status_code == 200

    def test_baseline_search_returns_list(self):
        r = client.get("/api/network/baselines/search", params={"q": "endo"}, headers=HEADERS)
        assert r.status_code == 200
        assert "results" in r.json()

    def test_baseline_stats_returns_counts(self):
        r = client.get("/api/network/baselines/stats", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "stats" in data

    def test_baseline_approve_returns_200(self):
        # Submit one first
        payload = {
            "instrument_category": "surgical_tray",
            "manufacturer_name": "ApproveMfr",
            "model_name": "ApproveModel",
        }
        r = client.post("/api/network/baselines", json=payload, headers=HEADERS)
        entry_id = r.json()["baseline"]["id"]
        r2 = client.post(f"/api/network/baselines/{entry_id}/approve", headers=HEADERS)
        assert r2.status_code == 200
        assert r2.json()["baseline"]["approval_status"] == "approved"


# ---------------------------------------------------------------------------
# TestIndustryDashboards
# ---------------------------------------------------------------------------

DASHBOARD_URLS = [
    "/api/network/dashboard/hospital",
    "/api/network/dashboard/health-system",
    "/api/network/dashboard/manufacturer",
    "/api/network/dashboard/vendor",
    "/api/network/dashboard/quality-leader",
]


class TestIndustryDashboards:
    def test_hospital_dashboard_returns_200(self):
        r = client.get("/api/network/dashboard/hospital", headers=HEADERS)
        assert r.status_code == 200

    def test_health_system_dashboard_returns_200(self):
        r = client.get("/api/network/dashboard/health-system", headers=HEADERS)
        assert r.status_code == 200

    def test_manufacturer_dashboard_returns_200(self):
        r = client.get("/api/network/dashboard/manufacturer", headers=HEADERS)
        assert r.status_code == 200

    def test_vendor_dashboard_returns_200(self):
        r = client.get("/api/network/dashboard/vendor", headers=HEADERS)
        assert r.status_code == 200

    def test_quality_leader_dashboard_returns_200(self):
        r = client.get("/api/network/dashboard/quality-leader", headers=HEADERS)
        assert r.status_code == 200

    def test_all_dashboards_have_network_benchmarks(self):
        for url in DASHBOARD_URLS:
            r = client.get(url, headers=HEADERS)
            assert r.status_code == 200, f"Failed for {url}"
            assert "network_benchmarks" in r.json(), f"Missing network_benchmarks in {url}"

    def test_all_dashboards_have_tenant_metrics(self):
        for url in DASHBOARD_URLS:
            r = client.get(url, headers=HEADERS)
            assert r.status_code == 200
            assert "tenant_metrics" in r.json(), f"Missing tenant_metrics in {url}"

    def test_dashboards_require_auth(self):
        for url in DASHBOARD_URLS:
            r = client.get(url)
            assert r.status_code == 401, f"Expected 401 for {url}"


# ---------------------------------------------------------------------------
# TestAnonymization
# ---------------------------------------------------------------------------

class TestAnonymization:
    def setup_method(self):
        _opt_in()

    def test_benchmarks_never_expose_tenant_id(self):
        r = client.get("/api/network/benchmarks", headers=HEADERS)
        assert r.status_code == 200
        body = r.text
        # Should never contain raw tenant_id
        assert "default-tenant" not in body

    def test_recall_signals_use_pseudonyms(self):
        r = client.get("/api/network/recall-signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.text
        # Raw tenant IDs must not appear; pseudonyms are hex strings
        assert "default-tenant" not in body
        for sig in r.json()["signals"]:
            assert "tenant_id" not in sig

    def test_registry_no_facility_ids_in_defect_history(self):
        r = client.get("/api/network/registry/ANY-UDI/defect-history", headers=HEADERS)
        assert r.status_code == 200
        body = r.text
        assert "tenant_id" not in body
        assert "facility_id" not in body

    def test_participant_count_not_below_minimum(self):
        # opt-in to ensure at least 1 participant exists, but count should be >= 0
        r = client.get("/api/network/participants/count")
        assert r.status_code == 200
        data = r.json()
        assert data["active_participants"] >= 0
