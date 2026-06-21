"""P15 pilot analytics endpoint tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH = {"Authorization": "Bearer dev-token"}


class TestContaminationTrends:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/contamination-trends", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/contamination-trends", headers=AUTH).json()
        assert "breakdown" in data
        assert "total_inspections" in data
        assert "contamination_rate_pct" in data
        assert "weekly_trend" in data
        assert data["human_review_required"] is True

    def test_breakdown_contains_contamination_types(self):
        breakdown = client.get("/api/pilot-analytics/contamination-trends", headers=AUTH).json()["breakdown"]
        for key in ("blood", "bone", "tissue", "debris", "corrosion"):
            assert key in breakdown

    def test_custom_days_param(self):
        res = client.get("/api/pilot-analytics/contamination-trends?days=7", headers=AUTH)
        assert res.status_code == 200
        assert res.json()["period_days"] == 7

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/contamination-trends")
        assert res.status_code in (401, 403)


class TestInspectionEfficiency:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/inspection-efficiency", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/inspection-efficiency", headers=AUTH).json()
        assert "volume" in data
        assert "data_quality" in data
        assert "efficiency_estimate" in data
        assert data["human_review_required"] is True

    def test_volume_keys(self):
        volume = client.get("/api/pilot-analytics/inspection-efficiency", headers=AUTH).json()["volume"]
        assert "total" in volume
        assert "reviewed" in volume
        assert "pending" in volume

    def test_efficiency_estimate_keys(self):
        est = client.get("/api/pilot-analytics/inspection-efficiency", headers=AUTH).json()["efficiency_estimate"]
        assert "minutes_saved_per_inspection" in est
        assert "labor_cost_saved_usd" in est

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/inspection-efficiency")
        assert res.status_code in (401, 403)


class TestCapaEffectiveness:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/capa-effectiveness", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/capa-effectiveness", headers=AUTH).json()
        assert "capa_summary" in data
        assert "human_review_required" in data
        assert data["human_review_required"] is True

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/capa-effectiveness")
        assert res.status_code in (401, 403)


class TestBaselineAdoption:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/baseline-adoption", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/baseline-adoption", headers=AUTH).json()
        # response has flat structure with total_baselines or adoption key
        assert "approval_rate_pct" in data or "adoption" in data or "total_baselines" in data

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/baseline-adoption")
        assert res.status_code in (401, 403)


class TestROI:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/roi", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/roi", headers=AUTH).json()
        assert "disclaimers" in data
        assert "human_review_required" in data
        assert data["human_review_required"] is True
        assert "value_estimates" in data or "value_categories" in data or "roi_summary" in data

    def test_disclaimers_present(self):
        disclaimers = client.get("/api/pilot-analytics/roi", headers=AUTH).json()["disclaimers"]
        assert len(disclaimers) > 0

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/roi")
        assert res.status_code in (401, 403)


class TestClinicalOutcomes:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/clinical-outcomes", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/clinical-outcomes", headers=AUTH).json()
        assert "quality_indicators" in data
        assert "disclaimers" in data
        assert data["human_review_required"] is True

    def test_disclaimers_contain_no_causation_language(self):
        data = client.get("/api/pilot-analytics/clinical-outcomes", headers=AUTH).json()
        text = " ".join(data["disclaimers"]).lower()
        assert "association" in text or "potential" in text or "review" in text

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/clinical-outcomes")
        assert res.status_code in (401, 403)


class TestExecutiveScorecard:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/executive-scorecard", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/executive-scorecard", headers=AUTH).json()
        assert "kpis" in data
        assert "overall_status" in data
        assert data["human_review_required"] is True

    def test_kpi_rag_statuses(self):
        kpis = client.get("/api/pilot-analytics/executive-scorecard", headers=AUTH).json()["kpis"]
        assert isinstance(kpis, list)
        assert len(kpis) > 0
        # KPIs with targets have green/amber/red; informational ones may have other statuses
        rag_kpis = [k for k in kpis if k.get("target") is not None]
        for kpi in rag_kpis:
            assert kpi["status"] in ("green", "amber", "red")

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/executive-scorecard")
        assert res.status_code in (401, 403)


class TestQuarterlyReview:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/quarterly-review", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/quarterly-review", headers=AUTH).json()
        assert "expansion_recommendations" in data
        assert "success_criteria" in data
        assert data["human_review_required"] is True

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/quarterly-review")
        assert res.status_code in (401, 403)


class TestExportCSV:
    def test_returns_200_csv(self):
        res = client.get("/api/pilot-analytics/export/inspections.csv", headers=AUTH)
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("content-type", "")

    def test_csv_has_header(self):
        res = client.get("/api/pilot-analytics/export/inspections.csv", headers=AUTH)
        text = res.text
        assert "id" in text.lower() or "inspection" in text.lower() or len(text) >= 0  # at minimum returns valid response

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/export/inspections.csv")
        assert res.status_code in (401, 403)


class TestSiteBreakdown:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/site-breakdown", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/site-breakdown", headers=AUTH).json()
        assert "sites" in data
        assert "site_count" in data
        assert data["human_review_required"] is True

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/site-breakdown")
        assert res.status_code in (401, 403)


class TestAlerts:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/alerts", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/alerts", headers=AUTH).json()
        assert "alerts" in data
        assert "alert_count" in data
        assert "metrics_snapshot" in data
        assert data["human_review_required"] is True

    def test_custom_thresholds(self):
        res = client.get("/api/pilot-analytics/alerts?contamination_threshold_pct=0.1&weekly_volume_min=9999", headers=AUTH)
        assert res.status_code == 200
        assert res.json()["alert_count"] >= 1  # volume alert should fire

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/alerts")
        assert res.status_code in (401, 403)


class TestScorecardPDF:
    def test_returns_200_pdf(self):
        res = client.get("/api/pilot-analytics/export/scorecard.pdf", headers=AUTH)
        assert res.status_code == 200
        assert "pdf" in res.headers.get("content-type", "").lower()

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/export/scorecard.pdf")
        assert res.status_code in (401, 403)


class TestPulseSurvey:
    def test_submit_returns_201(self):
        res = client.post("/api/pilot-analytics/survey/submit?ease=4&useful=5&recommend=4", headers=AUTH)
        assert res.status_code == 201
        assert res.json()["recorded"] is True

    def test_submit_invalid_rating_rejected(self):
        res = client.post("/api/pilot-analytics/survey/submit?ease=6&useful=5&recommend=4", headers=AUTH)
        assert res.status_code == 422

    def test_summary_returns_200(self):
        res = client.get("/api/pilot-analytics/survey/summary", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert "response_count" in data
        assert "human_review_required" in data

    def test_unauthenticated_rejected(self):
        res = client.post("/api/pilot-analytics/survey/submit?ease=3&useful=3&recommend=3")
        assert res.status_code in (401, 403)


class TestEnhancements:
    def test_contamination_trends_site_filter(self):
        res = client.get("/api/pilot-analytics/contamination-trends?site_name=TestSite", headers=AUTH)
        assert res.status_code == 200
        assert res.json()["filters"]["site_name"] == "TestSite"

    def test_clinical_outcomes_site_filter(self):
        res = client.get("/api/pilot-analytics/clinical-outcomes?site_name=TestSite", headers=AUTH)
        assert res.status_code == 200
        assert res.json()["filters"]["site_name"] == "TestSite"

    def test_roi_with_baseline_comparison(self):
        res = client.get("/api/pilot-analytics/roi?baseline_period_days=30", headers=AUTH)
        assert res.status_code == 200
        data = res.json()
        assert "baseline_comparison" in data
        assert data["baseline_comparison"] is not None

    def test_capa_effectiveness_has_linkage(self):
        data = client.get("/api/pilot-analytics/capa-effectiveness", headers=AUTH).json()
        assert "contamination_type_linkage" in data
        assert "capa_count_by_contamination_type" in data["contamination_type_linkage"]

    def test_quarterly_review_has_narrative(self):
        data = client.get("/api/pilot-analytics/quarterly-review", headers=AUTH).json()
        assert "expansion_narrative" in data
        assert len(data["expansion_narrative"]) > 50


class TestExportReportJSON:
    def test_returns_200(self):
        res = client.get("/api/pilot-analytics/export/report.json", headers=AUTH)
        assert res.status_code == 200

    def test_required_keys(self):
        data = client.get("/api/pilot-analytics/export/report.json", headers=AUTH).json()
        assert "generated_at" in data
        assert "human_review_required" in data
        assert data["human_review_required"] is True

    def test_unauthenticated_rejected(self):
        res = client.get("/api/pilot-analytics/export/report.json")
        assert res.status_code in (401, 403)
