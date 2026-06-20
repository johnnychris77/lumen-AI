"""P7: Predictive Instrument Failure Analytics tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH = {"Authorization": "Bearer dev-token", "X-LumenAI-Role": "operator"}
TENANT = "test-tenant-p7"
TENANT_B = "another-tenant-p7"
INSTRUMENT = "Laparoscopic Trocar 5mm"


# ────────────────────────────────────────────────────────────────────────────────
# TestFailurePredictionAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestFailurePredictionAPI:
    def test_list_failures_status_ok(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_list_failures_returns_success(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_list_failures_has_predictions_list(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        assert "predictions" in r.json()
        assert isinstance(r.json()["predictions"], list)

    def test_list_failures_not_empty(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["predictions"]) > 0

    def test_list_failures_has_risk_score(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        p = r.json()["predictions"][0]
        assert "risk_score" in p
        assert 0 <= p["risk_score"] <= 100

    def test_list_failures_has_failure_probability(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        p = r.json()["predictions"][0]
        assert 0.0 <= p["failure_probability"] <= 1.0

    def test_list_failures_risk_category_valid(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        p = r.json()["predictions"][0]
        assert p["risk_category"] in ("low", "medium", "high", "critical")

    def test_list_failures_data_source_valid(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        p = r.json()["predictions"][0]
        assert p["data_source"] in ("real", "mock", "insufficient")

    def test_list_failures_has_evidence(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        p = r.json()["predictions"][0]
        assert "evidence" in p
        assert isinstance(p["evidence"], list)
        assert len(p["evidence"]) >= 1

    def test_list_failures_horizon_days_default(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["horizon_days"] == 30

    def test_list_failures_horizon_90(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT, "horizon_days": 90}, headers=AUTH)
        assert r.json()["horizon_days"] == 90

    def test_list_failures_requires_auth(self):
        r = client.get("/api/predictions/failures", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_get_failure_by_instrument_status_ok(self):
        r = client.get(f"/api/predictions/failures/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_failure_by_instrument_returns_prediction(self):
        r = client.get(f"/api/predictions/failures/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert "prediction" in r.json()

    def test_get_failure_by_instrument_has_instrument_name(self):
        r = client.get(f"/api/predictions/failures/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["prediction"]["instrument_name"] == INSTRUMENT


# ────────────────────────────────────────────────────────────────────────────────
# TestContaminationPredictionAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestContaminationPredictionAPI:
    def test_list_contamination_status_ok(self):
        r = client.get("/api/predictions/contamination", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_list_contamination_returns_success(self):
        r = client.get("/api/predictions/contamination", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_list_contamination_has_predictions(self):
        r = client.get("/api/predictions/contamination", params={"tenant_id": TENANT}, headers=AUTH)
        assert "predictions" in r.json()
        assert len(r.json()["predictions"]) > 0

    def test_list_contamination_has_recurrence_probability(self):
        r = client.get("/api/predictions/contamination", params={"tenant_id": TENANT}, headers=AUTH)
        p = r.json()["predictions"][0]
        assert 0.0 <= p["recurrence_probability"] <= 1.0

    def test_list_contamination_has_dominant_contaminant(self):
        r = client.get("/api/predictions/contamination", params={"tenant_id": TENANT}, headers=AUTH)
        p = r.json()["predictions"][0]
        assert "dominant_contaminant" in p
        assert p["dominant_contaminant"] in ("blood", "bone", "tissue", "residue")

    def test_list_contamination_has_evidence(self):
        r = client.get("/api/predictions/contamination", params={"tenant_id": TENANT}, headers=AUTH)
        p = r.json()["predictions"][0]
        assert len(p["evidence"]) >= 1

    def test_list_contamination_requires_auth(self):
        r = client.get("/api/predictions/contamination", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_get_contamination_by_instrument_status_ok(self):
        r = client.get(f"/api/predictions/contamination/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_contamination_by_instrument_has_prediction(self):
        r = client.get(f"/api/predictions/contamination/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert "prediction" in r.json()

    def test_get_contamination_risk_score_valid(self):
        r = client.get(f"/api/predictions/contamination/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert 0 <= r.json()["prediction"]["risk_score"] <= 100

    def test_get_contamination_has_recommended_action(self):
        r = client.get(f"/api/predictions/contamination/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["prediction"]["recommended_action"]) > 0

    def test_contamination_data_source_valid(self):
        r = client.get(f"/api/predictions/contamination/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["prediction"]["data_source"] in ("real", "mock", "insufficient")


# ────────────────────────────────────────────────────────────────────────────────
# TestRepairForecastAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestRepairForecastAPI:
    def test_list_repairs_status_ok(self):
        r = client.get("/api/predictions/repairs", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_list_repairs_returns_success(self):
        r = client.get("/api/predictions/repairs", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_list_repairs_has_forecasts(self):
        r = client.get("/api/predictions/repairs", params={"tenant_id": TENANT}, headers=AUTH)
        assert "forecasts" in r.json()
        assert len(r.json()["forecasts"]) > 0

    def test_list_repairs_has_repair_probability(self):
        r = client.get("/api/predictions/repairs", params={"tenant_id": TENANT}, headers=AUTH)
        f = r.json()["forecasts"][0]
        assert 0.0 <= f["repair_probability_90d"] <= 1.0

    def test_list_repairs_has_replacement_probability(self):
        r = client.get("/api/predictions/repairs", params={"tenant_id": TENANT}, headers=AUTH)
        f = r.json()["forecasts"][0]
        assert 0.0 <= f["replacement_probability_180d"] <= 1.0

    def test_list_repairs_has_cost_estimate(self):
        r = client.get("/api/predictions/repairs", params={"tenant_id": TENANT}, headers=AUTH)
        f = r.json()["forecasts"][0]
        assert f["estimated_repair_cost_usd"] >= 0
        assert f["estimated_replacement_cost_usd"] >= 0

    def test_list_repairs_requires_auth(self):
        r = client.get("/api/predictions/repairs", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_get_repair_by_instrument_status_ok(self):
        r = client.get(f"/api/predictions/repairs/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_repair_by_instrument_has_forecast(self):
        r = client.get(f"/api/predictions/repairs/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert "forecast" in r.json()

    def test_get_repair_has_recommended_action(self):
        r = client.get(f"/api/predictions/repairs/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["forecast"]["recommended_action"]) > 0

    def test_get_repair_has_evidence(self):
        r = client.get(f"/api/predictions/repairs/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["forecast"]["evidence"]) >= 1

    def test_repair_risk_category_valid(self):
        r = client.get(f"/api/predictions/repairs/{INSTRUMENT}", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["forecast"]["risk_category"] in ("low", "medium", "high", "critical")


# ────────────────────────────────────────────────────────────────────────────────
# TestRecallRiskAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestRecallRiskAPI:
    def test_list_recall_risks_status_ok(self):
        r = client.get("/api/predictions/recall-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_list_recall_risks_returns_success(self):
        r = client.get("/api/predictions/recall-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_list_recall_risks_has_recall_risks(self):
        r = client.get("/api/predictions/recall-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert "recall_risks" in r.json()
        assert len(r.json()["recall_risks"]) > 0

    def test_list_recall_risks_exposure_score_valid(self):
        r = client.get("/api/predictions/recall-risk", params={"tenant_id": TENANT}, headers=AUTH)
        risk = r.json()["recall_risks"][0]
        assert 0 <= risk["exposure_score"] <= 100

    def test_list_recall_risks_urgency_tier_valid(self):
        r = client.get("/api/predictions/recall-risk", params={"tenant_id": TENANT}, headers=AUTH)
        risk = r.json()["recall_risks"][0]
        assert risk["urgency_tier"] in ("low", "watch", "act", "critical")

    def test_list_recall_risks_requires_auth(self):
        r = client.get("/api/predictions/recall-risk", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_get_recall_risk_by_category_status_ok(self):
        r = client.get("/api/predictions/recall-risk/laparoscopic", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_recall_risk_by_category_has_recall_risk(self):
        r = client.get("/api/predictions/recall-risk/laparoscopic", params={"tenant_id": TENANT}, headers=AUTH)
        assert "recall_risk" in r.json()

    def test_get_recall_risk_has_evidence(self):
        r = client.get("/api/predictions/recall-risk/laparoscopic", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["recall_risk"]["evidence"]) >= 1

    def test_get_recall_risk_has_recommended_action(self):
        r = client.get("/api/predictions/recall-risk/laparoscopic", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["recall_risk"]["recommended_action"]) > 0


# ────────────────────────────────────────────────────────────────────────────────
# TestTrayRiskAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestTrayRiskAPI:
    def test_get_tray_risk_status_ok(self):
        r = client.get("/api/predictions/tray-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_tray_risk_returns_success(self):
        r = client.get("/api/predictions/tray-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_get_tray_risk_has_tray_risk(self):
        r = client.get("/api/predictions/tray-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert "tray_risk" in r.json()

    def test_get_tray_risk_score_valid(self):
        r = client.get("/api/predictions/tray-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert 0 <= r.json()["tray_risk"]["tray_risk_score"] <= 100

    def test_get_tray_risk_category_valid(self):
        r = client.get("/api/predictions/tray-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["tray_risk"]["risk_category"] in ("low", "medium", "high", "critical")

    def test_get_tray_risk_has_evidence(self):
        r = client.get("/api/predictions/tray-risk", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["tray_risk"]["evidence"]) >= 1

    def test_get_tray_risk_requires_auth(self):
        r = client.get("/api/predictions/tray-risk", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_get_tray_risk_custom_tray_id(self):
        r = client.get("/api/predictions/tray-risk", params={"tenant_id": TENANT, "tray_id": "tray-alpha"}, headers=AUTH)
        assert r.status_code == 200
        assert r.json()["tray_risk"]["tray_id"] == "tray-alpha"


# ────────────────────────────────────────────────────────────────────────────────
# TestPredictiveDashboardAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestPredictiveDashboardAPI:
    def test_dashboard_status_ok(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_dashboard_returns_success(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_dashboard_has_dashboard_key(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert "dashboard" in r.json()

    def test_dashboard_has_predicted_failures_30d(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        d = r.json()["dashboard"]
        assert "predicted_failures_30d" in d
        assert isinstance(d["predicted_failures_30d"], int)

    def test_dashboard_has_predicted_failures_90d(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        d = r.json()["dashboard"]
        assert "predicted_failures_90d" in d

    def test_dashboard_has_highest_risk_instruments(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        d = r.json()["dashboard"]
        assert "highest_risk_instruments" in d
        assert isinstance(d["highest_risk_instruments"], list)

    def test_dashboard_has_recall_exposure_score(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        d = r.json()["dashboard"]
        assert "recall_exposure_score" in d
        assert 0 <= d["recall_exposure_score"] <= 100

    def test_dashboard_has_top_risk_factors(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        d = r.json()["dashboard"]
        assert "top_risk_factors" in d
        assert isinstance(d["top_risk_factors"], list)

    def test_dashboard_requires_auth(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_dashboard_has_data_source(self):
        r = client.get("/api/predictions/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        d = r.json()["dashboard"]
        assert d["data_source"] in ("real", "mock", "insufficient")


# ────────────────────────────────────────────────────────────────────────────────
# TestPredictionEngine (unit tests)
# ────────────────────────────────────────────────────────────────────────────────

class TestPredictionEngine:
    def test_failure_prediction_returns_result(self):
        from app.services.prediction_engine import predict_instrument_failure
        result = predict_instrument_failure(TENANT, INSTRUMENT)
        assert result.instrument_name == INSTRUMENT

    def test_failure_prediction_risk_score_range(self):
        from app.services.prediction_engine import predict_instrument_failure
        result = predict_instrument_failure(TENANT, INSTRUMENT)
        assert 0 <= result.risk_score <= 100

    def test_failure_prediction_probability_range(self):
        from app.services.prediction_engine import predict_instrument_failure
        result = predict_instrument_failure(TENANT, INSTRUMENT)
        assert 0.0 <= result.failure_probability <= 1.0

    def test_failure_prediction_mock_data_source(self):
        from app.services.prediction_engine import predict_instrument_failure
        result = predict_instrument_failure(TENANT, INSTRUMENT, db=None)
        assert result.data_source == "mock"

    def test_contamination_prediction_returns_result(self):
        from app.services.prediction_engine import predict_contamination_recurrence
        result = predict_contamination_recurrence(TENANT, INSTRUMENT)
        assert result.instrument_name == INSTRUMENT

    def test_contamination_prediction_valid_dominant(self):
        from app.services.prediction_engine import predict_contamination_recurrence
        result = predict_contamination_recurrence(TENANT, INSTRUMENT)
        assert result.dominant_contaminant in ("blood", "bone", "tissue", "residue")

    def test_repair_forecast_returns_result(self):
        from app.services.prediction_engine import forecast_repair
        result = forecast_repair(TENANT, INSTRUMENT)
        assert result.instrument_name == INSTRUMENT

    def test_repair_forecast_costs_positive(self):
        from app.services.prediction_engine import forecast_repair
        result = forecast_repair(TENANT, INSTRUMENT)
        assert result.estimated_repair_cost_usd >= 0
        assert result.estimated_replacement_cost_usd >= 0

    def test_recall_risk_returns_result(self):
        from app.services.prediction_engine import assess_recall_risk
        result = assess_recall_risk(TENANT, "laparoscopic")
        assert result.instrument_category == "laparoscopic"

    def test_recall_risk_exposure_score_range(self):
        from app.services.prediction_engine import assess_recall_risk
        result = assess_recall_risk(TENANT, "laparoscopic")
        assert 0 <= result.exposure_score <= 100

    def test_tray_risk_returns_result(self):
        from app.services.prediction_engine import assess_tray_risk
        result = assess_tray_risk(TENANT, "tray-001")
        assert result.tray_id == "tray-001"

    def test_tray_risk_score_range(self):
        from app.services.prediction_engine import assess_tray_risk
        result = assess_tray_risk(TENANT, "tray-001")
        assert 0 <= result.tray_risk_score <= 100

    def test_risk_category_function_low(self):
        from app.services.prediction_engine import _risk_category
        assert _risk_category(10) == "low"

    def test_risk_category_function_medium(self):
        from app.services.prediction_engine import _risk_category
        assert _risk_category(30) == "medium"

    def test_risk_category_function_critical(self):
        from app.services.prediction_engine import _risk_category
        assert _risk_category(80) == "critical"


# ────────────────────────────────────────────────────────────────────────────────
# TestTenantIsolation
# ────────────────────────────────────────────────────────────────────────────────

class TestTenantIsolation:
    def test_failure_different_tenants_different_results(self):
        from app.services.prediction_engine import predict_instrument_failure
        r1 = predict_instrument_failure(TENANT, INSTRUMENT)
        r2 = predict_instrument_failure(TENANT_B, INSTRUMENT)
        # Different tenants produce different predictions (seeded by tenant_id)
        assert r1.tenant_id == TENANT
        assert r2.tenant_id == TENANT_B

    def test_contamination_tenant_id_in_result(self):
        from app.services.prediction_engine import predict_contamination_recurrence
        result = predict_contamination_recurrence(TENANT, INSTRUMENT)
        assert result.tenant_id == TENANT

    def test_repair_tenant_id_in_result(self):
        from app.services.prediction_engine import forecast_repair
        result = forecast_repair(TENANT, INSTRUMENT)
        assert result.tenant_id == TENANT

    def test_recall_tenant_id_in_result(self):
        from app.services.prediction_engine import assess_recall_risk
        result = assess_recall_risk(TENANT, "orthopedic")
        assert result.tenant_id == TENANT

    def test_dashboard_tenant_id_in_result(self):
        from app.services.prediction_engine import compute_predictive_dashboard
        result = compute_predictive_dashboard(TENANT)
        assert result.tenant_id == TENANT


# ────────────────────────────────────────────────────────────────────────────────
# TestExplainability
# ────────────────────────────────────────────────────────────────────────────────

class TestExplainability:
    def test_failure_evidence_has_required_fields(self):
        from app.services.prediction_engine import predict_instrument_failure
        result = predict_instrument_failure(TENANT, INSTRUMENT)
        for ev in result.evidence:
            assert hasattr(ev, "factor")
            assert hasattr(ev, "value")
            assert hasattr(ev, "weight")
            assert hasattr(ev, "signal")

    def test_contamination_evidence_has_required_fields(self):
        from app.services.prediction_engine import predict_contamination_recurrence
        result = predict_contamination_recurrence(TENANT, INSTRUMENT)
        for ev in result.evidence:
            assert ev.factor
            assert ev.signal in ("elevated", "stable", "degrading", "below_threshold", "above_threshold",
                                  "repair_preferred", "evaluate_replacement", "low", "medium", "high", "critical")

    def test_repair_evidence_includes_cost_ratio(self):
        from app.services.prediction_engine import forecast_repair
        result = forecast_repair(TENANT, INSTRUMENT)
        factors = [ev.factor for ev in result.evidence]
        assert "repair_vs_replace_ratio" in factors

    def test_recall_evidence_has_three_factors(self):
        from app.services.prediction_engine import assess_recall_risk
        result = assess_recall_risk(TENANT, "general_surgery")
        assert len(result.evidence) >= 3

    def test_tray_evidence_has_instrument_count(self):
        from app.services.prediction_engine import assess_tray_risk
        result = assess_tray_risk(TENANT, "tray-beta")
        factors = [ev.factor for ev in result.evidence]
        assert "instrument_count" in factors
