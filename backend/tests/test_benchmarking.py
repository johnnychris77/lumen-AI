"""P5: Tests for Enterprise Multi-Hospital Benchmarking & Portfolio Intelligence."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

# ── Module-level client ───────────────────────────────────────────────────────

client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer dev-token", "X-LumenAI-Role": "operator"}


# ── Hospital benchmarks ───────────────────────────────────────────────────────

class TestHospitalBenchmarks:
    def test_list_hospital_benchmarks_returns_list(self):
        resp = client.get(
            "/api/enterprise/benchmarks/hospitals",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_post_hospital_benchmarks(self):
        resp = client.post(
            "/api/enterprise/benchmarks/hospitals",
            json={"tenant_id": "demo-tenant", "hospital_ids": [], "period": {"period_type": "monthly"}},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_hospital_benchmark_fields(self):
        resp = client.get(
            "/api/enterprise/benchmarks/hospitals",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        if data:
            h = data[0]
            assert "hospital_id" in h
            assert "hospital_name" in h
            assert "period_label" in h
            assert "contamination_rate_pct" in h
            assert "avg_cleanliness_score" in h
            assert "compliance_score" in h
            assert "risk_tier" in h

    def test_hospital_benchmark_scores_in_range(self):
        resp = client.get(
            "/api/enterprise/benchmarks/hospitals",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        for h in resp.json():
            assert 0.0 <= h["avg_cleanliness_score"] <= 100.0
            assert h["contamination_rate_pct"] >= 0.0
            assert 0.0 <= h["compliance_score"] <= 100.0

    def test_get_single_hospital_benchmark(self):
        # First get the list to find a valid hospital_id
        list_resp = client.get(
            "/api/enterprise/benchmarks/hospitals",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert list_resp.status_code == 200
        hospitals = list_resp.json()
        if not hospitals:
            pytest.skip("No hospitals returned")

        hid = hospitals[0]["hospital_id"]
        resp = client.get(
            f"/api/enterprise/benchmarks/hospitals/{hid}",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["hospital_id"] == hid

    def test_get_nonexistent_hospital_returns_placeholder(self):
        resp = client.get(
            "/api/enterprise/benchmarks/hospitals/nonexistent-hospital-xyz",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hospital_id"] == "nonexistent-hospital-xyz"

    def test_hospital_benchmarks_quarterly(self):
        resp = client.get(
            "/api/enterprise/benchmarks/hospitals",
            params={"tenant_id": "demo-tenant", "period_type": "quarterly"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "Q" in data[0]["period_label"]

    def test_hospital_benchmarks_annual(self):
        resp = client.get(
            "/api/enterprise/benchmarks/hospitals",
            params={"tenant_id": "demo-tenant", "period_type": "annual"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_hospital_benchmarks_requires_auth(self):
        resp = client.get("/api/enterprise/benchmarks/hospitals")
        assert resp.status_code in (401, 403)

    def test_hospital_risk_tiers_valid(self):
        resp = client.get(
            "/api/enterprise/benchmarks/hospitals",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        valid_tiers = {"low", "medium", "high", "critical"}
        for h in resp.json():
            assert h["risk_tier"] in valid_tiers


# ── Vendor benchmarks ─────────────────────────────────────────────────────────

class TestVendorBenchmarks:
    def test_list_vendor_benchmarks(self):
        resp = client.get(
            "/api/enterprise/benchmarks/vendors",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_post_vendor_benchmarks(self):
        resp = client.post(
            "/api/enterprise/benchmarks/vendors",
            json={"tenant_id": "demo-tenant", "vendor_ids": [], "period": {"period_type": "monthly"}},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_vendor_benchmark_fields(self):
        resp = client.get(
            "/api/enterprise/benchmarks/vendors",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        if data:
            v = data[0]
            assert "vendor_id" in v
            assert "vendor_name" in v
            assert "baseline_adoption_rate_pct" in v
            assert "defect_rate_pct" in v
            assert "vendor_score" in v
            assert "risk_tier" in v

    def test_vendor_scores_in_range(self):
        resp = client.get(
            "/api/enterprise/benchmarks/vendors",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        for v in resp.json():
            assert 0.0 <= v["vendor_score"] <= 100.0
            assert 0.0 <= v["baseline_adoption_rate_pct"] <= 100.0
            assert v["defect_rate_pct"] >= 0.0

    def test_vendor_benchmarks_requires_auth(self):
        resp = client.get("/api/enterprise/benchmarks/vendors")
        assert resp.status_code in (401, 403)


# ── Enterprise rollup ─────────────────────────────────────────────────────────

class TestEnterpriseRollup:
    def test_get_rollup(self):
        resp = client.get(
            "/api/enterprise/benchmarks/rollup",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant_id" in data
        assert "period_label" in data
        assert "total_hospitals" in data

    def test_post_rollup(self):
        resp = client.post(
            "/api/enterprise/benchmarks/rollup",
            json={"tenant_id": "demo-tenant", "period": {"period_type": "monthly"}},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == "demo-tenant"

    def test_rollup_quality_fields(self):
        resp = client.get(
            "/api/enterprise/benchmarks/rollup",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "avg_cleanliness_score" in data
        assert "avg_contamination_rate_pct" in data
        assert "total_blood_findings" in data
        assert "pct_hospitals_compliant" in data
        assert "baseline_adoption_rate_pct" in data

    def test_rollup_risk_distribution(self):
        resp = client.get(
            "/api/enterprise/benchmarks/rollup",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "hospitals_low_risk" in data
        assert "hospitals_medium_risk" in data
        assert "hospitals_high_risk" in data
        assert "hospitals_critical_risk" in data

    def test_rollup_leaderboards(self):
        resp = client.get(
            "/api/enterprise/benchmarks/rollup",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["top_hospitals"], list)
        assert isinstance(data["bottom_hospitals"], list)
        assert isinstance(data["top_vendors"], list)

    def test_rollup_requires_auth(self):
        resp = client.get("/api/enterprise/benchmarks/rollup")
        assert resp.status_code in (401, 403)

    def test_rollup_cleanliness_in_range(self):
        resp = client.get(
            "/api/enterprise/benchmarks/rollup",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 0.0 <= data["avg_cleanliness_score"] <= 100.0
        assert data["avg_contamination_rate_pct"] >= 0.0
        assert 0.0 <= data["pct_hospitals_compliant"] <= 100.0


# ── Executive dashboard ───────────────────────────────────────────────────────

class TestExecutiveDashboard:
    def test_executive_dashboard_shape(self):
        resp = client.get(
            "/api/enterprise/benchmarks/executive-dashboard",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tenant_id" in data
        assert "generated_at" in data
        assert "period_label" in data

    def test_executive_dashboard_headline_kpis(self):
        resp = client.get(
            "/api/enterprise/benchmarks/executive-dashboard",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_hospitals" in data
        assert "portfolio_cleanliness_score" in data
        assert "blood_detections_mtd" in data
        assert "baseline_adoption_rate_pct" in data
        assert "pct_hospitals_compliant" in data

    def test_executive_dashboard_risk_snapshot(self):
        resp = client.get(
            "/api/enterprise/benchmarks/executive-dashboard",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "hospitals_at_critical_risk" in data
        assert "hospitals_at_high_risk" in data

    def test_executive_dashboard_trend_deltas(self):
        resp = client.get(
            "/api/enterprise/benchmarks/executive-dashboard",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "cleanliness_score_delta" in data
        assert "contamination_rate_delta" in data
        assert "baseline_adoption_delta" in data

    def test_executive_dashboard_trend_series(self):
        resp = client.get(
            "/api/enterprise/benchmarks/executive-dashboard",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["contamination_trend"], list)
        assert isinstance(data["cleanliness_trend"], list)
        assert isinstance(data["baseline_adoption_trend"], list)

    def test_executive_dashboard_leaderboards(self):
        resp = client.get(
            "/api/enterprise/benchmarks/executive-dashboard",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["top_performing_hospitals"], list)
        assert isinstance(data["highest_risk_hospitals"], list)
        assert isinstance(data["top_vendors"], list)

    def test_executive_dashboard_role_insights(self):
        resp = client.get(
            "/api/enterprise/benchmarks/executive-dashboard",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["spd_director_insights"], list)
        assert isinstance(data["quality_leader_insights"], list)
        assert isinstance(data["market_director_insights"], list)
        # Insights should have meaningful content
        all_insights = (
            data["spd_director_insights"]
            + data["quality_leader_insights"]
            + data["market_director_insights"]
        )
        assert len(all_insights) > 0

    def test_executive_dashboard_requires_auth(self):
        resp = client.get("/api/enterprise/benchmarks/executive-dashboard")
        assert resp.status_code in (401, 403)


# ── Trend series ──────────────────────────────────────────────────────────────

class TestTrendSeries:
    def test_enterprise_contamination_trend(self):
        resp = client.get(
            "/api/enterprise/benchmarks/trends/enterprise/all/contamination_rate_pct",
            params={"tenant_id": "demo-tenant", "n_periods": 6},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["subject_id"] == "all"
        assert data["metric_name"] == "contamination_rate_pct"
        assert isinstance(data["points"], list)

    def test_trend_n_periods_respected(self):
        resp = client.get(
            "/api/enterprise/benchmarks/trends/enterprise/all/avg_cleanliness_score",
            params={"tenant_id": "demo-tenant", "n_periods": 4},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        points = resp.json()["points"]
        assert len(points) == 4

    def test_trend_point_fields(self):
        resp = client.get(
            "/api/enterprise/benchmarks/trends/enterprise/all/baseline_adoption_rate_pct",
            params={"tenant_id": "demo-tenant", "n_periods": 3},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        points = resp.json()["points"]
        assert len(points) == 3
        for p in points:
            assert "period_label" in p
            assert "period_start" in p
            assert "value" in p
            assert isinstance(p["value"], float)

    def test_trend_n_periods_clamped(self):
        # n_periods is clamped to [2, 24]
        resp = client.get(
            "/api/enterprise/benchmarks/trends/enterprise/all/contamination_rate_pct",
            params={"tenant_id": "demo-tenant", "n_periods": 1},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        points = resp.json()["points"]
        assert len(points) >= 2

    def test_hospital_trend(self):
        resp = client.get(
            "/api/enterprise/benchmarks/trends/hospital/hosp-001/avg_cleanliness_score",
            params={"tenant_id": "demo-tenant", "n_periods": 6},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["subject_id"] == "hosp-001"

    def test_trend_requires_auth(self):
        resp = client.get(
            "/api/enterprise/benchmarks/trends/enterprise/all/contamination_rate_pct"
        )
        assert resp.status_code in (401, 403)


# ── Board reports ─────────────────────────────────────────────────────────────

class TestBoardReports:
    def test_generate_monthly_report(self):
        resp = client.post(
            "/api/enterprise/benchmarks/reports/generate",
            json={"tenant_id": "demo-tenant", "report_type": "monthly", "publish": False},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_type"] == "monthly"
        assert data["tenant_id"] == "demo-tenant"

    def test_generate_quarterly_report(self):
        resp = client.post(
            "/api/enterprise/benchmarks/reports/generate",
            json={"tenant_id": "demo-tenant", "report_type": "quarterly", "publish": False},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_type"] == "quarterly"

    def test_generate_annual_report(self):
        resp = client.post(
            "/api/enterprise/benchmarks/reports/generate",
            json={"tenant_id": "demo-tenant", "report_type": "annual", "publish": False},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_type"] == "annual"

    def test_report_fields(self):
        resp = client.post(
            "/api/enterprise/benchmarks/reports/generate",
            json={"tenant_id": "demo-tenant", "report_type": "monthly"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "title" in data
        assert "executive_summary" in data
        assert isinstance(data["key_findings"], list)
        assert isinstance(data["recommendations"], list)
        assert "status" in data

    def test_report_has_key_findings(self):
        resp = client.post(
            "/api/enterprise/benchmarks/reports/generate",
            json={"tenant_id": "demo-tenant", "report_type": "monthly"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["key_findings"]) > 0
        assert len(data["recommendations"]) > 0

    def test_report_draft_status(self):
        resp = client.post(
            "/api/enterprise/benchmarks/reports/generate",
            json={"tenant_id": "demo-tenant", "report_type": "monthly", "publish": False},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "draft"

    def test_list_reports(self):
        resp = client.get(
            "/api/enterprise/benchmarks/reports/monthly",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_report_by_period(self):
        # Generate first, then retrieve
        gen_resp = client.post(
            "/api/enterprise/benchmarks/reports/generate",
            json={"tenant_id": "demo-tenant", "report_type": "monthly", "period_label": "2025-01"},
            headers=AUTH_HEADERS,
        )
        assert gen_resp.status_code == 200

        resp = client.get(
            "/api/enterprise/benchmarks/reports/monthly/2025-01",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_label"] == "2025-01"

    def test_report_requires_auth(self):
        resp = client.post(
            "/api/enterprise/benchmarks/reports/generate",
            json={"tenant_id": "demo-tenant", "report_type": "monthly"},
        )
        assert resp.status_code in (401, 403)


# ── KPI summary ───────────────────────────────────────────────────────────────

class TestKPISummary:
    def test_kpi_summary_shape(self):
        resp = client.get(
            "/api/enterprise/benchmarks/kpi-summary",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "period_label" in data
        assert "total_hospitals" in data
        assert "total_inspections" in data
        assert "portfolio_cleanliness_score" in data
        assert "contamination_rate_pct" in data

    def test_kpi_summary_risk_fields(self):
        resp = client.get(
            "/api/enterprise/benchmarks/kpi-summary",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "hospitals_critical_risk" in data
        assert "hospitals_high_risk" in data

    def test_kpi_summary_leaderboard_snapshot(self):
        resp = client.get(
            "/api/enterprise/benchmarks/kpi-summary",
            params={"tenant_id": "demo-tenant"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        # top_hospital and top_vendor may be None if no data
        assert "top_hospital" in data
        assert "top_vendor" in data

    def test_kpi_summary_requires_auth(self):
        resp = client.get("/api/enterprise/benchmarks/kpi-summary")
        assert resp.status_code in (401, 403)


# ── Engine unit tests ─────────────────────────────────────────────────────────

class TestBenchmarkEngine:
    def test_current_period_label_monthly(self):
        from app.services.benchmark_engine import _current_period_label
        label = _current_period_label("monthly")
        import re
        assert re.match(r"^\d{4}-\d{2}$", label)

    def test_current_period_label_quarterly(self):
        from app.services.benchmark_engine import _current_period_label
        label = _current_period_label("quarterly")
        assert "Q" in label

    def test_current_period_label_annual(self):
        from app.services.benchmark_engine import _current_period_label
        label = _current_period_label("annual")
        import re
        assert re.match(r"^\d{4}$", label)

    def test_period_bounds_monthly(self):
        from app.services.benchmark_engine import _period_bounds
        start, end = _period_bounds("2025-06", "monthly")
        assert start.year == 2025
        assert start.month == 6
        assert end > start

    def test_period_bounds_quarterly(self):
        from app.services.benchmark_engine import _period_bounds
        start, end = _period_bounds("2025-Q2", "quarterly")
        assert start.month == 4
        assert end.month == 7 or end.month == 6

    def test_compute_hospital_benchmarks_returns_list(self):
        from app.services.benchmark_engine import compute_hospital_benchmarks
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            results = compute_hospital_benchmarks(
                tenant_id="demo-tenant",
                period_label="2025-06",
                period_type="monthly",
                db=db,
            )
            assert isinstance(results, list)
        finally:
            db.close()

    def test_compute_vendor_benchmarks_returns_list(self):
        from app.services.benchmark_engine import compute_vendor_benchmarks
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            results = compute_vendor_benchmarks(
                tenant_id="demo-tenant",
                period_label="2025-06",
                period_type="monthly",
                db=db,
            )
            assert isinstance(results, list)
        finally:
            db.close()

    def test_compute_enterprise_rollup(self):
        from app.services.benchmark_engine import compute_enterprise_rollup
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            result = compute_enterprise_rollup(
                tenant_id="demo-tenant",
                period_label="2025-06",
                period_type="monthly",
                db=db,
            )
            assert result.tenant_id == "demo-tenant"
            assert result.period_label == "2025-06"
            assert isinstance(result.top_hospitals, list)
        finally:
            db.close()

    def test_compute_trend_series_length(self):
        from app.services.benchmark_engine import compute_trend_series
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            points = compute_trend_series(
                tenant_id="demo-tenant",
                subject_type="enterprise",
                subject_id="all",
                metric_name="contamination_rate_pct",
                n_periods=6,
                period_type="monthly",
                db=db,
            )
            assert len(points) == 6
        finally:
            db.close()

    def test_trend_values_nonnegative(self):
        from app.services.benchmark_engine import compute_trend_series
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            points = compute_trend_series(
                tenant_id="demo-tenant",
                subject_type="enterprise",
                subject_id="all",
                metric_name="avg_cleanliness_score",
                n_periods=4,
                period_type="monthly",
                db=db,
            )
            for p in points:
                assert p.value >= 0.0
        finally:
            db.close()

    def test_generate_board_report_fields(self):
        from app.services.benchmark_engine import generate_board_report
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            report = generate_board_report(
                tenant_id="demo-tenant",
                period_label="2025-06",
                period_type="monthly",
                report_type="monthly",
                db=db,
            )
            assert report.tenant_id == "demo-tenant"
            assert len(report.key_findings) > 0
            assert len(report.recommendations) > 0
            assert report.executive_summary != ""
        finally:
            db.close()

    def test_executive_dashboard_insights_generated(self):
        from app.services.benchmark_engine import compute_executive_dashboard
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            dashboard = compute_executive_dashboard(
                tenant_id="demo-tenant",
                period_label="2025-06",
                period_type="monthly",
                db=db,
            )
            assert len(dashboard.spd_director_insights) > 0
            assert len(dashboard.quality_leader_insights) > 0
            assert len(dashboard.market_director_insights) > 0
        finally:
            db.close()
