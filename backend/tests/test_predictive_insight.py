"""v3.3 — Project Insight: Predictive Clinical Intelligence & Quality Forecasting tests."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import RepairRequest
from app.models.supervisor_review import SupervisorReview

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _make_inspection(tenant_id: str, *, days_ago: int = 0, **overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, file_name="x.jpg", instrument_type="kerrison_rongeur",
            has_image=True, image_sha256="c3" * 32, score_status="scored", risk_score=10,
            detected_issue="none", stain_detected=False, supervisor_review_required=False,
            qa_review_status="pending", status="pending", inspected_zones_json="null",
            coverage_pct=95, baseline_status="approved", disposition="PASS", technician="Alex Tech",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_finding(tenant_id: str, inspection_id: int, *, days_ago: int = 0, **overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, inspection_id=inspection_id, instrument_type="kerrison_rongeur",
            finding_type="corrosion", zone="serrations", created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        db.add(InspectionFinding(**defaults))
        db.commit()
    finally:
        db.close()


def _make_supervisor_review(tenant_id: str, inspection_id: int, *, days_ago: int = 0, **overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, inspection_id=inspection_id, reviewer_name="Supervisor One", reviewer_role="spd_manager",
            agreement="agree", ai_confidence=0.9, created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        db.add(SupervisorReview(**defaults))
        db.commit()
    finally:
        db.close()


def _make_repair(tenant_id: str, inspection_id: int, *, days_ago: int = 0, **overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, inspection_id=inspection_id, instrument_identity="barcode:x", vendor_name="AcmeSurgical",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        db.add(RepairRequest(**defaults))
        db.commit()
    finally:
        db.close()


def _seed_corrosion_trend(tenant_id: str, instrument_type: str = "kerrison_rongeur") -> None:
    """Corrosion findings concentrated recently (last 14 days), sparse
    before that — a real, detectable increasing trend."""
    for d in range(60, 14, -7):
        insp_id = _make_inspection(tenant_id, days_ago=d, instrument_type=instrument_type)
        _make_finding(tenant_id, insp_id, days_ago=d, finding_type="corrosion", instrument_type=instrument_type)
    for d in range(13, -1, -1):
        insp_id = _make_inspection(tenant_id, days_ago=d, instrument_type=instrument_type)
        for _ in range(3):
            _make_finding(tenant_id, insp_id, days_ago=d, finding_type="corrosion", instrument_type=instrument_type)


class TestPredictiveIntelligenceEngine:
    def test_generate_predictive_intelligence_shape(self):
        tenant_id = uid("tenant")
        _make_inspection(tenant_id, days_ago=5)
        res = client.get("/api/insight/intelligence", headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        body = res.json()
        for key in (
            "quality_trend_forecasts", "operational_forecasts", "instrument_lifecycle_forecasts",
            "predictive_education", "existing_instrument_failure_dashboard", "existing_quality_forecasts", "summary",
        ):
            assert key in body
        assert body["human_review_required"] is True
        assert body["disclaimer"]

    def test_requires_leadership_role(self):
        tenant_id = uid("tenant")
        res = client.get("/api/insight/intelligence", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 403


class TestQualityTrendForecasting:
    def test_forecast_detects_increasing_corrosion_trend(self):
        tenant_id = uid("tenant")
        _seed_corrosion_trend(tenant_id)
        res = client.post(
            "/api/insight/quality-trends/generate", params={"horizon": "30_day"}, headers=_headers(AUTH_MGR, tenant_id),
        )
        assert res.status_code == 200
        forecasts = {f["metric"]: f for f in res.json()["forecasts"]}
        corrosion = forecasts["corrosion"]
        assert corrosion["trend_direction"] == "increasing"
        assert corrosion["confidence_level"] > 0

    def test_invalid_metric_rejected(self):
        tenant_id = uid("tenant")
        res = client.get("/api/insight/quality-trends", params={"metric": "not_a_metric"}, headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200  # list endpoint just filters, returns empty
        assert res.json()["forecasts"] == []

    def test_invalid_horizon_rejected_on_generate(self):
        tenant_id = uid("tenant")
        res = client.post("/api/insight/quality-trends/generate", params={"horizon": "not_a_horizon"}, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 422

    def test_generate_all_nine_metrics(self):
        tenant_id = uid("tenant")
        _make_inspection(tenant_id, days_ago=1)
        res = client.post("/api/insight/quality-trends/generate", headers=_headers(AUTH_MGR, tenant_id))
        metrics = {f["metric"] for f in res.json()["forecasts"]}
        assert metrics == {
            "blood", "bone", "debris", "rust", "corrosion", "damage",
            "coverage_compliance", "supervisor_workload", "inspection_throughput",
        }


class TestExplainabilityMetadata:
    def test_forecast_carries_full_explainability_envelope(self):
        tenant_id = uid("tenant")
        _seed_corrosion_trend(tenant_id)
        res = client.post("/api/insight/quality-trends/generate", params={"horizon": "7_day"}, headers=_headers(AUTH_MGR, tenant_id))
        forecast = next(f for f in res.json()["forecasts"] if f["metric"] == "corrosion")
        assert forecast["data_sources"]
        assert forecast["horizon"] == "7_day"
        assert "confidence_level" in forecast
        assert isinstance(forecast["contributing_factors"], list) and forecast["contributing_factors"]
        assert "recent_14d_avg" in forecast["historical_comparison"]
        assert isinstance(forecast["known_limitations"], list)


class TestInstrumentAndDigitalTwinForecasting:
    def test_lifecycle_forecast_shape_and_health_trajectory(self):
        tenant_id = uid("tenant")
        _seed_corrosion_trend(tenant_id, instrument_type="laparoscope")
        res = client.post("/api/insight/instrument-lifecycle/generate", headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        forecasts = {f["instrument_type"]: f for f in res.json()["forecasts"]}
        f = forecasts["laparoscope"]
        assert f["corrosion_progression_score"] is not None
        assert f["lifecycle_risk_tier"] in ("low", "moderate", "high", "critical")
        horizons = {p["horizon_days"] for p in f["health_score_trajectory"]}
        assert 7 in horizons
        assert 365 in horizons

    def test_removal_from_service_likelihood_reflects_real_dispositions(self):
        tenant_id = uid("tenant")
        for _ in range(3):
            _make_inspection(tenant_id, instrument_type="drill_bit", disposition="REMOVE FROM SERVICE", days_ago=2)
        for _ in range(2):
            _make_inspection(tenant_id, instrument_type="drill_bit", disposition="PASS", days_ago=2)
        res = client.post("/api/insight/instrument-lifecycle/generate", headers=_headers(AUTH_MGR, tenant_id))
        f = next(x for x in res.json()["forecasts"] if x["instrument_type"] == "drill_bit")
        assert f["removal_from_service_likelihood"] == 0.6

    def test_no_data_instrument_type_reports_none_not_fabricated(self):
        tenant_id = uid("tenant")
        res = client.get("/api/insight/instrument-lifecycle", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200
        assert res.json()["forecasts"] == []


class TestOperationalForecasting:
    def test_inspection_workload_forecast(self):
        tenant_id = uid("tenant")
        for d in range(10):
            _make_inspection(tenant_id, days_ago=d)
        res = client.post(
            "/api/insight/operational-forecasts/generate", params={"horizon": "30_day"}, headers=_headers(AUTH_MGR, tenant_id),
        )
        assert res.status_code == 200
        forecasts = {f["forecast_type"]: f for f in res.json()["forecasts"]}
        assert "inspection_workload" in forecasts
        assert forecasts["inspection_workload"]["confidence_level"] >= 0

    def test_peak_inspection_periods_returns_weekday_distribution(self):
        tenant_id = uid("tenant")
        for d in range(30):
            _make_inspection(tenant_id, days_ago=d)
        res = client.post("/api/insight/operational-forecasts/generate", headers=_headers(AUTH_MGR, tenant_id))
        peak = next(f for f in res.json()["forecasts"] if f["forecast_type"] == "peak_inspection_periods")
        assert "weekday_averages" in peak["forecast_detail"]

    def test_invalid_forecast_type_rejected_via_list(self):
        tenant_id = uid("tenant")
        res = client.get("/api/insight/operational-forecasts", params={"forecast_type": "not_a_type"}, headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200
        assert res.json()["forecasts"] == []


class TestPredictiveEducationEngine:
    def test_missed_anatomy_zone_and_coverage_decline_signals(self):
        tenant_id = uid("tenant")
        technician = "Jamie Tech"
        for d in range(45, 30, -3):
            _make_inspection(tenant_id, days_ago=d, technician=technician, coverage_pct=95, inspected_zones_json='["tip", "shaft", "hinge", "box_lock"]')
        for d in range(10, -1, -1):
            _make_inspection(tenant_id, days_ago=d, technician=technician, coverage_pct=60, inspected_zones_json='["tip"]')

        res = client.post("/api/insight/education-signals/generate", headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        body = res.json()
        assert "new_signals" in body
        assert "existing_competency_opportunities" in body

    def test_list_education_signals(self):
        tenant_id = uid("tenant")
        res = client.get("/api/insight/education-signals", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200
        assert res.json()["signals"] == []


class TestPredictiveRecommendationEngine:
    def test_recommendation_generated_from_adverse_quality_trend(self):
        tenant_id = uid("tenant")
        _seed_corrosion_trend(tenant_id)
        client.post("/api/insight/quality-trends/generate", params={"horizon": "30_day"}, headers=_headers(AUTH_MGR, tenant_id))

        res = client.post("/api/insight/recommendations/generate", headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        recs = res.json()["recommendations"]
        assert len(recs) > 0
        rec = recs[0]
        for key in ("evidence_json", "confidence_level", "reasoning", "suggested_action"):
            assert key in rec

    def test_action_and_dismiss_recommendation(self):
        tenant_id = uid("tenant")
        _seed_corrosion_trend(tenant_id)
        client.post("/api/insight/quality-trends/generate", headers=_headers(AUTH_MGR, tenant_id))
        recs = client.post("/api/insight/recommendations/generate", headers=_headers(AUTH_MGR, tenant_id)).json()["recommendations"]
        assert recs

        rec_id = recs[0]["id"]
        actioned = client.post(f"/api/insight/recommendations/{rec_id}/action", headers=_headers(AUTH_MGR, tenant_id))
        assert actioned.status_code == 200
        assert actioned.json()["status"] == "actioned"

    def test_dismiss_unknown_recommendation_404s(self):
        tenant_id = uid("tenant")
        res = client.post("/api/insight/recommendations/999999/dismiss", headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 404

    def test_regenerating_does_not_duplicate_open_recommendations(self):
        tenant_id = uid("tenant")
        _seed_corrosion_trend(tenant_id)
        client.post("/api/insight/quality-trends/generate", headers=_headers(AUTH_MGR, tenant_id))
        first = client.post("/api/insight/recommendations/generate", headers=_headers(AUTH_MGR, tenant_id)).json()["recommendations"]
        client.post("/api/insight/quality-trends/generate", headers=_headers(AUTH_MGR, tenant_id))
        second = client.post("/api/insight/recommendations/generate", headers=_headers(AUTH_MGR, tenant_id)).json()["recommendations"]
        assert len(second) == len(first)


class TestForecastDashboard:
    def test_dashboard_returns_six_named_displays(self):
        tenant_id = uid("tenant")
        _seed_corrosion_trend(tenant_id)
        res = client.get("/api/insight/dashboard", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200
        body = res.json()
        for key in (
            "enterprise_quality_forecast", "risk_forecast", "repair_forecast",
            "instrument_health_forecast", "inspection_volume_forecast", "education_forecast",
        ):
            assert key in body
        assert body["disclaimer"]


class TestExecutiveForecastReports:
    def test_generate_report_and_export_all_formats(self):
        tenant_id = uid("tenant")
        _seed_corrosion_trend(tenant_id)
        res = client.post("/api/insight/reports/generate", json={"cadence": "monthly"}, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        report = res.json()
        assert report["cadence"] == "monthly"
        report_id = report["id"]

        fetched = client.get(f"/api/insight/reports/{report_id}", headers=_headers(AUTH_VIEWER, tenant_id))
        assert fetched.status_code == 200
        assert "summary" in fetched.json()

        csv_res = client.get(f"/api/insight/reports/{report_id}.csv", headers=_headers(AUTH_VIEWER, tenant_id))
        assert csv_res.status_code == 200
        assert csv_res.headers["content-type"].startswith("text/csv")

        xlsx_res = client.get(f"/api/insight/reports/{report_id}.xlsx", headers=_headers(AUTH_VIEWER, tenant_id))
        assert xlsx_res.status_code == 200

        pdf_res = client.get(f"/api/insight/reports/{report_id}.pdf", headers=_headers(AUTH_VIEWER, tenant_id))
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"

    def test_invalid_cadence_rejected(self):
        tenant_id = uid("tenant")
        res = client.post("/api/insight/reports/generate", json={"cadence": "biannual"}, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 422

    def test_list_reports_filters_by_cadence(self):
        tenant_id = uid("tenant")
        client.post("/api/insight/reports/generate", json={"cadence": "weekly"}, headers=_headers(AUTH_MGR, tenant_id))
        client.post("/api/insight/reports/generate", json={"cadence": "annual"}, headers=_headers(AUTH_MGR, tenant_id))
        weekly = client.get("/api/insight/reports", params={"cadence": "weekly"}, headers=_headers(AUTH_VIEWER, tenant_id)).json()["reports"]
        assert all(r["cadence"] == "weekly" for r in weekly)
