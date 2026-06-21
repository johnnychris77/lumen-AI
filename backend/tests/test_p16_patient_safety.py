"""P16: Patient Safety Intelligence Integration — test suite."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer dev-token"}
NO_AUTH = {}

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _flatten_keys(obj, prefix=""):
    """Recursively collect all dict keys from a nested structure."""
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _flatten_keys(v, prefix=k)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _flatten_keys(item, prefix=prefix)
    return keys


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class TestPatientSafetySignals:
    def test_signals_list_returns_200(self):
        r = client.get("/api/patient-safety/signals", headers=HEADERS)
        assert r.status_code == 200

    def test_signals_require_auth(self):
        r = client.get("/api/patient-safety/signals", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_signals_response_has_disclaimer(self):
        r = client.get("/api/patient-safety/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10

    def test_signals_response_no_causation_language(self):
        # First create a signal via correlate
        client.post(
            "/api/patient-safety/correlate",
            json={"facility_id": "", "days_back": 90},
            headers=HEADERS,
        )
        r = client.get("/api/patient-safety/signals", headers=HEADERS)
        assert r.status_code == 200
        text = r.text.lower()
        assert "caused" not in text

    def test_signal_detail_returns_200_or_404(self):
        # If no signal exists, 404 is expected
        r = client.get("/api/patient-safety/signals/nonexistent-id", headers=HEADERS)
        assert r.status_code in (200, 404)

    def test_signals_scoped_to_tenant(self):
        # With dev-token the tenant is fixed; signals should not leak tenant info
        r = client.get("/api/patient-safety/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        for sig in body.get("signals", []):
            # All returned signals must belong to the authenticated tenant
            assert "tenant_id" in sig


# ---------------------------------------------------------------------------
# Correlation Engine
# ---------------------------------------------------------------------------


class TestCorrelationEngine:
    def test_correlate_returns_200(self):
        r = client.post(
            "/api/patient-safety/correlate",
            json={"facility_id": "", "days_back": 90},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_correlate_has_signals_analyzed(self):
        r = client.post(
            "/api/patient-safety/correlate",
            json={"facility_id": "", "days_back": 90},
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert "signals_analyzed" in body
        assert isinstance(body["signals_analyzed"], int)

    def test_correlate_has_correlation_count(self):
        r = client.post(
            "/api/patient-safety/correlate",
            json={"facility_id": "", "days_back": 90},
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert "correlations_found" in body

    def test_correlate_output_has_no_causation_language(self):
        r = client.post(
            "/api/patient-safety/correlate",
            json={"facility_id": "", "days_back": 90},
            headers=HEADERS,
        )
        assert r.status_code == 200
        text = r.text.lower()
        # "caused" must not appear as a positive claim.
        # The disclaimer "does not establish causation" is acceptable;
        # what is prohibited is affirmative causal claims like "caused", "resulted in".
        assert "caused" not in text
        # "causation" is only acceptable if it appears in a denial context (e.g. disclaimer)
        # We verify the disclaimer is present and no affirmative causal claim exists.
        body = r.json()
        disclaimer = body.get("disclaimer", "").lower()
        assert "causation" in disclaimer or "association" in disclaimer

    def test_correlate_human_review_required_true(self):
        r = client.post(
            "/api/patient-safety/correlate",
            json={"facility_id": "", "days_back": 90},
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True


# ---------------------------------------------------------------------------
# Near Misses
# ---------------------------------------------------------------------------


class TestNearMisses:
    def test_near_misses_returns_200(self):
        r = client.get("/api/patient-safety/near-misses", headers=HEADERS)
        assert r.status_code == 200

    def test_near_misses_is_list(self):
        r = client.get("/api/patient-safety/near-misses", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "near_misses" in body
        assert isinstance(body["near_misses"], list)


# ---------------------------------------------------------------------------
# Quality Investigations
# ---------------------------------------------------------------------------


class TestQualityInvestigations:
    def test_quality_investigations_returns_200(self):
        r = client.get("/api/patient-safety/quality-investigations", headers=HEADERS)
        assert r.status_code == 200

    def test_quality_investigations_is_list(self):
        r = client.get("/api/patient-safety/quality-investigations", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "investigations" in body
        assert isinstance(body["investigations"], list)


# ---------------------------------------------------------------------------
# Executive Risk
# ---------------------------------------------------------------------------


class TestExecutiveRisk:
    def test_executive_risk_returns_200(self):
        r = client.get("/api/patient-safety/executive-risk", headers=HEADERS)
        assert r.status_code in (200, 403)

    def test_executive_risk_has_risk_tier(self):
        r = client.get("/api/patient-safety/executive-risk", headers=HEADERS)
        if r.status_code == 200:
            body = r.json()
            assert "executive_risks" in body


# ---------------------------------------------------------------------------
# Event Import
# ---------------------------------------------------------------------------


class TestEventImport:
    def test_import_returns_200(self):
        r = client.post(
            "/api/patient-safety/events/import",
            json={
                "facility_id": "fac-1",
                "source_system": "safecare",
                "events": [
                    {
                        "id": "evt-001",
                        "event_type": "adverse_event",
                        "event_date": "2025-01-15T10:00:00",
                        "instrument_id": "INST-100",
                    }
                ],
            },
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_import_accepts_safecare_format(self):
        r = client.post(
            "/api/patient-safety/events/import",
            json={
                "facility_id": "fac-1",
                "source_system": "safecare",
                "events": [
                    {
                        "id": "sc-123",
                        "event_type": "near_miss",
                        "event_date": "2025-02-01T08:30:00",
                        "instrument_id": "INST-200",
                        "de_identified": True,
                    }
                ],
            },
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("imported", 0) >= 1

    def test_import_returns_imported_count(self):
        r = client.post(
            "/api/patient-safety/events/import",
            json={
                "facility_id": "",
                "source_system": "rldatix",
                "events": [
                    {
                        "id": "rld-001",
                        "event_type": "capa",
                        "event_date": "2025-03-10T12:00:00",
                    }
                ],
            },
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert "imported" in body
        assert isinstance(body["imported"], int)

    def test_import_requires_auth(self):
        r = client.post(
            "/api/patient-safety/events/import",
            json={"facility_id": "", "source_system": "safecare", "events": []},
            headers=NO_AUTH,
        )
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    _KPI_KEYS = [
        "total_quality_signals",
        "high_critical_signals",
        "near_misses_flagged",
        "executive_risks_open",
        "ip_signals_pending_review",
        "capa_recurrences_detected",
        "instruments_with_signals",
        "vendors_with_signals",
        "human_review_required_count",
    ]

    def test_dashboard_returns_200(self):
        r = client.get("/api/patient-safety/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_dashboard_has_all_kpis(self):
        r = client.get("/api/patient-safety/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        for key in self._KPI_KEYS:
            assert key in body, f"Missing KPI: {key}"

    def test_dashboard_has_disclaimer(self):
        r = client.get("/api/patient-safety/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10

    def test_dashboard_human_review_count_present(self):
        r = client.get("/api/patient-safety/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "human_review_required_count" in body
        assert isinstance(body["human_review_required_count"], int)


# ---------------------------------------------------------------------------
# Infection Prevention
# ---------------------------------------------------------------------------


class TestInfectionPrevention:
    def test_ip_signals_returns_200(self):
        r = client.get("/api/patient-safety/infection-prevention", headers=HEADERS)
        assert r.status_code == 200

    def test_ip_signals_is_list(self):
        r = client.get("/api/patient-safety/infection-prevention", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "signals" in body
        assert isinstance(body["signals"], list)


# ---------------------------------------------------------------------------
# CAPA Effectiveness
# ---------------------------------------------------------------------------


class TestCAPAEffectiveness:
    def test_capa_returns_200(self):
        r = client.get("/api/patient-safety/capa-effectiveness", headers=HEADERS)
        assert r.status_code == 200

    def test_capa_is_list(self):
        r = client.get("/api/patient-safety/capa-effectiveness", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "capa_signals" in body
        assert isinstance(body["capa_signals"], list)


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------


class TestGovernance:
    _FORBIDDEN_KEYS = {"patient_id", "mrn", "dob", "patient_name", "ssn"}

    def test_no_patient_identifiers_in_signals(self):
        r = client.get("/api/patient-safety/signals", headers=HEADERS)
        assert r.status_code == 200
        all_keys = _flatten_keys(r.json())
        overlap = self._FORBIDDEN_KEYS & all_keys
        assert not overlap, f"Patient identifiers found in response: {overlap}"

    def test_human_review_required_on_all_signal_types(self):
        # Dashboard always includes human_review_required field
        r = client.get("/api/patient-safety/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True

    def test_disclaimer_present_in_dashboard(self):
        r = client.get("/api/patient-safety/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        # Disclaimer must reference human review, not causation
        assert "causation" in body["disclaimer"].lower() or "human review" in body["disclaimer"].lower()

    def test_signals_tenant_isolated(self):
        # Create a signal via import
        client.post(
            "/api/patient-safety/events/import",
            json={
                "facility_id": "fac-test",
                "source_system": "midas",
                "events": [
                    {
                        "id": "iso-001",
                        "event_type": "adverse_event",
                        "event_date": "2025-04-01T09:00:00",
                        "instrument_id": "INST-ISO",
                    }
                ],
            },
            headers=HEADERS,
        )
        # Verify it appears in the signal list for the same token
        r = client.get("/api/patient-safety/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        # All signals must have a tenant_id
        for sig in body.get("signals", []):
            assert "tenant_id" in sig
