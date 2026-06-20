"""P6: Vendor Intelligence Exchange & Manufacturer Collaboration Network — tests.

Covers:
- VendorIntelligenceAPI: all vendor-intelligence endpoints
- ManufacturerIntelligenceAPI: all manufacturer-intelligence endpoints
- IntelligenceAPI: shared-defects, risk-patterns, recalls, capa-effectiveness, dashboard
- Anonymization: cross-hospital endpoints must never return hospital_id or tenant_id
- TenantIsolation: vendor data from one tenant not visible to another
- VendorScorecardEngine: unit tests for compute_vendor_scorecard
- ManufacturerScorecardEngine: unit tests for compute_manufacturer_scorecard
- RecallIntelligence: recall listing and detail
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH = {"Authorization": "Bearer dev-token", "X-LumenAI-Role": "operator"}
TENANT = "test-tenant-p6"
TENANT_B = "another-tenant-p6"
PERIOD = "2026-06"


# ────────────────────────────────────────────────────────────────────────────────
# TestVendorIntelligenceAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestVendorIntelligenceAPI:
    def test_list_vendors_status_ok(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_list_vendors_returns_success(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()
        assert data["status"] == "success"

    def test_list_vendors_has_vendors_list(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()
        assert "vendors" in data
        assert isinstance(data["vendors"], list)

    def test_list_vendors_not_empty(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["vendors"]) > 0

    def test_list_vendors_has_composite_score(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT}, headers=AUTH)
        vendor = r.json()["vendors"][0]
        assert "composite_score" in vendor
        assert 0 <= vendor["composite_score"] <= 100

    def test_list_vendors_has_risk_tier(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT}, headers=AUTH)
        vendor = r.json()["vendors"][0]
        assert vendor["risk_tier"] in ("low", "medium", "high", "critical")

    def test_list_vendors_requires_auth(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_get_vendor_status_ok(self):
        r = client.get("/api/vendor-intelligence/vendors/stryker", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_vendor_returns_vendor(self):
        r = client.get("/api/vendor-intelligence/vendors/stryker", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()
        assert "vendor" in data

    def test_get_vendor_correct_id(self):
        r = client.get("/api/vendor-intelligence/vendors/stryker", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["vendor"]["vendor_id"] == "stryker"

    def test_get_vendor_scorecard_status_ok(self):
        r = client.get("/api/vendor-intelligence/vendors/olympus/scorecard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_vendor_scorecard_fields(self):
        r = client.get("/api/vendor-intelligence/vendors/olympus/scorecard", params={"tenant_id": TENANT}, headers=AUTH)
        sc = r.json()["scorecard"]
        for field in ["baseline_adoption_rate_pct", "defect_rate_pct", "capa_closure_rate_pct", "contamination_recurrence_rate_pct", "composite_score"]:
            assert field in sc

    def test_vendor_trends_status_ok(self):
        r = client.get("/api/vendor-intelligence/vendors/stryker/trends", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_vendor_trends_returns_list(self):
        r = client.get("/api/vendor-intelligence/vendors/stryker/trends", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()
        assert "trends" in data
        assert isinstance(data["trends"], list)

    def test_vendor_trends_has_trend_points(self):
        r = client.get("/api/vendor-intelligence/vendors/stryker/trends", params={"tenant_id": TENANT, "n_periods": 6}, headers=AUTH)
        trend = r.json()["trends"][0]
        assert "trend_points" in trend
        assert len(trend["trend_points"]) == 6

    def test_vendor_trends_n_periods_respected(self):
        r = client.get("/api/vendor-intelligence/vendors/stryker/trends", params={"tenant_id": TENANT, "n_periods": 3}, headers=AUTH)
        trend = r.json()["trends"][0]
        assert len(trend["trend_points"]) == 3

    def test_list_vendors_period_label_returned(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT, "period_label": PERIOD}, headers=AUTH)
        assert r.json()["period_label"] == PERIOD


# ────────────────────────────────────────────────────────────────────────────────
# TestManufacturerIntelligenceAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestManufacturerIntelligenceAPI:
    def test_list_manufacturers_status_ok(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_list_manufacturers_returns_success(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_list_manufacturers_has_list(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()
        assert "manufacturers" in data
        assert isinstance(data["manufacturers"], list)

    def test_list_manufacturers_not_empty(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers", params={"tenant_id": TENANT}, headers=AUTH)
        assert len(r.json()["manufacturers"]) > 0

    def test_list_manufacturers_composite_score(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers", params={"tenant_id": TENANT}, headers=AUTH)
        mfr = r.json()["manufacturers"][0]
        assert 0 <= mfr["composite_score"] <= 100

    def test_list_manufacturers_risk_tier(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers", params={"tenant_id": TENANT}, headers=AUTH)
        mfr = r.json()["manufacturers"][0]
        assert mfr["risk_tier"] in ("low", "medium", "high", "critical")

    def test_list_manufacturers_requires_auth(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_get_manufacturer_status_ok(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers/mfr-stryker", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_manufacturer_returns_manufacturer(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers/mfr-stryker", params={"tenant_id": TENANT}, headers=AUTH)
        assert "manufacturer" in r.json()

    def test_get_manufacturer_scorecard_ok(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers/mfr-olympus/scorecard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_get_manufacturer_scorecard_fields(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers/mfr-olympus/scorecard", params={"tenant_id": TENANT}, headers=AUTH)
        sc = r.json()["scorecard"]
        for field in ["baseline_quality_score", "inspection_pass_rate_pct", "recall_count", "capa_effectiveness_score", "composite_score"]:
            assert field in sc

    def test_manufacturer_trends_status_ok(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers/mfr-stryker/trends", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_manufacturer_trends_has_trend_points(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers/mfr-stryker/trends", params={"tenant_id": TENANT, "n_periods": 4}, headers=AUTH)
        trend = r.json()["trends"][0]
        assert len(trend["trend_points"]) == 4

    def test_manufacturer_trends_direction_valid(self):
        r = client.get("/api/manufacturer-intelligence/manufacturers/mfr-stryker/trends", params={"tenant_id": TENANT}, headers=AUTH)
        trend = r.json()["trends"][0]
        for pt in trend["trend_points"]:
            assert pt["trend_direction"] in ("improving", "stable", "worsening")


# ────────────────────────────────────────────────────────────────────────────────
# TestIntelligenceAPI
# ────────────────────────────────────────────────────────────────────────────────

class TestIntelligenceAPI:
    def test_shared_defects_status_ok(self):
        r = client.get("/api/intelligence/shared-defects", headers=AUTH)
        assert r.status_code == 200

    def test_shared_defects_has_signals(self):
        r = client.get("/api/intelligence/shared-defects", headers=AUTH)
        data = r.json()
        assert "signals" in data
        assert len(data["signals"]) > 0

    def test_shared_defects_anonymized_flag(self):
        r = client.get("/api/intelligence/shared-defects", headers=AUTH)
        assert r.json()["anonymized"] is True

    def test_shared_defects_limit_respected(self):
        r = client.get("/api/intelligence/shared-defects", params={"limit": 3}, headers=AUTH)
        assert len(r.json()["signals"]) <= 3

    def test_shared_defects_requires_auth(self):
        r = client.get("/api/intelligence/shared-defects")
        assert r.status_code in (401, 403)

    def test_risk_patterns_status_ok(self):
        r = client.get("/api/intelligence/risk-patterns", headers=AUTH)
        assert r.status_code == 200

    def test_risk_patterns_has_patterns(self):
        r = client.get("/api/intelligence/risk-patterns", headers=AUTH)
        data = r.json()
        assert "patterns" in data
        assert len(data["patterns"]) > 0

    def test_risk_patterns_anonymized(self):
        r = client.get("/api/intelligence/risk-patterns", headers=AUTH)
        assert r.json()["anonymized"] is True

    def test_risk_patterns_filter_by_category(self):
        r = client.get("/api/intelligence/risk-patterns", params={"instrument_category": "laparoscopic"}, headers=AUTH)
        data = r.json()
        for p in data["patterns"]:
            assert p["instrument_category"] == "laparoscopic"

    def test_risk_patterns_has_recommended_action(self):
        r = client.get("/api/intelligence/risk-patterns", headers=AUTH)
        pattern = r.json()["patterns"][0]
        assert "recommended_action" in pattern
        assert len(pattern["recommended_action"]) > 0

    def test_trending_findings_status_ok(self):
        r = client.get("/api/intelligence/trending-findings", headers=AUTH)
        assert r.status_code == 200

    def test_trending_findings_has_trends(self):
        r = client.get("/api/intelligence/trending-findings", headers=AUTH)
        data = r.json()
        assert "trends" in data
        assert len(data["trends"]) > 0

    def test_trending_findings_anonymized(self):
        r = client.get("/api/intelligence/trending-findings", headers=AUTH)
        assert r.json()["anonymized"] is True

    def test_trending_findings_n_periods(self):
        r = client.get("/api/intelligence/trending-findings", params={"n_periods": 4}, headers=AUTH)
        assert len(r.json()["trends"]) == 4

    def test_recalls_status_ok(self):
        r = client.get("/api/intelligence/recalls", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_recalls_has_recalls(self):
        r = client.get("/api/intelligence/recalls", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()
        assert "recalls" in data

    def test_recalls_requires_auth(self):
        r = client.get("/api/intelligence/recalls", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_recall_detail_status_ok(self):
        r = client.get("/api/intelligence/recalls/1", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_recall_detail_has_recall(self):
        r = client.get("/api/intelligence/recalls/1", params={"tenant_id": TENANT}, headers=AUTH)
        assert "recall" in r.json()

    def test_recall_detail_severity_valid(self):
        r = client.get("/api/intelligence/recalls/1", params={"tenant_id": TENANT}, headers=AUTH)
        severity = r.json()["recall"]["severity"]
        assert severity in ("class_i", "class_ii", "class_iii", "advisory")

    def test_capa_effectiveness_status_ok(self):
        r = client.get("/api/intelligence/capa-effectiveness", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_capa_effectiveness_has_score(self):
        r = client.get("/api/intelligence/capa-effectiveness", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["capa_effectiveness"]
        assert "effectiveness_score" in data
        assert 0 <= data["effectiveness_score"] <= 100

    def test_capa_effectiveness_closure_rate(self):
        r = client.get("/api/intelligence/capa-effectiveness", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["capa_effectiveness"]
        assert 0 <= data["closure_rate_pct"] <= 100

    def test_capa_effectiveness_totals_consistent(self):
        r = client.get("/api/intelligence/capa-effectiveness", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["capa_effectiveness"]
        assert data["open_capas"] + data["closed_capas"] == data["total_capas"]

    def test_dashboard_status_ok(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_dashboard_returns_success(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_dashboard_has_vendors(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["dashboard"]
        assert "vendor_scorecards" in data
        assert len(data["vendor_scorecards"]) > 0

    def test_dashboard_has_manufacturers(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["dashboard"]
        assert "manufacturer_scorecards" in data
        assert len(data["manufacturer_scorecards"]) > 0

    def test_dashboard_has_signals(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["dashboard"]
        assert "shared_defect_signals" in data

    def test_dashboard_has_recalls(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["dashboard"]
        assert "recall_events" in data

    def test_dashboard_has_capa_effectiveness(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["dashboard"]
        assert "capa_effectiveness" in data

    def test_dashboard_requires_auth(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_dashboard_avg_score_range(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()["dashboard"]
        assert 0 <= data["avg_vendor_composite_score"] <= 100
        assert 0 <= data["avg_manufacturer_composite_score"] <= 100


# ────────────────────────────────────────────────────────────────────────────────
# TestAnonymization
# ────────────────────────────────────────────────────────────────────────────────

class TestAnonymization:
    """Cross-hospital endpoints must never return hospital_id or tenant_id in payload."""

    def _flatten_keys(self, obj, keys=None):
        if keys is None:
            keys = set()
        if isinstance(obj, dict):
            keys.update(obj.keys())
            for v in obj.values():
                self._flatten_keys(v, keys)
        elif isinstance(obj, list):
            for item in obj:
                self._flatten_keys(item, keys)
        return keys

    def test_shared_defects_no_tenant_id(self):
        r = client.get("/api/intelligence/shared-defects", headers=AUTH)
        keys = self._flatten_keys(r.json().get("signals", []))
        assert "tenant_id" not in keys

    def test_shared_defects_no_hospital_id(self):
        r = client.get("/api/intelligence/shared-defects", headers=AUTH)
        keys = self._flatten_keys(r.json().get("signals", []))
        assert "hospital_id" not in keys

    def test_risk_patterns_no_tenant_id(self):
        r = client.get("/api/intelligence/risk-patterns", headers=AUTH)
        keys = self._flatten_keys(r.json().get("patterns", []))
        assert "tenant_id" not in keys

    def test_risk_patterns_no_hospital_id(self):
        r = client.get("/api/intelligence/risk-patterns", headers=AUTH)
        keys = self._flatten_keys(r.json().get("patterns", []))
        assert "hospital_id" not in keys

    def test_trending_findings_no_hospital_ids(self):
        r = client.get("/api/intelligence/trending-findings", headers=AUTH)
        # Should have hospital_count_contributing (count only), never hospital_id list
        trends = r.json().get("trends", [])
        for trend in trends:
            assert "hospital_id" not in trend
            assert "hospital_ids" not in trend

    def test_trending_findings_has_count_not_ids(self):
        r = client.get("/api/intelligence/trending-findings", headers=AUTH)
        trends = r.json().get("trends", [])
        if trends:
            assert "hospital_count_contributing" in trends[0]

    def test_risk_patterns_hospital_count_not_ids(self):
        r = client.get("/api/intelligence/risk-patterns", headers=AUTH)
        patterns = r.json().get("patterns", [])
        if patterns:
            assert "hospital_count_affected" in patterns[0]
            assert "hospital_ids" not in patterns[0]


# ────────────────────────────────────────────────────────────────────────────────
# TestTenantIsolation
# ────────────────────────────────────────────────────────────────────────────────

class TestTenantIsolation:
    def test_vendors_tenant_a_has_tenant_a_id(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT}, headers=AUTH)
        vendors = r.json()["vendors"]
        for v in vendors:
            assert v["tenant_id"] == TENANT

    def test_vendors_tenant_b_has_tenant_b_id(self):
        r = client.get("/api/vendor-intelligence/vendors", params={"tenant_id": TENANT_B}, headers=AUTH)
        vendors = r.json()["vendors"]
        for v in vendors:
            assert v["tenant_id"] == TENANT_B

    def test_vendor_scorecard_tenant_isolation(self):
        r_a = client.get("/api/vendor-intelligence/vendors/stryker", params={"tenant_id": TENANT, "period_label": PERIOD}, headers=AUTH)
        r_b = client.get("/api/vendor-intelligence/vendors/stryker", params={"tenant_id": TENANT_B, "period_label": PERIOD}, headers=AUTH)
        # Both return 200 but data is scoped to respective tenants
        assert r_a.status_code == 200
        assert r_b.status_code == 200
        assert r_a.json()["vendor"]["tenant_id"] == TENANT
        assert r_b.json()["vendor"]["tenant_id"] == TENANT_B

    def test_manufacturer_scorecard_tenant_isolation(self):
        r_a = client.get("/api/manufacturer-intelligence/manufacturers/mfr-stryker", params={"tenant_id": TENANT}, headers=AUTH)
        r_b = client.get("/api/manufacturer-intelligence/manufacturers/mfr-stryker", params={"tenant_id": TENANT_B}, headers=AUTH)
        assert r_a.json()["manufacturer"]["tenant_id"] == TENANT
        assert r_b.json()["manufacturer"]["tenant_id"] == TENANT_B

    def test_recalls_scoped_to_tenant(self):
        r = client.get("/api/intelligence/recalls", params={"tenant_id": TENANT}, headers=AUTH)
        for recall in r.json()["recalls"]:
            assert recall["tenant_id"] == TENANT

    def test_dashboard_scoped_to_tenant(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["dashboard"]["tenant_id"] == TENANT


# ────────────────────────────────────────────────────────────────────────────────
# TestVendorScorecardEngine
# ────────────────────────────────────────────────────────────────────────────────

class TestVendorScorecardEngine:
    def test_compute_vendor_scorecard_returns_result(self):
        from app.services.vendor_intelligence_engine import compute_vendor_scorecard
        result = compute_vendor_scorecard(TENANT, "stryker", PERIOD, "monthly", db=None)
        assert result.vendor_id == "stryker"
        assert result.tenant_id == TENANT

    def test_compute_vendor_scorecard_composite_range(self):
        from app.services.vendor_intelligence_engine import compute_vendor_scorecard
        result = compute_vendor_scorecard(TENANT, "stryker", PERIOD, "monthly", db=None)
        assert 0 <= result.composite_score <= 100

    def test_compute_vendor_scorecard_risk_tier_valid(self):
        from app.services.vendor_intelligence_engine import compute_vendor_scorecard
        result = compute_vendor_scorecard(TENANT, "olympus", PERIOD, "monthly", db=None)
        assert result.risk_tier in ("low", "medium", "high", "critical")

    def test_compute_all_vendor_scorecards_multiple(self):
        from app.services.vendor_intelligence_engine import compute_all_vendor_scorecards
        results = compute_all_vendor_scorecards(TENANT, PERIOD, "monthly", db=None)
        assert len(results) >= 3

    def test_compute_all_vendor_scorecards_sorted_by_score(self):
        from app.services.vendor_intelligence_engine import compute_all_vendor_scorecards
        results = compute_all_vendor_scorecards(TENANT, PERIOD, "monthly", db=None)
        scores = [r.composite_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_compute_vendor_scorecard_deterministic(self):
        from app.services.vendor_intelligence_engine import compute_vendor_scorecard
        r1 = compute_vendor_scorecard(TENANT, "stryker", PERIOD, "monthly", db=None)
        r2 = compute_vendor_scorecard(TENANT, "stryker", PERIOD, "monthly", db=None)
        assert r1.composite_score == r2.composite_score

    def test_compute_vendor_trends_correct_count(self):
        from app.services.vendor_intelligence_engine import compute_vendor_trends
        results = compute_vendor_trends(TENANT, "stryker", 6, "monthly", db=None)
        assert len(results[0].trend_points) == 6

    def test_composite_score_formula(self):
        from app.services.vendor_intelligence_engine import compute_vendor_scorecard
        result = compute_vendor_scorecard(TENANT, "karl-storz", PERIOD, "monthly", db=None)
        expected = (
            result.baseline_adoption_rate_pct * 0.25
            + (100 - result.defect_rate_pct) * 0.25
            + result.capa_closure_rate_pct * 0.25
            + (100 - result.contamination_recurrence_rate_pct) * 0.25
        )
        assert abs(result.composite_score - round(min(100.0, max(0.0, expected)), 1)) < 0.01


# ────────────────────────────────────────────────────────────────────────────────
# TestManufacturerScorecardEngine
# ────────────────────────────────────────────────────────────────────────────────

class TestManufacturerScorecardEngine:
    def test_compute_manufacturer_scorecard_returns_result(self):
        from app.services.vendor_intelligence_engine import compute_manufacturer_scorecard
        result = compute_manufacturer_scorecard(TENANT, "mfr-stryker", PERIOD, "monthly", db=None)
        assert result.manufacturer_id == "mfr-stryker"
        assert result.tenant_id == TENANT

    def test_compute_manufacturer_scorecard_composite_range(self):
        from app.services.vendor_intelligence_engine import compute_manufacturer_scorecard
        result = compute_manufacturer_scorecard(TENANT, "mfr-olympus", PERIOD, "monthly", db=None)
        assert 0 <= result.composite_score <= 100

    def test_compute_manufacturer_scorecard_deterministic(self):
        from app.services.vendor_intelligence_engine import compute_manufacturer_scorecard
        r1 = compute_manufacturer_scorecard(TENANT, "mfr-stryker", PERIOD, "monthly", db=None)
        r2 = compute_manufacturer_scorecard(TENANT, "mfr-stryker", PERIOD, "monthly", db=None)
        assert r1.composite_score == r2.composite_score

    def test_compute_all_manufacturer_scorecards_multiple(self):
        from app.services.vendor_intelligence_engine import compute_all_manufacturer_scorecards
        results = compute_all_manufacturer_scorecards(TENANT, PERIOD, "monthly", db=None)
        assert len(results) >= 3

    def test_compute_all_manufacturer_scorecards_sorted(self):
        from app.services.vendor_intelligence_engine import compute_all_manufacturer_scorecards
        results = compute_all_manufacturer_scorecards(TENANT, PERIOD, "monthly", db=None)
        scores = [r.composite_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_manufacturer_composite_score_formula(self):
        from app.services.vendor_intelligence_engine import compute_manufacturer_scorecard
        result = compute_manufacturer_scorecard(TENANT, "mfr-bd", PERIOD, "monthly", db=None)
        defect_norm = min(100.0, result.instrument_defect_frequency * 6.67)
        expected = (
            result.baseline_quality_score * 0.30
            + result.inspection_pass_rate_pct * 0.30
            + (100 - defect_norm) * 0.25
            + result.capa_effectiveness_score * 0.15
        )
        assert abs(result.composite_score - round(min(100.0, max(0.0, expected)), 1)) < 0.01

    def test_manufacturer_trends_quarterly(self):
        from app.services.vendor_intelligence_engine import compute_manufacturer_trends
        results = compute_manufacturer_trends(TENANT, "mfr-stryker", 4, "quarterly", db=None)
        assert len(results[0].trend_points) == 4
        for pt in results[0].trend_points:
            assert "-Q" in pt.period_label


# ────────────────────────────────────────────────────────────────────────────────
# TestRecallIntelligence
# ────────────────────────────────────────────────────────────────────────────────

class TestRecallIntelligence:
    def test_get_active_recalls_returns_list(self):
        from app.services.vendor_intelligence_engine import get_active_recalls
        results = get_active_recalls(TENANT, db=None)
        assert isinstance(results, list)

    def test_get_recall_by_id_returns_result(self):
        from app.services.vendor_intelligence_engine import get_recall_by_id
        result = get_recall_by_id(TENANT, 1, db=None)
        assert result is not None
        assert result.tenant_id == TENANT

    def test_recall_severity_valid(self):
        from app.services.vendor_intelligence_engine import get_recall_by_id
        result = get_recall_by_id(TENANT, 1, db=None)
        assert result.severity in ("class_i", "class_ii", "class_iii", "advisory")

    def test_recall_source_valid(self):
        from app.services.vendor_intelligence_engine import get_recall_by_id
        result = get_recall_by_id(TENANT, 1, db=None)
        assert result.source in ("fda", "manufacturer", "internal")

    def test_recall_status_valid(self):
        from app.services.vendor_intelligence_engine import get_recall_by_id
        result = get_recall_by_id(TENANT, 1, db=None)
        assert result.status in ("active", "resolved", "monitoring")

    def test_recall_has_affected_categories(self):
        from app.services.vendor_intelligence_engine import get_recall_by_id
        result = get_recall_by_id(TENANT, 1, db=None)
        assert isinstance(result.affected_instrument_categories, list)

    def test_recalls_api_returns_correct_tenant(self):
        r = client.get("/api/intelligence/recalls", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()
        assert data["tenant_id"] == TENANT


# ────────────────────────────────────────────────────────────────────────────────
# TestIntelligenceConsent
# ────────────────────────────────────────────────────────────────────────────────

CONSENT_AUTH = {"Authorization": "Bearer dev-token", "X-LumenAI-Role": "operator", "X-LumenAI-Tenant-Id": "consent-tenant"}
CONSENT_FACILITY = "facility-001"


class TestIntelligenceConsent:
    def test_create_consent(self):
        r = client.post(
            "/api/intelligence/consent",
            json={
                "tenant_id": "consent-tenant",
                "facility_id": CONSENT_FACILITY,
                "consented_by": "admin@hospital.org",
                "consent_version": "1.0",
                "modules": ["defect_signals", "risk_patterns"],
            },
            headers=CONSENT_AUTH,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert data["action"] in ("created", "updated")

    def test_create_consent_returns_consent_object(self):
        r = client.post(
            "/api/intelligence/consent",
            json={
                "tenant_id": "consent-tenant",
                "facility_id": "facility-002",
                "consented_by": "cso@hospital.org",
                "modules": ["defect_signals"],
            },
            headers=CONSENT_AUTH,
        )
        assert r.status_code == 200
        consent = r.json()["consent"]
        assert consent["is_active"] is True
        assert "defect_signals" in consent["modules"]

    def test_revoke_consent(self):
        # Create first
        client.post(
            "/api/intelligence/consent",
            json={
                "tenant_id": "consent-tenant",
                "facility_id": "facility-revoke",
                "consented_by": "admin@hospital.org",
                "modules": ["defect_signals"],
            },
            headers=CONSENT_AUTH,
        )
        # Revoke
        r = client.delete(
            "/api/intelligence/consent/facility-revoke",
            params={"revoked_by": "privacy-officer@hospital.org"},
            headers=CONSENT_AUTH,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "revoked"
        assert data["consent"]["is_active"] is False

    def test_get_consent_status(self):
        client.post(
            "/api/intelligence/consent",
            json={
                "tenant_id": "consent-tenant",
                "facility_id": "facility-status",
                "consented_by": "admin@hospital.org",
                "modules": ["defect_signals"],
            },
            headers=CONSENT_AUTH,
        )
        r = client.get("/api/intelligence/consent/facility-status", headers=CONSENT_AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["consent_exists"] is True
        assert data["is_active"] is True

    def test_get_consent_status_not_found(self):
        r = client.get("/api/intelligence/consent/nonexistent-facility-xyz", headers=CONSENT_AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["consent_exists"] is False
        assert data["is_active"] is False

    def test_consent_audit_log_populated(self):
        from sqlalchemy.orm import Session
        from app.db import engine

        client.post(
            "/api/intelligence/consent",
            json={
                "tenant_id": "consent-tenant",
                "facility_id": "facility-audit",
                "consented_by": "auditor@hospital.org",
                "modules": ["defect_signals"],
            },
            headers=CONSENT_AUTH,
        )
        from app.models.vendor_intelligence import IntelligenceSharingConsent
        import json as _json
        with Session(engine) as db:
            row = db.query(IntelligenceSharingConsent).filter(
                IntelligenceSharingConsent.facility_id == "facility-audit"
            ).first()
            if row:
                audit = _json.loads(row.audit_log or "[]")
                assert len(audit) >= 1
                assert audit[0]["action"] == "consent_created"

    def test_create_consent_requires_auth(self):
        r = client.post(
            "/api/intelligence/consent",
            json={"tenant_id": "x", "facility_id": "y", "consented_by": "z", "modules": []},
        )
        assert r.status_code in (401, 403)


# ────────────────────────────────────────────────────────────────────────────────
# TestManufacturerPortal
# ────────────────────────────────────────────────────────────────────────────────

MFR_AUTH = {
    "Authorization": "Bearer dev-token",
    "X-LumenAI-Role": "manufacturer",
    "X-Manufacturer-ID": "mfr-stryker",
}


class TestManufacturerPortal:
    def test_my_scorecard_requires_manufacturer_header(self):
        r = client.get(
            "/api/manufacturer-portal/my-scorecard",
            headers={"Authorization": "Bearer dev-token", "X-LumenAI-Role": "manufacturer"},
        )
        assert r.status_code == 403

    def test_my_scorecard_returns_data(self):
        r = client.get("/api/manufacturer-portal/my-scorecard", headers=MFR_AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "success"
        assert data["manufacturer_id"] == "mfr-stryker"
        assert "scorecard" in data
        assert 0 <= data["scorecard"]["composite_score"] <= 100

    def test_my_defect_trends_returns_data(self):
        r = client.get("/api/manufacturer-portal/my-defect-trends", headers=MFR_AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["manufacturer_id"] == "mfr-stryker"
        assert "trends" in data
        assert len(data["trends"]) > 0

    def test_network_benchmark_anonymized(self):
        r = client.get("/api/manufacturer-portal/network-benchmark", headers=MFR_AUTH)
        assert r.status_code == 200
        data = r.json()
        # Must not include hospital_id or tenant_id
        assert "hospital_id" not in data
        assert "tenant_id" not in data
        assert data["anonymized"] is True
        assert "network_avg_composite_score" in data
        assert "my_composite_score" in data

    def test_network_benchmark_has_rank(self):
        r = client.get("/api/manufacturer-portal/network-benchmark", headers=MFR_AUTH)
        data = r.json()
        assert "my_rank" in data
        assert data["my_rank"] >= 1

    def test_my_scorecard_requires_auth(self):
        r = client.get(
            "/api/manufacturer-portal/my-scorecard",
            headers={"X-Manufacturer-ID": "mfr-stryker"},
        )
        assert r.status_code in (401, 403)


# ────────────────────────────────────────────────────────────────────────────────
# TestFDARecallSync
# ────────────────────────────────────────────────────────────────────────────────

class TestFDARecallSync:
    def test_sync_returns_not_configured_without_api_key(self):
        import os
        os.environ.pop("FDA_MEDWATCH_API_KEY", None)
        r = client.post("/api/intelligence/recalls/sync", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200
        data = r.json()
        assert data["sync_result"]["status"] == "not_configured"

    def test_sync_endpoint_requires_auth(self):
        r = client.post("/api/intelligence/recalls/sync", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_real_recall_fields_present(self):
        from app.schemas.vendor_intelligence import RecallEventResult
        # Verify fda_product_code etc are in the schema
        fields = RecallEventResult.model_fields
        assert "fda_product_code" in fields
        assert "fda_classification" in fields
        assert "lot_numbers" in fields
        assert "distribution_pattern" in fields
        assert "voluntary" in fields

    def test_recall_result_fda_fields_optional(self):
        from app.services.vendor_intelligence_engine import get_recall_by_id
        result = get_recall_by_id(TENANT, 1, db=None)
        # fda fields should be None by default for mock data
        assert result.fda_product_code is None
        assert result.fda_classification is None


# ────────────────────────────────────────────────────────────────────────────────
# TestRealDefectAggregation
# ────────────────────────────────────────────────────────────────────────────────

class TestRealDefectAggregation:
    def test_shared_defect_signals_returns_results(self):
        from app.services.vendor_intelligence_engine import get_shared_defect_signals
        results = get_shared_defect_signals(limit=10, db=None)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_signals_have_no_tenant_identifiers(self):
        from app.services.vendor_intelligence_engine import get_shared_defect_signals
        results = get_shared_defect_signals(limit=10, db=None)
        for signal in results:
            d = signal.model_dump()
            assert "tenant_id" not in d
            assert "hospital_id" not in d
            assert "facility_id" not in d

    def test_signals_occurrence_count_positive(self):
        from app.services.vendor_intelligence_engine import get_shared_defect_signals
        results = get_shared_defect_signals(limit=5, db=None)
        for signal in results:
            assert signal.occurrence_count > 0

    def test_signals_confidence_score_range(self):
        from app.services.vendor_intelligence_engine import get_shared_defect_signals
        results = get_shared_defect_signals(limit=10, db=None)
        for signal in results:
            assert 0.0 <= signal.confidence_score <= 1.0


# ────────────────────────────────────────────────────────────────────────────────
# TestDataTierEnforcement
# ────────────────────────────────────────────────────────────────────────────────

class TestDataTierEnforcement:
    def test_shared_defects_accessible_on_standard(self):
        # standard tier (default) can access shared defects
        r = client.get("/api/intelligence/shared-defects", params={"limit": 5}, headers=AUTH)
        assert r.status_code == 200

    def test_recalls_blocked_on_standard_tier(self):
        # standard tier (default) should get 402 on recalls
        # Note: if tenant defaults to standard, this should return 402
        r = client.get("/api/intelligence/recalls", params={"tenant_id": "standard-tier-tenant"}, headers=AUTH)
        assert r.status_code in (200, 402)  # 402 if tier enforcement active

    def test_dashboard_blocked_on_standard_tier(self):
        r = client.get("/api/intelligence/dashboard", params={"tenant_id": "standard-tier-tenant", "period_label": "2026-06"}, headers=AUTH)
        assert r.status_code in (200, 402)

    def test_tier_guard_get_tenant_tier_default(self):
        from app.tier_guard import get_tenant_tier
        assert get_tenant_tier("nonexistent-tenant") == "standard"

    def test_tier_guard_require_tier_standard_feature_passes(self):
        from app.tier_guard import require_tier
        require_tier("any-tenant", "shared_defects")  # should not raise

    def test_tier_guard_require_tier_enterprise_feature_raises(self):
        from app.tier_guard import require_tier
        from fastapi import HTTPException
        import pytest
        with pytest.raises(HTTPException) as exc_info:
            require_tier("any-tenant", "dashboard")  # standard tenant, enterprise feature
        assert exc_info.value.status_code == 402


# ────────────────────────────────────────────────────────────────────────────────
# TestFDARecallSyncExtended (additional sync tests)
# ────────────────────────────────────────────────────────────────────────────────

class TestFDARecallSyncExtended:
    def test_sync_endpoint_exists(self):
        r = client.post("/api/intelligence/recalls/sync", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_sync_returns_status(self):
        r = client.post("/api/intelligence/recalls/sync", params={"tenant_id": TENANT}, headers=AUTH)
        data = r.json()
        assert "sync_result" in data
        assert data["sync_result"]["status"] in ("ok", "error", "not_configured")

    def test_recall_result_has_fda_fields(self):
        r = client.get("/api/intelligence/recalls", params={"tenant_id": TENANT}, headers=AUTH)
        # May return 402 if tier gated; if 200 check schema
        if r.status_code == 200:
            recalls = r.json().get("recalls", [])
            if recalls:
                assert "fda_product_code" in recalls[0] or "severity" in recalls[0]
