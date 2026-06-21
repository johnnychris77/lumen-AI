"""P21: Autonomous Healthcare Quality Intelligence Network — test suite."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"Authorization": "Bearer dev-token"}
NO_AUTH = {}

client = TestClient(app, raise_server_exceptions=True)

_CAUSATION_WORDS = {"caused", "led to", "resulted in", "responsible for"}
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
# Emerging Risk Signals
# ---------------------------------------------------------------------------


class TestEmergingRiskSignals:
    def test_signals_returns_200(self):
        r = client.get("/api/intelligence/signals", headers=HEADERS)
        assert r.status_code == 200

    def test_signals_require_auth(self):
        r = client.get("/api/intelligence/signals", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_signals_has_disclaimer(self):
        r = client.get("/api/intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10

    def test_signals_no_causation_language(self):
        r = client.get("/api/intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        text = _flatten_text(r.json()).lower()
        for word in _CAUSATION_WORDS:
            assert word not in text, f"Causation language found: {word!r}"

    def test_signals_human_review_required(self):
        r = client.get("/api/intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert body.get("human_review_required") is True

    def test_signals_tenant_isolated(self):
        r = client.get("/api/intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        for sig in body.get("signals", []):
            assert "tenant_id" in sig

    def test_emerging_risks_alias_returns_200(self):
        r = client.get("/api/intelligence/emerging-risks", headers=HEADERS)
        assert r.status_code == 200

    def test_emerging_risks_has_disclaimer(self):
        r = client.get("/api/intelligence/emerging-risks", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body


# ---------------------------------------------------------------------------
# Risk Analysis
# ---------------------------------------------------------------------------


class TestRiskAnalysis:
    def test_run_analysis_returns_200(self):
        r = client.post(
            "/api/intelligence/run-analysis",
            json={"facility_id": ""},
            headers=HEADERS,
        )
        assert r.status_code == 200

    def test_run_analysis_has_signals_analyzed(self):
        r = client.post(
            "/api/intelligence/run-analysis",
            json={"facility_id": ""},
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert "signals_analyzed" in body
        assert isinstance(body["signals_analyzed"], int)

    def test_run_analysis_human_review_required_true(self):
        r = client.post(
            "/api/intelligence/run-analysis",
            json={"facility_id": ""},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json().get("human_review_required") is True

    def test_run_analysis_no_causation_language(self):
        r = client.post(
            "/api/intelligence/run-analysis",
            json={"facility_id": ""},
            headers=HEADERS,
        )
        assert r.status_code == 200
        text = _flatten_text(r.json()).lower()
        for word in _CAUSATION_WORDS:
            assert word not in text, f"Causation language found: {word!r}"

    def test_run_analysis_requires_auth(self):
        r = client.post(
            "/api/intelligence/run-analysis",
            json={"facility_id": ""},
            headers=NO_AUTH,
        )
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------


class TestInvestigations:
    def test_investigations_returns_200(self):
        r = client.get("/api/intelligence/investigations", headers=HEADERS)
        assert r.status_code == 200

    def test_investigation_requires_auth(self):
        r = client.get("/api/intelligence/investigations", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_create_investigation_returns_201_or_200(self):
        r = client.post(
            "/api/intelligence/investigations",
            json={
                "title": "Test Investigation",
                "description": "Elevated risk signal review candidate",
                "priority": "high",
            },
            headers=HEADERS,
        )
        assert r.status_code in (200, 201)

    def test_create_investigation_has_human_review(self):
        r = client.post(
            "/api/intelligence/investigations",
            json={"title": "Investigation Alpha", "priority": "medium"},
            headers=HEADERS,
        )
        assert r.status_code in (200, 201)
        body = r.json()
        assert body.get("human_review_required") is True

    def test_investigations_list_has_disclaimer(self):
        r = client.get("/api/intelligence/investigations", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body

    def test_update_investigation(self):
        # Create one first
        create_r = client.post(
            "/api/intelligence/investigations",
            json={"title": "Update Test", "priority": "low"},
            headers=HEADERS,
        )
        assert create_r.status_code in (200, 201)
        inv_id = create_r.json()["investigation"]["id"]
        # Now update
        r = client.patch(
            f"/api/intelligence/investigations/{inv_id}",
            json={"status": "in_progress"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["investigation"]["status"] == "in_progress"


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


class TestRecommendations:
    def test_recommendations_returns_200(self):
        r = client.get("/api/intelligence/recommendations", headers=HEADERS)
        assert r.status_code == 200

    def test_recommendations_is_list(self):
        r = client.get("/api/intelligence/recommendations", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body.get("recommendations"), list)

    def test_recommendations_has_human_review(self):
        r = client.get("/api/intelligence/recommendations", headers=HEADERS)
        assert r.status_code == 200
        assert r.json().get("human_review_required") is True

    def test_recommendations_require_auth(self):
        r = client.get("/api/intelligence/recommendations", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_recommendations_no_causation(self):
        r = client.get("/api/intelligence/recommendations", headers=HEADERS)
        assert r.status_code == 200
        text = _flatten_text(r.json()).lower()
        for word in _CAUSATION_WORDS:
            assert word not in text, f"Causation language found: {word!r}"


# ---------------------------------------------------------------------------
# Executive Summary
# ---------------------------------------------------------------------------


class TestExecutiveSummary:
    def test_executive_summary_returns_200(self):
        r = client.get("/api/intelligence/executive-summary", headers=HEADERS)
        assert r.status_code == 200

    def test_executive_summary_has_disclaimer(self):
        r = client.get("/api/intelligence/executive-summary", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "disclaimer" in body
        assert len(body["disclaimer"]) > 10

    def test_executive_summary_human_review_required(self):
        r = client.get("/api/intelligence/executive-summary", headers=HEADERS)
        assert r.status_code == 200
        assert r.json().get("human_review_required") is True

    def test_executive_summary_requires_auth(self):
        r = client.get("/api/intelligence/executive-summary", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_executive_summary_no_causation(self):
        r = client.get("/api/intelligence/executive-summary", headers=HEADERS)
        assert r.status_code == 200
        text = _flatten_text(r.json()).lower()
        for word in _CAUSATION_WORDS:
            assert word not in text, f"Causation language found: {word!r}"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    _KPI_KEYS = [
        "total_signals",
        "open_investigations",
        "pending_recommendations",
        "high_confidence_signals",
        "human_review_required_count",
    ]

    def test_dashboard_returns_200(self):
        r = client.get("/api/intelligence/quality-dashboard", headers=HEADERS)
        assert r.status_code == 200

    def test_dashboard_has_all_kpis(self):
        r = client.get("/api/intelligence/quality-dashboard", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        for key in self._KPI_KEYS:
            assert key in body, f"Missing KPI key: {key}"

    def test_dashboard_requires_auth(self):
        r = client.get("/api/intelligence/quality-dashboard", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_dashboard_human_review_required(self):
        r = client.get("/api/intelligence/quality-dashboard", headers=HEADERS)
        assert r.status_code == 200
        assert r.json().get("human_review_required") is True


# ---------------------------------------------------------------------------
# Risk Graph
# ---------------------------------------------------------------------------


class TestRiskGraph:
    def test_risk_graph_returns_200(self):
        r = client.get("/api/intelligence/risk-graph", headers=HEADERS)
        assert r.status_code == 200

    def test_risk_graph_has_nodes_and_edges(self):
        r = client.get("/api/intelligence/risk-graph", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "nodes" in body
        assert "edges" in body

    def test_risk_graph_requires_auth(self):
        r = client.get("/api/intelligence/risk-graph", headers=NO_AUTH)
        assert r.status_code in (401, 403)

    def test_risk_graph_human_review_required(self):
        r = client.get("/api/intelligence/risk-graph", headers=HEADERS)
        assert r.status_code == 200
        assert r.json().get("human_review_required") is True


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------


class TestGovernance:
    _FORBIDDEN_KEYS = {"patient_id", "mrn", "dob", "ssn", "patient_name"}

    def test_no_patient_identifiers_in_signals(self):
        r = client.get("/api/intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        all_keys = _flatten_keys(r.json())
        overlap = all_keys & self._FORBIDDEN_KEYS
        assert not overlap, f"Patient identifiers found in signals: {overlap}"

    def test_human_review_required_on_executive_summary(self):
        r = client.get("/api/intelligence/executive-summary", headers=HEADERS)
        assert r.status_code == 200
        assert r.json().get("human_review_required") is True

    def test_disclaimer_present(self):
        for endpoint in [
            "/api/intelligence/signals",
            "/api/intelligence/emerging-risks",
            "/api/intelligence/recommendations",
            "/api/intelligence/quality-dashboard",
            "/api/intelligence/executive-summary",
        ]:
            r = client.get(endpoint, headers=HEADERS)
            assert r.status_code == 200, f"{endpoint} returned {r.status_code}"
            body = r.json()
            assert "disclaimer" in body, f"No disclaimer on {endpoint}"

    def test_no_causation_in_recommendations(self):
        r = client.get("/api/intelligence/recommendations", headers=HEADERS)
        assert r.status_code == 200
        text = _flatten_text(r.json()).lower()
        for word in _CAUSATION_WORDS:
            assert word not in text, f"Causation language {word!r} in recommendations"

    def test_all_signals_have_association_reason(self):
        r = client.get("/api/intelligence/signals", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        for sig in body.get("signals", []):
            assert "association_reason" in sig, "Signal missing association_reason"
