"""P17 — Commercial Launch, Sales Enablement & Market Expansion tests."""
import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token"}
TS = str(int(time.time()))[-6:]


# ---------------------------------------------------------------------------
# Phase 1 — Packaging
# ---------------------------------------------------------------------------

class TestPackaging:
    def test_list_packages(self):
        r = client.get("/api/commercial/packages", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 4
        tiers = {p["tier"] for p in body["packages"]}
        assert tiers == {"starter", "professional", "enterprise", "health_system"}

    def test_get_package(self):
        r = client.get("/api/commercial/packages/enterprise", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["tier"] == "enterprise"

    def test_get_unknown_package_404(self):
        r = client.get("/api/commercial/packages/nope", headers=AUTH)
        assert r.status_code == 404

    def test_health_system_has_governance(self):
        r = client.get("/api/commercial/packages/health_system", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert "anonymized" in body["data_governance"].lower()

    def test_packages_require_auth(self):
        r = client.get("/api/commercial/packages")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Phase 2 — Pricing
# ---------------------------------------------------------------------------

class TestPricing:
    def test_hospital_pricing(self):
        r = client.get("/api/commercial/pricing/hospital", headers=AUTH)
        assert r.status_code == 200
        assert "tiers" in r.json()

    def test_vendor_pricing(self):
        r = client.get("/api/commercial/pricing/vendor", headers=AUTH)
        assert r.status_code == 200
        assert "manufacturer_portal" in r.json()["tiers"]

    def test_enterprise_pricing(self):
        r = client.get("/api/commercial/pricing/enterprise", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["enterprise_base_annual"] > 0

    def test_estimate_single_facility(self):
        r = client.post("/api/commercial/pricing/estimate",
                        json={"tier": "starter", "num_facilities": 1},
                        headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["total_discount_pct"] == 0.0
        assert body["net_annual_usd"] == body["gross_annual_usd"]

    def test_estimate_multi_facility_discount(self):
        r = client.post("/api/commercial/pricing/estimate",
                        json={"tier": "enterprise", "num_facilities": 6},
                        headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["multi_facility_discount_pct"] == 20.0
        assert body["net_annual_usd"] < body["gross_annual_usd"]

    def test_estimate_multi_year_discount(self):
        r = client.post("/api/commercial/pricing/estimate",
                        json={"tier": "professional", "num_facilities": 2,
                              "term_years": 3}, headers=AUTH)
        body = r.json()
        assert body["multi_year_discount_pct"] == 15.0

    def test_estimate_recommends_tier(self):
        r = client.post("/api/commercial/pricing/estimate",
                        json={"num_facilities": 15}, headers=AUTH)
        body = r.json()
        assert body["recommended_tier"] == "health_system"

    def test_estimate_unknown_tier_404(self):
        r = client.post("/api/commercial/pricing/estimate",
                        json={"tier": "nope", "num_facilities": 1}, headers=AUTH)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Phase 3 — Customer Success
# ---------------------------------------------------------------------------

class TestCustomerSuccess:
    def test_health_score(self):
        r = client.get("/api/commercial/customer-success/health-score", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert 0 <= body["composite_score"] <= 100
        assert body["status"] in {"healthy", "watch", "at_risk"}
        assert body["human_review_required"] is True

    def test_health_score_weights_sum_to_one(self):
        r = client.get("/api/commercial/customer-success/health-score", headers=AUTH)
        weights = r.json()["weights"]
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_health_score_dimensions_present(self):
        r = client.get("/api/commercial/customer-success/health-score"
                       "?onboarding_pct=50&training_pct=70", headers=AUTH)
        dims = r.json()["dimensions"]
        assert dims["onboarding"] == 50.0
        assert dims["training"] == 70.0

    def test_onboarding_status(self):
        r = client.get("/api/commercial/customer-success/onboarding-status", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert "completion_pct" in body
        assert "by_status" in body

    def test_snapshot_persist_and_trend(self):
        tid = f"cs-tenant-{TS}"
        r = client.post("/api/commercial/customer-success/snapshot",
                        json={"tenant_id": tid, "onboarding_pct": 80, "training_pct": 90},
                        headers=AUTH)
        assert r.status_code == 201
        body = r.json()
        assert body["tenant_id"] == tid
        assert 0 <= body["composite_score"] <= 100

        # Trend should now include the snapshot.
        t = client.get(f"/api/commercial/customer-success/trend?tenant_id={tid}", headers=AUTH)
        assert t.status_code == 200
        assert t.json()["count"] >= 1

    def test_health_score_uses_snapshot(self):
        tid = f"cs-snap-{TS}"
        client.post("/api/commercial/customer-success/snapshot",
                    json={"tenant_id": tid, "onboarding_pct": 40, "training_pct": 50},
                    headers=AUTH)
        r = client.get(f"/api/commercial/customer-success/health-score?tenant_id={tid}",
                       headers=AUTH)
        body = r.json()
        assert body["source"] == "snapshot"
        assert body["dimensions"]["onboarding"] == 40.0
        assert body["dimensions"]["training"] == 50.0

    def test_health_score_query_overrides_snapshot(self):
        tid = f"cs-override-{TS}"
        client.post("/api/commercial/customer-success/snapshot",
                    json={"tenant_id": tid, "onboarding_pct": 40, "training_pct": 50},
                    headers=AUTH)
        r = client.get(f"/api/commercial/customer-success/health-score"
                       f"?tenant_id={tid}&onboarding_pct=100", headers=AUTH)
        body = r.json()
        assert body["source"] == "query"
        assert body["dimensions"]["onboarding"] == 100.0

    def test_snapshot_requires_auth(self):
        r = client.post("/api/commercial/customer-success/snapshot",
                        json={"tenant_id": "x"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Phase 5 — Expansion Analytics
# ---------------------------------------------------------------------------

class TestExpansion:
    def test_opportunities(self):
        r = client.get("/api/commercial/expansion/opportunities", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert "opportunities" in body
        assert "renewal_risks" in body
        assert body["human_review_required"] is True


# ---------------------------------------------------------------------------
# Phase 4 & 6 — ROI calculator / business case
# ---------------------------------------------------------------------------

class TestROI:
    def test_roi_calculate_default(self):
        r = client.post("/api/commercial/roi/calculate", json={}, headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["savings"]["gross_benefit_usd"] > 0
        assert body["human_review_required"] is True

    def test_roi_with_explicit_cost(self):
        r = client.post("/api/commercial/roi/calculate",
                        json={"monthly_inspections": 5000,
                              "annual_subscription_usd": 100000},
                        headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["annual_cost_usd"] == 100000
        assert body["roi_pct"] is not None

    def test_roi_payback_months(self):
        r = client.post("/api/commercial/roi/calculate",
                        json={"monthly_inspections": 3000, "num_facilities": 2},
                        headers=AUTH)
        body = r.json()
        assert body["payback_months"] is not None
        assert body["annual_inspections"] == 3000 * 12 * 2

    def test_roi_no_fda_claim(self):
        r = client.post("/api/commercial/roi/calculate", json={}, headers=AUTH)
        text = r.text.lower()
        assert "fda" not in text or "no fda" in text or "not a guarantee" in text

    def test_business_case_summary(self):
        r = client.get("/api/commercial/business-case/executive-summary", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert "modeled_annual_savings_usd" in body
        assert body["quality"]["human_review_required"] is True
        assert "no fda clearance" in body["disclaimer"].lower()


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class TestPermissions:
    def test_pricing_requires_auth(self):
        assert client.get("/api/commercial/pricing/hospital").status_code == 401

    def test_roi_requires_auth(self):
        assert client.post("/api/commercial/roi/calculate", json={}).status_code == 401

    def test_business_case_requires_auth(self):
        assert client.get("/api/commercial/business-case/executive-summary").status_code == 401
