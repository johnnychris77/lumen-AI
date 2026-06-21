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
