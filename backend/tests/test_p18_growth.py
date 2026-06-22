"""P18 — National Expansion & Strategic Partnerships tests."""
import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token"}
TS = str(int(time.time()))[-6:]


class TestPartnerships:
    def test_create_and_list(self):
        r = client.post("/api/growth/partnerships",
                        json={"partner_name": f"Acme-{TS}", "partner_type": "manufacturer",
                              "status": "engaged"}, headers=AUTH)
        assert r.status_code == 201
        pid = r.json()["id"]

        lst = client.get("/api/growth/partnerships?partner_type=manufacturer", headers=AUTH)
        assert lst.status_code == 200
        assert any(p["id"] == pid for p in lst.json()["partnerships"])

    def test_invalid_partner_type_422(self):
        r = client.post("/api/growth/partnerships",
                        json={"partner_name": "X", "partner_type": "bogus"}, headers=AUTH)
        assert r.status_code == 422

    def test_update_status(self):
        r = client.post("/api/growth/partnerships",
                        json={"partner_name": f"GPO-{TS}", "partner_type": "gpo"}, headers=AUTH)
        pid = r.json()["id"]
        u = client.patch(f"/api/growth/partnerships/{pid}?status=active", headers=AUTH)
        assert u.status_code == 200
        assert u.json()["status"] == "active"

    def test_update_status_invalid(self):
        r = client.post("/api/growth/partnerships",
                        json={"partner_name": f"V-{TS}", "partner_type": "vendor"}, headers=AUTH)
        pid = r.json()["id"]
        u = client.patch(f"/api/growth/partnerships/{pid}?status=nope", headers=AUTH)
        assert u.status_code == 422

    def test_update_missing_404(self):
        u = client.patch("/api/growth/partnerships/99999999?status=active", headers=AUTH)
        assert u.status_code == 404

    def test_requires_auth(self):
        assert client.get("/api/growth/partnerships").status_code == 401


class TestReferenceCustomers:
    def test_create_redacts_until_consent(self):
        tid = f"ref-{TS}"
        r = client.post("/api/growth/reference-customers",
                        json={"tenant_id": tid, "display_name": "Mercy Hospital",
                              "conversion_stage": "enterprise"}, headers=AUTH)
        assert r.status_code == 201
        rid = r.json()["id"]

        # Internal listing redacts name until consent is granted.
        lst = client.get("/api/growth/reference-customers", headers=AUTH)
        match = next(x for x in lst.json()["reference_customers"] if x["id"] == rid)
        assert match["display_name"] == f"Reference #{rid}"
        assert match["public_reference_consent"] is False
        assert match["tenant_id"] is None  # redacted

    def test_consent_unlocks_name_and_public_listing(self):
        tid = f"ref2-{TS}"
        r = client.post("/api/growth/reference-customers",
                        json={"tenant_id": tid, "display_name": "St. Luke",
                              "conversion_stage": "reference"}, headers=AUTH)
        rid = r.json()["id"]
        c = client.post(f"/api/growth/reference-customers/{rid}/consent?consent=true", headers=AUTH)
        assert c.status_code == 200
        assert c.json()["public_reference_consent"] is True

        pub = client.get("/api/growth/reference-customers?public_only=true", headers=AUTH)
        match = next(x for x in pub.json()["reference_customers"] if x["id"] == rid)
        assert match["display_name"] == "St. Luke"

    def test_consent_missing_404(self):
        assert client.post("/api/growth/reference-customers/99999999/consent?consent=true",
                           headers=AUTH).status_code == 404

    def test_conversion_funnel(self):
        r = client.get("/api/growth/conversion-funnel", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert set(body["stages"].keys()) == {"pilot", "converting", "enterprise", "reference"}
        assert "pilot_to_enterprise_conversion_pct" in body


class TestMarketIntelligence:
    def test_summary_governance_and_kanonymity(self):
        r = client.get("/api/growth/market-intelligence/summary", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["governance"]["human_review_required"] is True
        # With a small/empty network the detail must be suppressed.
        assert "k_anonymity_met" in body["benchmark_network"]
        assert "no fda" in body["disclaimer"].lower()

    def test_kpis(self):
        r = client.get("/api/growth/kpis", headers=AUTH)
        assert r.status_code == 200
        names = {k["name"] for k in r.json()["kpis"]}
        assert "Active strategic partnerships" in names

    def test_summary_requires_auth(self):
        assert client.get("/api/growth/market-intelligence/summary").status_code == 401
