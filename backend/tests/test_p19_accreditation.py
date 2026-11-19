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
        # P472-03: the listing is scoped to the caller's verified tenant. This
        # smoke test selects the tenant it operates in with the verified
        # ``X-Tenant-Id`` header (honoured here for the dev/admin token), rather
        # than passing a tenant selector in the query string (now inert, AW-04).
        scoped = {**AUTH, "X-Tenant-Id": tid}
        r = client.post("/api/accreditation/programs",
                        json={"tenant_id": tid, "facility_id": "F1",
                              "accreditor": "joint_commission"}, headers=scoped)
        assert r.status_code == 201
        pid = r.json()["id"]
        lst = client.get("/api/accreditation/programs", headers=scoped)
        assert any(p["id"] == pid for p in lst.json()["programs"])

    def test_invalid_accreditor_422(self):
        r = client.post("/api/accreditation/programs",
                        json={"tenant_id": "x", "facility_id": "F1", "accreditor": "bogus"},
                        headers=AUTH)
        assert r.status_code == 422

    def test_update_status(self):
        # P472-03: the status update enforces object ownership — the program must
        # belong to the caller's verified tenant (AW-08a). Operate in that tenant
        # via the verified ``X-Tenant-Id`` header.
        tid = f"acc2-{TS}"
        scoped = {**AUTH, "X-Tenant-Id": tid}
        r = client.post("/api/accreditation/programs",
                        json={"tenant_id": tid, "facility_id": "F1",
                              "accreditor": "dnv"}, headers=scoped)
        pid = r.json()["id"]
        u = client.patch(f"/api/accreditation/programs/{pid}?status=accredited", headers=scoped)
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
        # P472-03 AW-04: readiness scopes to the caller's verified tenant; select it.
        r = client.get(f"/api/accreditation/readiness?tenant_id={tid}&facility_id={fid}&accreditor=cms",
                       headers={**AUTH, "X-Tenant-Id": tid})
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
                       headers={**AUTH, "X-Tenant-Id": tid})
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
        lst = client.get(f"/api/accreditation/survey-evidence?tenant_id={tid}", headers={**AUTH, "X-Tenant-Id": tid})
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


class TestEvidenceTemplates:
    def test_templates_listed(self):
        r = client.get("/api/accreditation/evidence-templates?accreditor=joint_commission",
                       headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()["items"]) > 0

    def test_seed_is_idempotent(self):
        tid, fid = f"seed-{TS}", "F1"
        first = client.post("/api/accreditation/evidence-items/seed",
                            json={"tenant_id": tid, "facility_id": fid,
                                  "accreditor": "cms"}, headers=AUTH)
        assert first.status_code == 201
        assert first.json()["created"] > 0
        second = client.post("/api/accreditation/evidence-items/seed",
                             json={"tenant_id": tid, "facility_id": fid,
                                   "accreditor": "cms"}, headers=AUTH)
        assert second.json()["created"] == 0  # already seeded


class TestReadinessCapaLinkage:
    def test_create_capas_from_critical_gaps(self):
        tid, fid = f"capa-{TS}", "F1"
        # Seed CMS template (has a critical missing item by default)
        client.post("/api/accreditation/evidence-items/seed",
                    json={"tenant_id": tid, "facility_id": fid, "accreditor": "cms"},
                    headers=AUTH)
        r = client.post("/api/accreditation/readiness/create-capas",
                        json={"tenant_id": tid, "facility_id": fid, "accreditor": "cms"},
                        headers=AUTH)
        assert r.status_code == 201
        body = r.json()
        assert body["open_critical_gaps"] >= 1
        assert body["capas_created"] >= 1
        # idempotent second call creates none
        again = client.post("/api/accreditation/readiness/create-capas",
                            json={"tenant_id": tid, "facility_id": fid, "accreditor": "cms"},
                            headers=AUTH)
        assert again.json()["capas_created"] == 0


class TestCertificationEligibility:
    def test_eligibility_gated_by_open_critical(self):
        tid, fid = f"elig-{TS}", "F1"
        client.post("/api/accreditation/evidence-items/seed",
                    json={"tenant_id": tid, "facility_id": fid, "accreditor": "hfap"},
                    headers=AUTH)
        c = client.post("/api/accreditation/certifications",
                        json={"tenant_id": tid, "facility_id": fid,
                              "certification_type": "certified_site"}, headers=AUTH)
        cid = c.json()["id"]
        e = client.get(f"/api/accreditation/certifications/{cid}/eligibility", headers=AUTH)
        assert e.status_code == 200
        body = e.json()
        # HFAP template has open critical items → not eligible
        assert body["checks"]["no_open_critical"] is False
        assert body["eligible"] is False


class TestBenchmarkArchiveAndExport:
    def test_publish_below_floor_409(self):
        r = client.post("/api/accreditation/benchmark-publications/publish",
                        json={"edition": f"2026-{TS}"}, headers=AUTH)
        # Small test network → suppressed
        assert r.status_code in (201, 409)

    def test_list_publications(self):
        r = client.get("/api/accreditation/benchmark-publications", headers=AUTH)
        assert r.status_code == 200
        assert "publications" in r.json()

    def test_export_package_html(self):
        tid, fid = f"exp-{TS}", "F1"
        client.post("/api/accreditation/evidence-items",
                    json={"tenant_id": tid, "facility_id": fid, "accreditor": "state",
                          "status": "complete", "title": "policy"}, headers=AUTH)
        g = client.post("/api/accreditation/survey-evidence/generate",
                        json={"tenant_id": tid, "facility_id": fid, "accreditor": "state"},
                        headers=AUTH)
        pid = g.json()["id"]
        x = client.get(f"/api/accreditation/survey-evidence/{pid}/export", headers=AUTH)
        assert x.status_code == 200
        assert "Survey Evidence Binder" in x.text


class TestAdvisoryBoard:
    def test_member_and_proposal_signoff(self):
        m = client.post("/api/accreditation/advisory-board/members",
                        json={"member_name": f"Dr. Q-{TS}", "role": "quality_advisor",
                              "conflict_of_interest_disclosed": True}, headers=AUTH)
        assert m.status_code == 201
        p = client.post("/api/accreditation/advisory-board/proposals",
                        json={"title": "Raise readiness gate", "description": "to 90"},
                        headers=AUTH)
        pid = p.json()["id"]
        assert p.json()["status"] == "proposed"
        s = client.post(f"/api/accreditation/advisory-board/proposals/{pid}/sign-off?decision=approved",
                        headers=AUTH)
        assert s.status_code == 200
        assert s.json()["status"] == "approved"
        assert s.json()["signed_off_at"] is not None

    def test_invalid_decision_422(self):
        p = client.post("/api/accreditation/advisory-board/proposals",
                        json={"title": "x"}, headers=AUTH)
        pid = p.json()["id"]
        s = client.post(f"/api/accreditation/advisory-board/proposals/{pid}/sign-off?decision=maybe",
                        headers=AUTH)
        assert s.status_code == 422
