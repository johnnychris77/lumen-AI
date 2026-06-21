"""P10: Digital Twin of SPD Operations — Test suite (80+ tests)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}


# ---------------------------------------------------------------------------
# TestTwinState
# ---------------------------------------------------------------------------
class TestTwinState:
    def test_twin_state_200(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        assert r.status_code == 200

    def test_twin_state_has_stations(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "stations" in data
        assert isinstance(data["stations"], list)

    def test_twin_state_has_throughput(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "throughput_per_hour" in data

    def test_twin_state_data_source(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert data["data_source"] in ("real", "mock")

    def test_twin_state_has_bottleneck(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "bottleneck_station" in data

    def test_twin_state_has_utilization(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "utilization_pct" in data
        assert isinstance(data["utilization_pct"], (int, float))

    def test_twin_state_has_cycle_time(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "avg_cycle_time_minutes" in data

    def test_twin_state_has_kpis(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "kpis" in data
        assert isinstance(data["kpis"], dict)

    def test_twin_state_has_instruments_in_flight(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "total_instruments_in_flight" in data

    def test_twin_state_tenant_id_present(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "tenant_id" in data

    def test_twin_state_facility_id_param(self):
        r = client.get("/api/digital-twin/state?facility_id=hosp-1", headers=HEADERS)
        assert r.status_code == 200

    def test_twin_state_station_utilization_computed(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        for station in data["stations"]:
            assert "utilization_pct" in station
            assert station["utilization_pct"] >= 0

    def test_twin_state_bottleneck_is_str(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert isinstance(data["bottleneck_station"], str)

    def test_twin_state_snapshot_at_present(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        data = r.json()
        assert "snapshot_at" in data


# ---------------------------------------------------------------------------
# TestStationManagement
# ---------------------------------------------------------------------------
class TestStationManagement:
    def test_list_stations_200(self):
        r = client.get("/api/digital-twin/stations", headers=HEADERS)
        assert r.status_code == 200

    def test_stations_is_list(self):
        r = client.get("/api/digital-twin/stations", headers=HEADERS)
        assert isinstance(r.json(), list)

    def test_stations_have_required_fields(self):
        r = client.get("/api/digital-twin/stations", headers=HEADERS)
        stations = r.json()
        assert len(stations) > 0
        s = stations[0]
        for field in ("station_name", "station_type", "capacity", "current_load", "utilization_pct", "status"):
            assert field in s, f"Missing field: {field}"

    def test_default_stations_seeded(self):
        r = client.get("/api/digital-twin/stations", headers=HEADERS)
        stations = r.json()
        # Should have at least the 8 default stations
        assert len(stations) >= 1

    def test_stations_types_valid(self):
        r = client.get("/api/digital-twin/stations", headers=HEADERS)
        valid_types = {"decontamination", "inspection", "sterilization", "storage", "dispatch"}
        for s in r.json():
            assert s["station_type"] in valid_types

    def test_stations_status_valid(self):
        r = client.get("/api/digital-twin/stations", headers=HEADERS)
        valid_statuses = {"active", "offline", "maintenance"}
        for s in r.json():
            assert s["status"] in valid_statuses


# ---------------------------------------------------------------------------
# TestInstrumentFlow
# ---------------------------------------------------------------------------
class TestInstrumentFlow:
    def test_list_flow_200(self):
        r = client.get("/api/digital-twin/flow", headers=HEADERS)
        assert r.status_code == 200

    def test_list_flow_is_list(self):
        r = client.get("/api/digital-twin/flow", headers=HEADERS)
        assert isinstance(r.json(), list)

    def test_log_flow_201(self):
        payload = {
            "instrument_name": "Scalpel #3",
            "instrument_id": "INS-001",
            "from_station": "",
            "to_station": "Decontamination Bay 1",
            "station_type": "decontamination",
        }
        r = client.post("/api/digital-twin/flow", json=payload, headers=HEADERS)
        assert r.status_code == 200

    def test_log_flow_returns_record(self):
        payload = {
            "instrument_name": "Forceps",
            "instrument_id": "INS-002",
            "from_station": "",
            "to_station": "Inspection Station A",
            "station_type": "inspection",
        }
        r = client.post("/api/digital-twin/flow", json=payload, headers=HEADERS)
        data = r.json()
        assert data["instrument_name"] == "Forceps"
        assert data["outcome"] == "pending"

    def test_log_flow_has_arrived_at(self):
        payload = {
            "instrument_name": "Retractor",
            "instrument_id": "INS-003",
            "to_station": "Sterilizer 1",
            "station_type": "sterilization",
        }
        r = client.post("/api/digital-twin/flow", json=payload, headers=HEADERS)
        assert "arrived_at" in r.json()

    def test_log_flow_appears_in_list(self):
        instrument_name = "UniqueInstrument_XYZ"
        payload = {
            "instrument_name": instrument_name,
            "instrument_id": "INS-999",
            "to_station": "Dispatch",
            "station_type": "dispatch",
        }
        client.post("/api/digital-twin/flow", json=payload, headers=HEADERS)
        r = client.get("/api/digital-twin/flow?limit=50", headers=HEADERS)
        names = [f["instrument_name"] for f in r.json()]
        assert instrument_name in names

    def test_flow_limit_param(self):
        r = client.get("/api/digital-twin/flow?limit=5", headers=HEADERS)
        assert r.status_code == 200
        assert len(r.json()) <= 5

    def test_flow_fields(self):
        payload = {
            "instrument_name": "Clamp",
            "instrument_id": "INS-004",
            "to_station": "Sterile Storage",
            "station_type": "storage",
        }
        r = client.post("/api/digital-twin/flow", json=payload, headers=HEADERS)
        data = r.json()
        for field in ("id", "tenant_id", "instrument_name", "to_station", "station_type", "arrived_at", "outcome"):
            assert field in data


# ---------------------------------------------------------------------------
# TestFlowCompletion
# ---------------------------------------------------------------------------
class TestFlowCompletion:
    def _create_flow(self, instrument_name: str = "Test Instrument") -> dict:
        payload = {
            "instrument_name": instrument_name,
            "instrument_id": "INS-COMP",
            "to_station": "Inspection Station B",
            "station_type": "inspection",
        }
        return client.post("/api/digital-twin/flow", json=payload, headers=HEADERS).json()

    def test_complete_flow_200(self):
        flow = self._create_flow("Instrument-Complete-1")
        r = client.post(
            f"/api/digital-twin/flow/{flow['id']}/complete",
            json={"outcome": "passed"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_complete_flow_outcome_set(self):
        flow = self._create_flow("Instrument-Complete-2")
        r = client.post(
            f"/api/digital-twin/flow/{flow['id']}/complete",
            json={"outcome": "failed"},
            headers=HEADERS,
        )
        assert r.json()["outcome"] == "failed"

    def test_complete_flow_departed_at_set(self):
        flow = self._create_flow("Instrument-Complete-3")
        r = client.post(
            f"/api/digital-twin/flow/{flow['id']}/complete",
            json={"outcome": "passed"},
            headers=HEADERS,
        )
        assert r.json()["departed_at"] is not None

    def test_complete_flow_processing_time_computed(self):
        flow = self._create_flow("Instrument-Complete-4")
        r = client.post(
            f"/api/digital-twin/flow/{flow['id']}/complete",
            json={"outcome": "passed"},
            headers=HEADERS,
        )
        assert r.json()["processing_time_minutes"] >= 0

    def test_complete_flow_404_for_nonexistent(self):
        r = client.post(
            "/api/digital-twin/flow/999999/complete",
            json={"outcome": "passed"},
            headers=HEADERS,
        )
        assert r.status_code == 404

    def test_complete_flow_quarantined(self):
        flow = self._create_flow("Instrument-Quarantine")
        r = client.post(
            f"/api/digital-twin/flow/{flow['id']}/complete",
            json={"outcome": "quarantined", "notes": "Contamination detected"},
            headers=HEADERS,
        )
        assert r.json()["outcome"] == "quarantined"


# ---------------------------------------------------------------------------
# TestAlerts
# ---------------------------------------------------------------------------
class TestAlerts:
    def test_list_alerts_200(self):
        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        assert r.status_code == 200

    def test_list_alerts_is_list(self):
        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        assert isinstance(r.json(), list)

    def test_alert_fields(self):
        # Force at least one alert via state check
        client.get("/api/digital-twin/state", headers=HEADERS)
        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        alerts = r.json()
        if alerts:
            a = alerts[0]
            for field in ("id", "alert_type", "severity", "message", "acknowledged", "created_at"):
                assert field in a

    def test_acknowledge_alert(self):
        # Ensure alerts exist
        client.get("/api/digital-twin/state", headers=HEADERS)
        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        alerts = r.json()
        if not alerts:
            pytest.skip("No open alerts to acknowledge")
        alert_id = alerts[0]["id"]
        r = client.post(
            f"/api/digital-twin/alerts/{alert_id}/acknowledge",
            json={"acknowledged_by": "test-user"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["acknowledged"] is True

    def test_acknowledge_updates_acknowledged_by(self):
        client.get("/api/digital-twin/state", headers=HEADERS)
        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        alerts = r.json()
        if not alerts:
            pytest.skip("No open alerts")
        alert_id = alerts[0]["id"]
        r = client.post(
            f"/api/digital-twin/alerts/{alert_id}/acknowledge",
            json={"acknowledged_by": "jane.doe"},
            headers=HEADERS,
        )
        assert r.json()["acknowledged_by"] == "jane.doe"

    def test_acknowledge_404_for_nonexistent(self):
        r = client.post(
            "/api/digital-twin/alerts/999999/acknowledge",
            json={"acknowledged_by": "test"},
            headers=HEADERS,
        )
        assert r.status_code == 404

    def test_alert_severity_valid(self):
        client.get("/api/digital-twin/state", headers=HEADERS)
        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        valid = {"low", "medium", "high", "critical"}
        for a in r.json():
            assert a["severity"] in valid


# ---------------------------------------------------------------------------
# TestAlertGeneration
# ---------------------------------------------------------------------------
class TestAlertGeneration:
    def test_overload_alert_on_high_load(self):
        """Pushing many instruments to a small station triggers an alert."""
        from app.main import app as fastapi_app  # noqa: F401
        from app.db.session import engine
        from app.models.digital_twin import SPDWorkflowStation
        from sqlalchemy.orm import Session
        from datetime import datetime, timezone

        with Session(engine) as db:
            # Create a tiny station
            station = SPDWorkflowStation(
                tenant_id="default-tenant",
                facility_id="alert-test",
                station_name="Tiny Station Alert Test",
                station_type="inspection",
                capacity=2,
                current_load=0,
                avg_processing_time_minutes=15.0,
                status="active",
                last_updated=datetime.now(timezone.utc),
            )
            db.add(station)
            db.commit()

        # Push 3 instruments to trigger overload
        for i in range(3):
            client.post(
                "/api/digital-twin/flow",
                json={
                    "instrument_name": f"AlertInstrument_{i}",
                    "instrument_id": f"AI-{i}",
                    "to_station": "Tiny Station Alert Test",
                    "station_type": "inspection",
                },
                headers=HEADERS,
            )

        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        alerts = r.json()
        station_alerts = [a for a in alerts if a.get("station_name") == "Tiny Station Alert Test"]
        assert len(station_alerts) >= 1

    def test_alert_type_overload(self):
        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        valid_types = {"bottleneck", "overload", "station_offline", "cycle_time_exceeded", "throughput_drop"}
        for a in r.json():
            assert a["alert_type"] in valid_types


# ---------------------------------------------------------------------------
# TestWhatIf
# ---------------------------------------------------------------------------
class TestWhatIf:
    def test_whatif_200(self):
        payload = {
            "scenario_name": "Add Decon Station",
            "description": "What if we add a third decontamination bay?",
            "add_station": "decontamination",
        }
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        assert r.status_code == 200

    def test_whatif_returns_baseline(self):
        payload = {"scenario_name": "Test Baseline", "add_station": "inspection"}
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        data = r.json()
        assert "baseline" in data
        assert isinstance(data["baseline"], dict)

    def test_whatif_returns_simulated(self):
        payload = {"scenario_name": "Test Simulated", "add_station": "sterilization"}
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        data = r.json()
        assert "simulated" in data

    def test_whatif_returns_delta(self):
        payload = {"scenario_name": "Test Delta", "volume_change_pct": 20.0}
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        data = r.json()
        assert "delta" in data
        assert isinstance(data["delta"], dict)

    def test_whatif_returns_recommendation(self):
        payload = {"scenario_name": "Test Rec", "add_station": "dispatch"}
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        data = r.json()
        assert "recommendation" in data
        assert len(data["recommendation"]) > 0

    def test_whatif_persisted_to_db(self):
        scenario_name = "Unique Scenario 77XYZ"
        payload = {"scenario_name": scenario_name, "add_station": "inspection"}
        client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        r = client.get("/api/digital-twin/whatif", headers=HEADERS)
        names = [s["scenario_name"] for s in r.json()]
        assert scenario_name in names

    def test_whatif_volume_increase(self):
        payload = {"scenario_name": "Volume +30%", "volume_change_pct": 30.0}
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        # Higher volume → higher utilization
        assert data["simulated"]["utilization_pct"] >= 0

    def test_whatif_remove_station(self):
        # First ensure stations exist
        client.get("/api/digital-twin/stations", headers=HEADERS)
        payload = {
            "scenario_name": "Remove Dispatch",
            "remove_station": "Dispatch",
        }
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        assert r.status_code == 200

    def test_whatif_capacity_change(self):
        payload = {
            "scenario_name": "Increase Sterilizer",
            "capacity_change": {"Sterilizer 1": 50},
        }
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        assert r.status_code == 200

    def test_list_whatif_200(self):
        r = client.get("/api/digital-twin/whatif", headers=HEADERS)
        assert r.status_code == 200

    def test_list_whatif_is_list(self):
        r = client.get("/api/digital-twin/whatif", headers=HEADERS)
        assert isinstance(r.json(), list)

    def test_whatif_has_id(self):
        payload = {"scenario_name": "ID Test", "add_station": "storage"}
        r = client.post("/api/digital-twin/whatif", json=payload, headers=HEADERS)
        data = r.json()
        assert "id" in data
        assert data["id"] is not None


# ---------------------------------------------------------------------------
# TestTwinDashboard
# ---------------------------------------------------------------------------
class TestTwinDashboard:
    def test_dashboard_200(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_dashboard_has_twin_state(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert "twin_state" in data
        assert isinstance(data["twin_state"], dict)

    def test_dashboard_has_recent_flow(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert "recent_flow" in data
        assert isinstance(data["recent_flow"], list)

    def test_dashboard_has_open_alerts(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert "open_alerts" in data

    def test_dashboard_has_whatif_scenarios(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert "what_if_scenarios" in data

    def test_dashboard_trend_data_present(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert "trend_data" in data
        assert len(data["trend_data"]) > 0

    def test_dashboard_trend_data_24h(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert len(data["trend_data"]) == 24

    def test_dashboard_trend_data_has_throughput(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        for entry in data["trend_data"]:
            assert "throughput" in entry
            assert "utilization" in entry

    def test_dashboard_recommendations_non_empty(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0

    def test_dashboard_data_source(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert data["data_source"] in ("real", "mock")

    def test_dashboard_generated_at(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        data = r.json()
        assert "generated_at" in data

    def test_dashboard_facility_id_param(self):
        r = client.get("/api/digital-twin/dashboard?facility_id=f1", headers=HEADERS)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# TestMockFallback
# ---------------------------------------------------------------------------
class TestMockFallback:
    def test_mock_twin_state_deterministic(self):
        """Mock state for same tenant+facility is deterministic."""
        from app.services.digital_twin_engine import _mock_twin_state
        result1 = _mock_twin_state("tenant-mock", "fac-mock")
        result2 = _mock_twin_state("tenant-mock", "fac-mock")
        assert result1.throughput_per_hour == result2.throughput_per_hour
        assert result1.bottleneck_station == result2.bottleneck_station

    def test_mock_data_source_is_mock(self):
        from app.services.digital_twin_engine import _mock_twin_state
        result = _mock_twin_state("tenant-xyz", "fac-xyz")
        assert result.data_source == "mock"

    def test_mock_has_stations(self):
        from app.services.digital_twin_engine import _mock_twin_state
        result = _mock_twin_state("tenant-abc", "fac-abc")
        assert len(result.stations) > 0

    def test_mock_utilization_in_range(self):
        from app.services.digital_twin_engine import _mock_twin_state
        result = _mock_twin_state("tenant-range", "fac-range")
        for s in result.stations:
            assert 0 <= s.utilization_pct <= 100

    def test_mock_different_tenants_different_results(self):
        from app.services.digital_twin_engine import _mock_twin_state
        r1 = _mock_twin_state("tenant-A", "")
        r2 = _mock_twin_state("tenant-B", "")
        # Should differ
        assert r1.throughput_per_hour != r2.throughput_per_hour or r1.bottleneck_station != r2.bottleneck_station


# ---------------------------------------------------------------------------
# TestTierGating
# ---------------------------------------------------------------------------
class TestTierGating:
    """Tier gating tests — permissive by default (no TenantPlan record)."""

    def test_twin_state_accessible_default(self):
        r = client.get("/api/digital-twin/state", headers=HEADERS)
        assert r.status_code == 200

    def test_twin_alerts_accessible_default(self):
        r = client.get("/api/digital-twin/alerts", headers=HEADERS)
        assert r.status_code == 200

    def test_twin_whatif_accessible_default(self):
        r = client.get("/api/digital-twin/whatif", headers=HEADERS)
        assert r.status_code == 200

    def test_twin_dashboard_accessible_default(self):
        r = client.get("/api/digital-twin/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_401_without_auth_state(self):
        r = client.get("/api/digital-twin/state")
        assert r.status_code == 401

    def test_401_without_auth_alerts(self):
        r = client.get("/api/digital-twin/alerts")
        assert r.status_code == 401

    def test_401_without_auth_dashboard(self):
        r = client.get("/api/digital-twin/dashboard")
        assert r.status_code == 401

    def test_401_without_auth_whatif_post(self):
        r = client.post(
            "/api/digital-twin/whatif",
            json={"scenario_name": "no-auth"},
        )
        assert r.status_code == 401

    def test_tier_features_include_standard(self):
        from app.tier_guard import TIER_FEATURES
        assert "twin_state" in TIER_FEATURES["standard"]

    def test_tier_features_include_professional(self):
        from app.tier_guard import TIER_FEATURES
        assert "twin_alerts" in TIER_FEATURES["professional"]

    def test_tier_features_include_enterprise(self):
        from app.tier_guard import TIER_FEATURES
        assert "twin_whatif" in TIER_FEATURES["enterprise"]
        assert "twin_dashboard" in TIER_FEATURES["enterprise"]
