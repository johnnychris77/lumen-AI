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

    def test_notes_lifecycle(self):
        r = client.post("/api/growth/partnerships",
                        json={"partner_name": f"Note-{TS}", "partner_type": "vendor"}, headers=AUTH)
        pid = r.json()["id"]
        n = client.post(f"/api/growth/partnerships/{pid}/notes",
                        json={"note": "Intro call held"}, headers=AUTH)
        assert n.status_code == 201
        lst = client.get(f"/api/growth/partnerships/{pid}/notes", headers=AUTH)
        assert lst.status_code == 200
        assert lst.json()["count"] >= 1

    def test_notes_missing_partnership_404(self):
        assert client.post("/api/growth/partnerships/99999999/notes",
                           json={"note": "x"}, headers=AUTH).status_code == 404

    def test_overdue_review_filter(self):
        # A past next_review_date should be flagged overdue and surface in filter.
        r = client.post("/api/growth/partnerships",
                        json={"partner_name": f"Due-{TS}", "partner_type": "gpo",
                              "next_review_date": "2020-01-01T00:00:00Z"}, headers=AUTH)
        pid = r.json()["id"]
        assert r.json()["review_overdue"] is True
        lst = client.get("/api/growth/partnerships?overdue_review=true", headers=AUTH)
        assert any(p["id"] == pid for p in lst.json()["partnerships"])


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

    def test_roi_linkage_and_checklist(self):
        tid = f"roi-{TS}"
        r = client.post("/api/growth/reference-customers",
                        json={"tenant_id": tid, "display_name": "ROI Health",
                              "conversion_stage": "enterprise"}, headers=AUTH)
        rid = r.json()["id"]
        roi = client.post(f"/api/growth/reference-customers/{rid}/roi",
                          json={"modeled_annual_savings_usd": 250000, "roi_payback_months": 8},
                          headers=AUTH)
        assert roi.status_code == 200
        assert roi.json()["roi_captured_at"] is not None

        chk = client.get(f"/api/growth/reference-customers/{rid}/case-study-checklist", headers=AUTH)
        assert chk.status_code == 200
        body = chk.json()
        assert body["checklist"]["roi_captured"] is True
        assert body["checklist"]["public_consent"] is False
        assert body["externally_citable"] is False

    def test_ready_to_convert_filter(self):
        r = client.get("/api/growth/reference-customers?ready_to_convert=true", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["ready_to_convert"] is True
        assert body["human_review_required"] is True


class TestBenchmarkTrends:
    def test_snapshot_and_trend_kanonymity(self):
        # Below-floor snapshot is suppressed; above-floor appears.
        client.post("/api/growth/benchmark-snapshots",
                    json={"metric_name": f"contam-{TS}", "n_participants": 3, "p50": 1.0},
                    headers=AUTH)
        client.post("/api/growth/benchmark-snapshots",
                    json={"metric_name": f"contam-{TS}", "n_participants": 8, "p50": 0.9},
                    headers=AUTH)
        t = client.get(f"/api/growth/benchmark-trends?metric=contam-{TS}", headers=AUTH)
        assert t.status_code == 200
        body = t.json()
        assert len(body["points"]) == 1
        assert body["suppressed_below_k"] == 1

    def test_by_region_suppresses_small_regions(self):
        r = client.get("/api/growth/market-intelligence/by-region", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["k_anonymity_floor"] == 5
        assert "regions" in body and "suppressed_regions" in body


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
