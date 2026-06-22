"""P25: Global Surgical Quality Infrastructure & Industry Utility Platform — test suite."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer dev-token"}
NO_AUTH = {}
TS = str(int(time.time() * 1000))

client = TestClient(app, raise_server_exceptions=True)

_CAUSATION = ["causes", "caused by", "proves", "confirms causation", "establishes causation"]


def _has_causation(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in _CAUSATION)


def _flatten(obj) -> str:
    if isinstance(obj, dict):
        return " ".join(_flatten(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_flatten(v) for v in obj)
    return str(obj) if obj is not None else ""


# ---------------------------------------------------------------------------
# Phase 1: Instrument Digital Identity
# ---------------------------------------------------------------------------


class TestInstrumentIdentity:
    _PAYLOAD = {
        "instrument_category": "flexible_scopes",
        "manufacturer_name": "Scope Co",
        "model_name": f"FlexModel-{TS}",
        "serial_number": f"SN-{TS}",
        "udi": f"00889290{TS[-8:]}",
    }

    def test_list_returns_200(self):
        r = client.get("/api/infrastructure/instruments", headers=HEADERS)
        assert r.status_code == 200

    def test_list_requires_auth(self):
        r = client.get("/api/infrastructure/instruments", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_list_returns_instruments(self):
        r = client.get("/api/infrastructure/instruments", headers=HEADERS)
        assert isinstance(r.json().get("instruments"), list)
        assert len(r.json()["instruments"]) > 0

    def test_list_has_disclaimer(self):
        r = client.get("/api/infrastructure/instruments", headers=HEADERS)
        assert "disclaimer" in r.json()

    def test_filter_by_category(self):
        r = client.get("/api/infrastructure/instruments?category=flexible_scopes", headers=HEADERS)
        assert r.status_code == 200

    def test_filter_by_status(self):
        r = client.get("/api/infrastructure/instruments?status=active", headers=HEADERS)
        assert r.status_code == 200

    def test_register_returns_200(self):
        r = client.post("/api/infrastructure/instruments", json=self._PAYLOAD, headers=HEADERS)
        assert r.status_code == 200

    def test_register_returns_id(self):
        r = client.post("/api/infrastructure/instruments", json=self._PAYLOAD, headers=HEADERS)
        assert "instrument_id" in r.json()

    def test_register_udi_verified(self):
        r = client.post("/api/infrastructure/instruments", json=self._PAYLOAD, headers=HEADERS)
        assert r.json()["identity_verified"] is True
        assert r.json()["verification_method"] == "udi"

    def test_register_requires_identifier(self):
        payload = {"instrument_category": "flexible_scopes", "manufacturer_name": "Co"}
        r = client.post("/api/infrastructure/instruments", json=payload, headers=HEADERS)
        assert r.status_code == 422
        assert r.json()["detail"]["error"] == "no_identifier"

    def test_register_requires_auth(self):
        r = client.post("/api/infrastructure/instruments", json=self._PAYLOAD, headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_keydot_verification_method(self):
        payload = {
            "instrument_category": "orthopaedic_instruments",
            "keydot_id": f"KD-{TS}",
        }
        r = client.post("/api/infrastructure/instruments", json=payload, headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["verification_method"] == "keydot"

    def test_get_single_instrument(self):
        r = client.post("/api/infrastructure/instruments", json=self._PAYLOAD, headers=HEADERS)
        iid = r.json()["instrument_id"]
        r2 = client.get(f"/api/infrastructure/instruments/{iid}", headers=HEADERS)
        assert r2.status_code == 200
        assert r2.json()["instrument"]["id"] == iid

    def test_get_unknown_is_404(self):
        r = client.get("/api/infrastructure/instruments/999999", headers=HEADERS)
        assert r.status_code == 404

    def test_lifecycle_update(self):
        r = client.post("/api/infrastructure/instruments", json=self._PAYLOAD, headers=HEADERS)
        iid = r.json()["instrument_id"]
        r2 = client.post(
            f"/api/infrastructure/instruments/{iid}/lifecycle?status=quarantined",
            headers=HEADERS,
        )
        assert r2.status_code == 200
        assert r2.json()["new_status"] == "quarantined"
        assert r2.json()["human_review_required"] is True

    def test_lifecycle_invalid_status(self):
        r = client.post("/api/infrastructure/instruments", json=self._PAYLOAD, headers=HEADERS)
        iid = r.json()["instrument_id"]
        r2 = client.post(
            f"/api/infrastructure/instruments/{iid}/lifecycle?status=vaporized",
            headers=HEADERS,
        )
        assert r2.status_code == 422

    def test_lifecycle_unknown_instrument(self):
        r = client.post(
            "/api/infrastructure/instruments/999999/lifecycle?status=retired",
            headers=HEADERS,
        )
        assert r.status_code == 404

    def test_instruments_no_patient_identifiers(self):
        r = client.get("/api/infrastructure/instruments", headers=HEADERS)
        keys = set()
        for inst in r.json().get("instruments", []):
            keys |= set(inst.keys())
        forbidden = {"patient_id", "mrn", "dob", "patient_name"}
        assert not (keys & forbidden)


# ---------------------------------------------------------------------------
# Phase 2: Surgical Readiness Index
# ---------------------------------------------------------------------------


class TestSurgicalReadiness:
    def test_facility_readiness_returns_200(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "facility", "reference_id": "main"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_readiness_has_score(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "facility"},
            headers=HEADERS,
        )
        body = r.json()
        assert "readiness_score" in body
        assert 0 <= body["readiness_score"] <= 100

    def test_readiness_has_tier(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "facility"},
            headers=HEADERS,
        )
        assert r.json().get("readiness_tier") in ("green", "yellow", "amber", "red")

    def test_readiness_tray_scope(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "tray", "reference_id": "tray-001"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_readiness_enterprise_scope(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "enterprise"},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_readiness_invalid_scope(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "planet"},
            headers=HEADERS,
        )
        assert r.status_code == 422

    def test_readiness_human_review_required(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "facility"},
            headers=HEADERS,
        )
        assert r.json().get("human_review_required") is True

    def test_readiness_has_components(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "facility"},
            headers=HEADERS,
        )
        body = r.json()
        for key in ("instrument_availability", "contamination_status",
                    "inspection_compliance", "capa_backlog_health",
                    "sterilization_cycle_compliance"):
            assert key in body

    def test_readiness_has_disclaimer(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "facility"},
            headers=HEADERS,
        )
        assert "disclaimer" in r.json()

    def test_readiness_requires_auth(self):
        r = client.post(
            "/api/infrastructure/readiness",
            json={"scope": "facility"},
            headers=NO_AUTH,
        )
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Phase 3: Instrument Passport
# ---------------------------------------------------------------------------


class TestInstrumentPassport:
    def _create_instrument(self) -> int:
        r = client.post(
            "/api/infrastructure/instruments",
            json={"instrument_category": "flexible_scopes", "udi": f"UDI-{TS}-{id(self)}"},
            headers=HEADERS,
        )
        return r.json()["instrument_id"]

    def test_get_passport_returns_200(self):
        iid = self._create_instrument()
        r = client.get(f"/api/infrastructure/instruments/{iid}/passport", headers=HEADERS)
        assert r.status_code == 200

    def test_passport_has_instrument(self):
        iid = self._create_instrument()
        r = client.get(f"/api/infrastructure/instruments/{iid}/passport", headers=HEADERS)
        assert "instrument" in r.json()

    def test_passport_has_events_list(self):
        iid = self._create_instrument()
        r = client.get(f"/api/infrastructure/instruments/{iid}/passport", headers=HEADERS)
        assert isinstance(r.json().get("passport_events"), list)

    def test_add_inspection_event(self):
        iid = self._create_instrument()
        r = client.post(
            f"/api/infrastructure/instruments/{iid}/passport",
            json={
                "instrument_id": iid,
                "event_type": "inspection",
                "event_detail": "visual_pass",
                "outcome": "pass",
            },
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["event_type"] == "inspection"

    def test_add_sterilization_increments_cycle(self):
        iid = self._create_instrument()
        r = client.post(
            f"/api/infrastructure/instruments/{iid}/passport",
            json={"instrument_id": iid, "event_type": "sterilization", "outcome": "pass"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        cycle = r.json()["cycle_count"]
        assert isinstance(cycle, int)
        assert cycle >= 1

    def test_add_quarantine_event_triggers_review(self):
        iid = self._create_instrument()
        r = client.post(
            f"/api/infrastructure/instruments/{iid}/passport",
            json={"instrument_id": iid, "event_type": "quarantine", "outcome": "quarantined"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["human_review_required"] is True

    def test_passport_invalid_event_type(self):
        iid = self._create_instrument()
        r = client.post(
            f"/api/infrastructure/instruments/{iid}/passport",
            json={"instrument_id": iid, "event_type": "teleportation"},
            headers=HEADERS,
        )
        assert r.status_code == 422

    def test_passport_unknown_instrument_is_404(self):
        r = client.post(
            "/api/infrastructure/instruments/999999/passport",
            json={"instrument_id": 999999, "event_type": "inspection"},
            headers=HEADERS,
        )
        assert r.status_code == 404

    def test_passport_events_appear_in_history(self):
        iid = self._create_instrument()
        client.post(
            f"/api/infrastructure/instruments/{iid}/passport",
            json={"instrument_id": iid, "event_type": "maintenance", "outcome": "completed"},
            headers=HEADERS,
        )
        r = client.get(f"/api/infrastructure/instruments/{iid}/passport", headers=HEADERS)
        events = r.json()["passport_events"]
        assert any(e["event_type"] == "maintenance" for e in events)

    def test_passport_requires_auth(self):
        iid = self._create_instrument()
        r = client.get(f"/api/infrastructure/instruments/{iid}/passport", headers=NO_AUTH)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Phase 4: Global Quality Registry
# ---------------------------------------------------------------------------


class TestQualityRegistry:
    def test_returns_200(self):
        r = client.get("/api/infrastructure/quality-registry", headers=HEADERS)
        assert r.status_code == 200

    def test_requires_auth(self):
        r = client.get("/api/infrastructure/quality-registry", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_returns_entries(self):
        r = client.get("/api/infrastructure/quality-registry", headers=HEADERS)
        assert isinstance(r.json().get("entries"), list)
        assert len(r.json()["entries"]) > 0

    def test_registry_types_covered(self):
        r = client.get("/api/infrastructure/quality-registry", headers=HEADERS)
        types = {e.get("registry_type") for e in r.json()["entries"]}
        assert {"contamination", "defect", "reliability", "baseline"} <= types

    def test_human_review_required(self):
        r = client.get("/api/infrastructure/quality-registry", headers=HEADERS)
        assert r.json().get("human_review_required") is True

    def test_has_disclaimer(self):
        r = client.get("/api/infrastructure/quality-registry", headers=HEADERS)
        assert "disclaimer" in r.json()
        for entry in r.json()["entries"]:
            assert "disclaimer" in entry

    def test_filter_by_type(self):
        r = client.get("/api/infrastructure/quality-registry?registry_type=contamination", headers=HEADERS)
        assert r.status_code == 200

    def test_k_anonymity_verified(self):
        r = client.get("/api/infrastructure/quality-registry", headers=HEADERS)
        for entry in r.json()["entries"]:
            assert entry.get("contributing_facilities", 0) >= 5

    def test_no_causation_in_registry(self):
        r = client.get("/api/infrastructure/quality-registry", headers=HEADERS)
        text = _flatten(r.json().get("entries", []))
        assert not _has_causation(text)


# ---------------------------------------------------------------------------
# Phase 5: Industry Utility APIs
# ---------------------------------------------------------------------------


class TestAPICredentials:
    _PAYLOAD = {
        "consumer_type": "researcher",
        "requested_scopes": ["registry.read", "forecasts.read"],
    }

    def test_list_returns_200(self):
        r = client.get("/api/infrastructure/api-credentials", headers=HEADERS)
        assert r.status_code == 200

    def test_list_requires_auth(self):
        r = client.get("/api/infrastructure/api-credentials", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_list_does_not_expose_key_hash(self):
        r = client.get("/api/infrastructure/api-credentials", headers=HEADERS)
        for cred in r.json().get("credentials", []):
            assert "api_key_hash" not in cred

    def test_issue_returns_200(self):
        r = client.post("/api/infrastructure/api-credentials", json=self._PAYLOAD, headers=HEADERS)
        assert r.status_code == 200

    def test_issue_returns_raw_key_once(self):
        r = client.post("/api/infrastructure/api-credentials", json=self._PAYLOAD, headers=HEADERS)
        body = r.json()
        assert "api_key" in body
        assert len(body["api_key"]) >= 20

    def test_issue_has_important_notice(self):
        r = client.post("/api/infrastructure/api-credentials", json=self._PAYLOAD, headers=HEADERS)
        assert "important" in r.json()

    def test_issue_invalid_consumer_type(self):
        bad = {**self._PAYLOAD, "consumer_type": "hacker"}
        r = client.post("/api/infrastructure/api-credentials", json=bad, headers=HEADERS)
        assert r.status_code == 422

    def test_issue_requires_auth(self):
        r = client.post("/api/infrastructure/api-credentials", json=self._PAYLOAD, headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_revoke_credential(self):
        r = client.post("/api/infrastructure/api-credentials", json=self._PAYLOAD, headers=HEADERS)
        cid = r.json()["credential_id"]
        r2 = client.post(f"/api/infrastructure/api-credentials/{cid}/revoke", headers=HEADERS)
        assert r2.status_code == 200
        assert r2.json()["credential_status"] == "revoked"

    def test_revoke_unknown_is_404(self):
        r = client.post("/api/infrastructure/api-credentials/999999/revoke", headers=HEADERS)
        assert r.status_code == 404

    def test_revoke_double_is_conflict(self):
        r = client.post("/api/infrastructure/api-credentials", json=self._PAYLOAD, headers=HEADERS)
        cid = r.json()["credential_id"]
        client.post(f"/api/infrastructure/api-credentials/{cid}/revoke", headers=HEADERS)
        r2 = client.post(f"/api/infrastructure/api-credentials/{cid}/revoke", headers=HEADERS)
        assert r2.status_code == 409

    def test_anonymization_enforced(self):
        r = client.post("/api/infrastructure/api-credentials", json=self._PAYLOAD, headers=HEADERS)
        assert r.json()["anonymization_enforced"] is True


# ---------------------------------------------------------------------------
# Phase 6: Predictive Infrastructure
# ---------------------------------------------------------------------------


class TestForecasts:
    def test_returns_200(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        assert r.status_code == 200

    def test_requires_auth(self):
        r = client.get("/api/infrastructure/forecasts", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_returns_forecasts(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        assert isinstance(r.json().get("forecasts"), list)
        assert len(r.json()["forecasts"]) > 0

    def test_forecast_types_covered(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        types = {f.get("forecast_type") for f in r.json()["forecasts"]}
        expected = {"contamination", "failure", "compliance", "workforce_impact"}
        assert expected <= types

    def test_human_review_required(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        assert r.json().get("human_review_required") is True

    def test_has_disclaimer(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        assert "disclaimer" in r.json()
        for f in r.json()["forecasts"]:
            assert "disclaimer" in f

    def test_filter_by_type(self):
        r = client.get("/api/infrastructure/forecasts?forecast_type=contamination", headers=HEADERS)
        assert r.status_code == 200

    def test_forecast_has_confidence(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        for f in r.json()["forecasts"]:
            assert "confidence_score" in f
            assert 0 <= f["confidence_score"] <= 1

    def test_forecast_has_intervals(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        for f in r.json()["forecasts"]:
            assert "confidence_interval_low" in f
            assert "confidence_interval_high" in f

    def test_no_causation_in_forecasts(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        text = _flatten(r.json().get("forecasts", []))
        assert not _has_causation(text)

    def test_forecast_has_recommended_actions(self):
        r = client.get("/api/infrastructure/forecasts", headers=HEADERS)
        for f in r.json()["forecasts"]:
            assert "recommended_actions" in f


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    _KPI_KEYS = [
        "total_instruments",
        "active_instruments",
        "quarantined_instruments",
        "quality_registry_entries",
        "active_forecasts",
        "facility_readiness_score",
        "facility_readiness_tier",
    ]

    def test_returns_200(self):
        r = client.get("/api/infrastructure/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_has_all_kpis(self):
        r = client.get("/api/infrastructure/dashboard", headers=HEADERS)
        body = r.json()
        for key in self._KPI_KEYS:
            assert key in body, f"Missing KPI: {key}"

    def test_has_disclaimer(self):
        r = client.get("/api/infrastructure/dashboard", headers=HEADERS)
        assert "disclaimer" in r.json()

    def test_human_review_required(self):
        r = client.get("/api/infrastructure/dashboard", headers=HEADERS)
        assert r.json().get("human_review_required") is True

    def test_requires_auth(self):
        r = client.get("/api/infrastructure/dashboard", headers=NO_AUTH)
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Public Platform Stats
# ---------------------------------------------------------------------------


class TestPlatformStats:
    def test_returns_200_no_auth(self):
        r = client.get("/api/infrastructure/platform-stats")
        assert r.status_code == 200

    def test_has_registered_instruments(self):
        r = client.get("/api/infrastructure/platform-stats")
        body = r.json()
        assert "registered_instruments" in body
        assert isinstance(body["registered_instruments"], int)

    def test_has_disclaimer(self):
        r = client.get("/api/infrastructure/platform-stats")
        assert "disclaimer" in r.json()


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------


class TestGovernance:
    def test_disclaimer_on_all_auth_endpoints(self):
        endpoints = [
            "/api/infrastructure/instruments",
            "/api/infrastructure/quality-registry",
            "/api/infrastructure/forecasts",
            "/api/infrastructure/dashboard",
            "/api/infrastructure/api-credentials",
        ]
        for ep in endpoints:
            r = client.get(ep, headers=HEADERS)
            assert r.status_code == 200, f"{ep} → {r.status_code}"
            assert "disclaimer" in r.json(), f"No disclaimer in {ep}"

    def test_no_causation_across_endpoints(self):
        endpoints = [
            "/api/infrastructure/instruments",
            "/api/infrastructure/quality-registry",
            "/api/infrastructure/forecasts",
        ]
        for ep in endpoints:
            r = client.get(ep, headers=HEADERS)
            text = _flatten(r.json())
            assert not _has_causation(text), f"Causation language found in {ep}"

    def test_no_patient_identifiers_in_instruments(self):
        r = client.get("/api/infrastructure/instruments", headers=HEADERS)
        forbidden = {"patient_id", "mrn", "dob", "ssn", "patient_name"}
        keys: set = set()
        for inst in r.json().get("instruments", []):
            keys |= set(inst.keys())
        assert not (keys & forbidden)
