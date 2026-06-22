"""P19 — Industry Standardization, Accreditation Integration & Ecosystem Leadership."""
import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer dev-token"}
TS = str(int(time.time()))[-6:]


class TestAccreditationPrograms:
    def test_create_and_list(self):
        tid = f"acc-{TS}"
        r = client.post("/api/accreditation/programs",
                        json={"tenant_id": tid, "facility_id": "F1",
                              "accreditor": "joint_commission"}, headers=AUTH)
        assert r.status_code == 201
        pid = r.json()["id"]
        lst = client.get(f"/api/accreditation/programs?tenant_id={tid}", headers=AUTH)
        assert any(p["id"] == pid for p in lst.json()["programs"])

    def test_invalid_accreditor_422(self):
        r = client.post("/api/accreditation/programs",
                        json={"tenant_id": "x", "facility_id": "F1", "accreditor": "bogus"},
                        headers=AUTH)
        assert r.status_code == 422

    def test_update_status(self):
        r = client.post("/api/accreditation/programs",
                        json={"tenant_id": f"acc2-{TS}", "facility_id": "F1",
                              "accreditor": "dnv"}, headers=AUTH)
        pid = r.json()["id"]
        u = client.patch(f"/api/accreditation/programs/{pid}?status=accredited", headers=AUTH)
        assert u.status_code == 200
        assert u.json()["status"] == "accredited"

    def test_requires_auth(self):
        assert client.get("/api/accreditation/programs").status_code == 401


class TestReadinessEngine:
    def _seed(self, tid, fid, accreditor="cms"):
        # 4 items: 2 complete, 1 in_progress, 1 missing critical
        specs = [
            ("complete", False), ("complete", False),
            ("in_progress", False), ("missing", True),
        ]
        for status, crit in specs:
            client.post("/api/accreditation/evidence-items",
                        json={"tenant_id": tid, "facility_id": fid, "accreditor": accreditor,
                              "status": status, "is_critical": crit,
                              "title": "item"}, headers=AUTH)

    def test_readiness_scoring(self):
        tid, fid = f"rd-{TS}", "F1"
        self._seed(tid, fid)
        r = client.get(f"/api/accreditation/readiness?tenant_id={tid}&facility_id={fid}&accreditor=cms",
                       headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["total_items"] == 4
        assert body["breakdown"]["complete"] == 2
        assert body["open_critical_items"] == 1
        # open critical caps status below ready
        assert body["readiness_status"] in {"approaching", "not_ready"}
        assert body["human_review_required"] is True
        assert "does not guarantee accreditation" in body["disclaimer"].lower()

    def test_empty_facility_is_not_ready(self):
        r = client.get(f"/api/accreditation/readiness?tenant_id=empty-{TS}&facility_id=F9",
                       headers=AUTH)
        assert r.json()["readiness_status"] == "not_ready"
        assert r.json()["risk_score"] == 100.0

    def test_snapshot_and_trend(self):
        tid, fid = f"snap-{TS}", "F1"
        self._seed(tid, fid, "hfap")
        s = client.post("/api/accreditation/readiness/snapshot",
                        json={"tenant_id": tid, "facility_id": fid, "accreditor": "hfap"},
                        headers=AUTH)
        assert s.status_code == 201
        assert "assessment_id" in s.json()
        t = client.get(f"/api/accreditation/readiness/trend?tenant_id={tid}&facility_id={fid}",
                       headers=AUTH)
        assert t.status_code == 200
        assert len(t.json()["points"]) >= 1


class TestSurveyEvidence:
    def test_generate_package(self):
        tid, fid = f"pkg-{TS}", "F1"
        client.post("/api/accreditation/evidence-items",
                    json={"tenant_id": tid, "facility_id": fid, "accreditor": "state",
                          "status": "complete", "title": "policy"}, headers=AUTH)
        g = client.post("/api/accreditation/survey-evidence/generate",
                        json={"tenant_id": tid, "facility_id": fid, "accreditor": "state",
                              "package_type": "binder"}, headers=AUTH)
        assert g.status_code == 201
        body = g.json()
        assert body["item_count"] == 1
        assert body["complete_count"] == 1
        assert "readiness" in body
        lst = client.get(f"/api/accreditation/survey-evidence?tenant_id={tid}", headers=AUTH)
        assert lst.json()["count"] >= 1

    def test_invalid_package_type_422(self):
        g = client.post("/api/accreditation/survey-evidence/generate",
                        json={"tenant_id": "x", "facility_id": "F1", "accreditor": "cms",
                              "package_type": "bogus"}, headers=AUTH)
        assert g.status_code == 422


class TestCertification:
    def test_create_and_award(self):
        tid = f"cert-{TS}"
        c = client.post("/api/accreditation/certifications",
                        json={"tenant_id": tid, "facility_id": "F1",
                              "certification_type": "certified_site"}, headers=AUTH)
        assert c.status_code == 201
        cid = c.json()["id"]
        assert c.json()["status"] == "applicant"
        a = client.post(f"/api/accreditation/certifications/{cid}/award?valid_days=365", headers=AUTH)
        assert a.status_code == 200
        assert a.json()["status"] == "certified"
        assert a.json()["expires_at"] is not None

    def test_invalid_cert_type_422(self):
        c = client.post("/api/accreditation/certifications",
                        json={"tenant_id": "x", "facility_id": "F1",
                              "certification_type": "bogus"}, headers=AUTH)
        assert c.status_code == 422


class TestBenchmarkPublicationAndKpis:
    def test_annual_report_kanonymity(self):
        r = client.get("/api/accreditation/benchmark-publications/annual-report", headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        # Either suppressed (small network) or published with methodology.
        assert "published" in body
        if not body["published"]:
            assert "k-anonymity" in body["message"].lower()
        else:
            assert body["methodology"]["k_anonymity_floor"] == 5

    def test_kpis(self):
        r = client.get("/api/accreditation/kpis", headers=AUTH)
        assert r.status_code == 200
        names = {k["name"] for k in r.json()["kpis"]}
        assert "Accredited facilities" in names

    def test_report_requires_auth(self):
        assert client.get(
            "/api/accreditation/benchmark-publications/annual-report").status_code == 401
