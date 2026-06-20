"""P14 Commercial Launch — tests for all 12 recommendations."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}


# ---------------------------------------------------------------------------
# 1. Pilot conversion gate
# ---------------------------------------------------------------------------
class TestPilotConversionGate:
    def test_start_pilot(self) -> None:
        resp = client.post(
            "/api/pilot/start",
            json={"facility_id": "fac-1", "agreed_kpis": {"inspection_rate": 95, "contamination_flag": 5}},
            headers=HEADERS,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "pilot_id" in data
        assert data["status"] == "started"

    def test_get_pilot_status(self) -> None:
        # Start a pilot first
        client.post(
            "/api/pilot/start",
            json={"facility_id": "fac-status", "agreed_kpis": {"kpi_a": 10}},
            headers=HEADERS,
        )
        resp = client.get("/api/pilot/status?facility_id=fac-status", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "days_remaining" in data
        assert "kpi_progress" in data
        assert "conversion_ready" in data

    def test_pilot_status_404_when_none(self) -> None:
        resp = client.get("/api/pilot/status?facility_id=nonexistent-999", headers=HEADERS)
        assert resp.status_code == 404

    def test_convert_pilot(self) -> None:
        client.post(
            "/api/pilot/start",
            json={"facility_id": "fac-convert", "agreed_kpis": {}},
            headers=HEADERS,
        )
        resp = client.post("/api/pilot/convert?facility_id=fac-convert", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["conversion_ready"] is True
        assert data["status"] == "converted"

    def test_pilot_requires_auth(self) -> None:
        resp = client.get("/api/pilot/status")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. CFO dashboard live data
# ---------------------------------------------------------------------------
class TestCFODashboard:
    def test_cfo_dashboard_returns_data_source(self) -> None:
        resp = client.get("/api/executive/dashboard/cfo", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "data_source" in data
        assert data["data_source"] in ("real", "mock")

    def test_cfo_has_financial_kpis(self) -> None:
        resp = client.get("/api/executive/dashboard/cfo", headers=HEADERS)
        data = resp.json()
        assert "labor_savings_usd" in data
        assert "roi_multiple" in data


# ---------------------------------------------------------------------------
# 3. Customer health score
# ---------------------------------------------------------------------------
class TestCustomerHealthScore:
    def test_health_score_200(self) -> None:
        resp = client.get("/api/tenant/health-score", headers=HEADERS)
        assert resp.status_code == 200, resp.text

    def test_health_score_has_required_fields(self) -> None:
        resp = client.get("/api/tenant/health-score", headers=HEADERS)
        data = resp.json()
        assert "score" in data
        assert "tier" in data
        assert "components" in data
        assert data["tier"] in ("green", "yellow", "red")
        assert 0 <= data["score"] <= 100

    def test_health_score_requires_auth(self) -> None:
        resp = client.get("/api/tenant/health-score")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Billing webhook handler
# ---------------------------------------------------------------------------
class TestBillingWebhooks:
    def test_webhook_no_auth_works(self) -> None:
        """Webhook endpoint must NOT require auth (Stripe calls it)."""
        event = {
            "type": "invoice.payment_failed",
            "data": {"object": {"metadata": {"tenant_id": "test-webhook-tenant"}}},
        }
        resp = client.post(
            "/api/billing/webhook",
            json=event,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["received"] is True

    def test_webhook_payment_failed(self) -> None:
        event = {
            "type": "invoice.payment_failed",
            "data": {"object": {"metadata": {"tenant_id": "wh-tenant-1"}}},
        }
        resp = client.post("/api/billing/webhook", json=event)
        assert resp.status_code == 200

    def test_webhook_subscription_deleted(self) -> None:
        event = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"metadata": {"tenant_id": "wh-tenant-2"}}},
        }
        resp = client.post("/api/billing/webhook", json=event)
        assert resp.status_code == 200
        assert resp.json()["received"] is True

    def test_webhook_subscription_updated(self) -> None:
        event = {
            "type": "customer.subscription.updated",
            "data": {"object": {"plan": {"nickname": "enterprise"}, "metadata": {"tenant_id": "wh-tenant-3"}}},
        }
        resp = client.post("/api/billing/webhook", json=event)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. Demo tenant mode
# ---------------------------------------------------------------------------
class TestDemoMode:
    def test_demo_reset_403_when_demo_mode_not_set(self) -> None:
        """Without DEMO_MODE=1, /api/demo/reset must return 403."""
        import os
        os.environ.pop("DEMO_MODE", None)
        resp = client.get("/api/demo/reset", headers=HEADERS)
        assert resp.status_code == 403, resp.text

    def test_demo_reset_works_with_demo_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEMO_MODE", "1")
        resp = client.get("/api/demo/reset", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "reset"


# ---------------------------------------------------------------------------
# 6. ROI report PDF export
# ---------------------------------------------------------------------------
class TestROIPDFExport:
    def test_pdf_export_200(self) -> None:
        resp = client.get("/api/executive/dashboard/cfo/pdf", headers=HEADERS)
        assert resp.status_code == 200, resp.text

    def test_pdf_has_content_disposition(self) -> None:
        resp = client.get("/api/executive/dashboard/cfo/pdf", headers=HEADERS)
        assert "content-disposition" in resp.headers
        assert "roi-report.pdf" in resp.headers["content-disposition"]

    def test_pdf_requires_auth(self) -> None:
        resp = client.get("/api/executive/dashboard/cfo/pdf")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 7. Manufacturer portal onboarding
# ---------------------------------------------------------------------------
class TestManufacturerPortal:
    def test_register_no_auth(self) -> None:
        resp = client.post(
            "/api/manufacturers/register",
            json={
                "manufacturer_name": "Acme Medical",
                "contact_email": "contact@acme.com",
                "instruments_manufactured": ["scalpel", "forceps"],
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "registration_id" in data
        assert data["registration_status"] == "pending"

    def test_check_status_no_auth(self) -> None:
        reg_resp = client.post(
            "/api/manufacturers/register",
            json={"manufacturer_name": "Beta Med", "contact_email": "b@beta.com"},
        )
        reg_id = reg_resp.json()["registration_id"]
        resp = client.get(f"/api/manufacturers/register/{reg_id}")
        assert resp.status_code == 200
        assert resp.json()["registration_id"] == reg_id

    def test_list_registrations_requires_auth(self) -> None:
        resp = client.get("/api/manufacturers/registrations")
        assert resp.status_code == 401

    def test_list_registrations_with_auth(self) -> None:
        resp = client.get("/api/manufacturers/registrations", headers=HEADERS)
        assert resp.status_code == 200
        assert "registrations" in resp.json()

    def test_approve_registration(self) -> None:
        reg_resp = client.post(
            "/api/manufacturers/register",
            json={"manufacturer_name": "Gamma Instruments", "contact_email": "g@gamma.com"},
        )
        reg_id = reg_resp.json()["registration_id"]
        resp = client.post(
            f"/api/manufacturers/registrations/{reg_id}/approve",
            json={"notes": "Looks good"},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["registration_status"] == "approved"


# ---------------------------------------------------------------------------
# 8. GPO contract pricing
# ---------------------------------------------------------------------------
class TestGPOContract:
    def test_set_gpo_contract(self) -> None:
        resp = client.post(
            "/api/billing/gpo-contract",
            json={"gpo_contract_id": "GPO-2024-001", "gpo_discount_pct": 12.5},
            headers=HEADERS,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["gpo_contract_id"] == "GPO-2024-001"
        assert data["gpo_discount_pct"] == 12.5

    def test_get_gpo_contract(self) -> None:
        client.post(
            "/api/billing/gpo-contract",
            json={"gpo_contract_id": "GPO-GET-TEST", "gpo_discount_pct": 5.0},
            headers=HEADERS,
        )
        resp = client.get("/api/billing/gpo-contract", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "gpo_contract_id" in data
        assert "gpo_discount_pct" in data


# ---------------------------------------------------------------------------
# 9. Usage metering
# ---------------------------------------------------------------------------
class TestUsageMetering:
    def test_current_month_returns_required_fields(self) -> None:
        resp = client.get("/api/usage/current-month", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "inspection_count" in data
        assert "cap" in data
        assert "remaining" in data
        assert "pct_used" in data

    def test_increment_usage(self) -> None:
        resp = client.post("/api/usage/increment?amount=5", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "inspection_count" in data

    def test_usage_requires_auth(self) -> None:
        resp = client.get("/api/usage/current-month")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 10. HIPAA BAA tracker
# ---------------------------------------------------------------------------
class TestHIPAABAA:
    def test_post_hipaa_baa(self) -> None:
        resp = client.post(
            "/api/tenant/hipaa-baa",
            json={"hipaa_baa_reference": "BAA-2024-XYZ"},
            headers=HEADERS,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "signed"
        assert data["hipaa_baa_signed_at"] is not None

    def test_get_hipaa_baa(self) -> None:
        client.post(
            "/api/tenant/hipaa-baa",
            json={"hipaa_baa_reference": "BAA-GET-TEST"},
            headers=HEADERS,
        )
        resp = client.get("/api/tenant/hipaa-baa", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "hipaa_baa_signed" in data

    def test_hipaa_baa_requires_auth(self) -> None:
        resp = client.get("/api/tenant/hipaa-baa")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 11. SSO configuration
# ---------------------------------------------------------------------------
class TestSSOConfig:
    def test_post_sso_config(self) -> None:
        resp = client.post(
            "/api/tenant/sso-config",
            json={
                "provider": "okta",
                "oidc_issuer_url": "https://example.okta.com",
                "client_id": "client-abc-123",
                "audience": "api://default",
            },
            headers=HEADERS,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["provider"] == "okta"

    def test_get_sso_config(self) -> None:
        client.post(
            "/api/tenant/sso-config",
            json={"provider": "azure_ad", "client_id": "az-client-456"},
            headers=HEADERS,
        )
        resp = client.get("/api/tenant/sso-config", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "provider" in data
        assert "configured" in data

    def test_delete_sso_config(self) -> None:
        client.post(
            "/api/tenant/sso-config",
            json={"provider": "epic"},
            headers=HEADERS,
        )
        resp = client.delete("/api/tenant/sso-config", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        assert resp.json()["provider"] == "none"

    def test_sso_config_requires_auth(self) -> None:
        resp = client.get("/api/tenant/sso-config")
        assert resp.status_code == 401

    def test_invalid_provider_rejected(self) -> None:
        resp = client.post(
            "/api/tenant/sso-config",
            json={"provider": "invalid_provider"},
            headers=HEADERS,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 12. Status page
# ---------------------------------------------------------------------------
class TestStatusPage:
    def test_status_200(self) -> None:
        resp = client.get("/status")
        assert resp.status_code == 200, resp.text

    def test_status_has_required_fields(self) -> None:
        resp = client.get("/status")
        data = resp.json()
        assert "status" in data
        assert "components" in data
        assert "uptime_30d_pct" in data
        assert "last_checked" in data
        assert data["status"] in ("operational", "degraded", "outage")

    def test_status_no_auth_required(self) -> None:
        """Status endpoint must be public."""
        resp = client.get("/status")
        assert resp.status_code == 200

    def test_status_components_structure(self) -> None:
        resp = client.get("/status")
        data = resp.json()
        assert isinstance(data["components"], list)
        for comp in data["components"]:
            assert "name" in comp
            assert "status" in comp
