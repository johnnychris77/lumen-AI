"""P22: Healthcare Digital Quality Twin — test suite."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer dev-token"}
NO_AUTH = {}

client = TestClient(app, raise_server_exceptions=True)

_FORBIDDEN_PATIENT_KEYS = {"patient_id", "mrn", "dob", "ssn", "patient_name"}


def _flatten_text(obj) -> str:
    """Recursively stringify all values in a nested structure."""
    if isinstance(obj, dict):
        return " ".join(_flatten_text(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_flatten_text(v) for v in obj)
    return str(obj) if obj is not None else ""


def _flatten_keys(obj) -> set:
    """Recursively collect all dict keys."""
    keys: set = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _flatten_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _flatten_keys(item)
    return keys


# ---------------------------------------------------------------------------
# Twin State
# ---------------------------------------------------------------------------


class TestTwinState:
    def test_state_returns_200(self):
        r = client.get("/api/quality-twin/state", headers=HEADERS)
        assert r.status_code == 200

    def test_state_requires_auth(self):
        r = client.get("/api/quality-twin/state", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_state_has_overall_quality_score(self):
        r = client.get("/api/quality-twin/state", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        state = body.get("state", body)
        assert "overall_quality_score" in state
        assert isinstance(state["overall_quality_score"], (int, float))

    def test_state_has_human_review_required(self):
        r = client.get("/api/quality-twin/state", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True

    def test_state_has_disclaimer(self):
        r = client.get("/api/quality-twin/state", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10

    def test_state_has_trend_direction(self):
        r = client.get("/api/quality-twin/state", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        state = body.get("state", body)
        assert "trend_direction" in state
        assert state["trend_direction"] in ("improving", "stable", "declining")


# ---------------------------------------------------------------------------
# Forecasts
# ---------------------------------------------------------------------------


class TestForecasts:
    def test_forecasts_returns_200(self):
        r = client.get("/api/quality-twin/forecasts", headers=HEADERS)
        assert r.status_code == 200

    def test_forecasts_is_list(self):
        r = client.get("/api/quality-twin/forecasts", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body.get("forecasts"), list)

    def test_forecasts_has_30_60_90_horizons(self):
        r = client.get("/api/quality-twin/forecasts", headers=HEADERS)
        assert r.status_code == 200
        forecasts = r.json()["forecasts"]
        horizons = {f["forecast_horizon_days"] for f in forecasts}
        assert 30 in horizons
        assert 60 in horizons
        assert 90 in horizons

    def test_forecasts_human_review_required(self):
        r = client.get("/api/quality-twin/forecasts", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True
        for f in body["forecasts"]:
            assert f.get("human_review_required") is True

    def test_forecasts_no_causation_language(self):
        r = client.get("/api/quality-twin/forecasts", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        # Disclaimer should explicitly state it does NOT establish causation
        disclaimer_text = " ".join(
            f.get("disclaimer", "") for f in body["forecasts"]
        ).lower()
        assert "does not establish causation" in disclaimer_text


# ---------------------------------------------------------------------------
# Scenario Simulation
# ---------------------------------------------------------------------------


class TestScenarioSimulation:
    def _simulate(self, **kwargs):
        payload = {
            "scenario_type": "quality_improvement",
            "intervention_type": "vendor_change",
            "parameters": {"timeframe_days": 90},
        }
        payload.update(kwargs)
        return client.post("/api/quality-twin/simulate", json=payload, headers=HEADERS)

    def test_simulate_returns_200(self):
        r = self._simulate()
        assert r.status_code == 200

    def test_simulate_has_projected_quality_delta(self):
        r = self._simulate()
        assert r.status_code == 200
        sim = r.json()["simulation"]
        assert "projected_quality_delta" in sim
        assert isinstance(sim["projected_quality_delta"], (int, float))

    def test_simulate_human_review_required_true(self):
        r = self._simulate()
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True
        assert body["simulation"].get("human_review_required") is True

    def test_simulate_has_disclaimer(self):
        r = self._simulate()
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        sim = body["simulation"]
        assert "disclaimer" in sim
        assert len(sim["disclaimer"]) > 10

    def test_simulate_no_causation_language(self):
        r = self._simulate()
        assert r.status_code == 200
        sim = r.json()["simulation"]
        disclaimer = sim.get("disclaimer", "").lower()
        assert "does not establish causation" in disclaimer


# ---------------------------------------------------------------------------
# Interventions
# ---------------------------------------------------------------------------


class TestInterventions:
    def test_interventions_returns_200(self):
        r = client.get("/api/quality-twin/interventions", headers=HEADERS)
        assert r.status_code == 200

    def test_interventions_is_list(self):
        r = client.get("/api/quality-twin/interventions", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body.get("interventions"), list)

    def test_intervention_has_confidence_score(self):
        r = client.get("/api/quality-twin/interventions", headers=HEADERS)
        assert r.status_code == 200
        interventions = r.json()["interventions"]
        assert len(interventions) > 0
        for item in interventions:
            assert "confidence_score" in item


# ---------------------------------------------------------------------------
# Executive Brief
# ---------------------------------------------------------------------------


class TestExecutiveBrief:
    def test_executive_brief_returns_200(self):
        r = client.get("/api/quality-twin/executive-brief", headers=HEADERS)
        assert r.status_code == 200

    def test_executive_brief_has_headline_risk(self):
        r = client.get("/api/quality-twin/executive-brief", headers=HEADERS)
        assert r.status_code == 200
        brief = r.json()["brief"]
        assert "headline_risk" in brief
        assert brief["headline_risk"]

    def test_executive_brief_human_review_required(self):
        r = client.get("/api/quality-twin/executive-brief", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True
        assert body["brief"].get("human_review_required") is True

    def test_executive_brief_returns_role_specific_content(self):
        roles = ["CEO", "COO", "CNO", "CQO", "quality_director", "market_director"]
        headlines = set()
        for role in roles:
            r = client.get(
                f"/api/quality-twin/executive-brief?role={role}", headers=HEADERS
            )
            assert r.status_code == 200, f"Failed for role {role}"
            brief = r.json()["brief"]
            assert brief.get("role") == role or brief.get("headline_risk"), (
                f"Role {role} brief missing headline_risk"
            )
            headlines.add(brief.get("headline_risk", ""))
        # At least some roles should have distinct headlines
        assert len(headlines) > 1


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


class TestSynthesis:
    def test_synthesize_returns_200(self):
        r = client.post(
            "/api/quality-twin/synthesize", json={"facility_id": ""}, headers=HEADERS
        )
        assert r.status_code == 200

    def test_synthesize_has_sources_ingested(self):
        r = client.post(
            "/api/quality-twin/synthesize", json={"facility_id": ""}, headers=HEADERS
        )
        assert r.status_code == 200
        body = r.json()
        assert "sources_ingested" in body
        assert isinstance(body["sources_ingested"], list)
        assert len(body["sources_ingested"]) == 9


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_dashboard_returns_200(self):
        r = client.get("/api/quality-twin/dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_dashboard_has_all_kpis(self):
        r = client.get("/api/quality-twin/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        required_keys = {
            "overall_quality_score",
            "open_emerging_risks",
            "open_investigations",
            "active_recalls",
            "trend_direction",
            "human_review_required_count",
        }
        for key in required_keys:
            assert key in body, f"Missing key: {key}"

    def test_dashboard_has_disclaimer(self):
        r = client.get("/api/quality-twin/dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------


class TestGovernance:
    def test_no_patient_identifiers_in_state(self):
        r = client.get("/api/quality-twin/state", headers=HEADERS)
        assert r.status_code == 200
        keys = _flatten_keys(r.json())
        forbidden_found = keys & _FORBIDDEN_PATIENT_KEYS
        assert not forbidden_found, f"Forbidden patient keys found: {forbidden_found}"

    def test_no_causation_language_in_forecasts(self):
        r = client.get("/api/quality-twin/forecasts", headers=HEADERS)
        assert r.status_code == 200
        forecasts = r.json()["forecasts"]
        for f in forecasts:
            disclaimer = f.get("disclaimer", "").lower()
            assert "does not establish causation" in disclaimer

    def test_human_review_on_all_scenarios(self):
        # First create a scenario
        client.post(
            "/api/quality-twin/simulate",
            json={"scenario_type": "risk_reduction", "intervention_type": "capa_closure", "parameters": {}},
            headers=HEADERS,
        )
        r = client.get("/api/quality-twin/scenarios", headers=HEADERS)
        assert r.status_code == 200
        scenarios = r.json()["scenarios"]
        for s in scenarios:
            assert s.get("human_review_required") is True

    def test_disclaimer_in_executive_brief(self):
        r = client.get(
            "/api/quality-twin/executive-brief?role=CQO", headers=HEADERS
        )
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        brief = body["brief"]
        disclaimer = brief.get("disclaimer", body.get("disclaimer", "")).lower()
        assert "association" in disclaimer or "does not establish" in disclaimer
