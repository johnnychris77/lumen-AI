"""Regression test for a production bug: GET /api/analytics/kpi-summary and
GET /api/analytics/powerbi both 404'd because app/routes/analytics.py's
router was defined but never registered in main.py — ~15 frontend pages
(dashboards, executive consoles, NotificationProvider) called
/api/analytics/kpi-summary with no backend route at all.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}


class TestAnalyticsRouterRegistered:
    def test_kpi_summary_endpoint_exists(self):
        r = client.get("/api/analytics/kpi-summary", headers=AUTH_ADMIN)
        assert r.status_code == 200, r.text

    def test_powerbi_endpoint_exists(self):
        r = client.get("/api/analytics/powerbi", headers=AUTH_ADMIN)
        assert r.status_code == 200, r.text


class TestKpiSummaryShape:
    def test_kpi_summary_has_expected_real_fields(self):
        r = client.get("/api/analytics/kpi-summary", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "total_inspections", "inspections_this_week", "high_risk_findings",
            "open_findings", "review_backlog", "images_collected",
            "total_baselines", "baselines_approved", "baseline_coverage_pct",
            "total_capas", "open_capas", "completed_capas", "total_users",
            "human_review_required",
        ):
            assert key in body

    def test_kpi_summary_readable_by_viewer(self):
        r = client.get("/api/analytics/kpi-summary", headers=AUTH_VIEWER)
        assert r.status_code == 200

    def test_kpi_summary_no_fabricated_fields_present(self):
        # Fields that aren't honestly computable yet must be absent, not
        # fabricated with a fake value.
        r = client.get("/api/analytics/kpi-summary", headers=AUTH_ADMIN)
        body = r.json()
        for key in ("active_users", "review_turnaround_hrs", "login_frequency_per_week", "adoption_rate_pct"):
            assert key not in body
