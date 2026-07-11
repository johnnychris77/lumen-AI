"""P8: Regulatory & Accreditation Automation tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH = {"Authorization": "Bearer dev-token", "X-LumenAI-Role": "operator"}
TENANT = "test-tenant-p8"
TENANT_B = "another-tenant-p8"

VALID_TIERS = ("survey_ready", "conditional", "needs_improvement", "at_risk")
VALID_SEVERITIES = ("low", "medium", "high", "critical")


# ── TestAccreditationReadinessAPI ────────────────────────────────────────────

class TestAccreditationReadinessAPI:
    def test_readiness_status_ok(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_readiness_returns_success(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_readiness_has_readiness_key(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert "readiness" in r.json()

    def test_readiness_overall_score_range(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        score = r.json()["readiness"]["overall_score"]
        assert 0 <= score <= 100

    def test_readiness_tier_valid(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["readiness"]["readiness_tier"] in VALID_TIERS

    def test_readiness_jc_score_range(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        score = r.json()["readiness"]["joint_commission_score"]
        assert 0 <= score <= 100

    def test_readiness_aami_score_range(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert 0 <= r.json()["readiness"]["aami_score"] <= 100

    def test_readiness_fda_score_range(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert 0 <= r.json()["readiness"]["fda_score"] <= 100

    def test_readiness_cms_score_range(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert 0 <= r.json()["readiness"]["cms_score"] <= 100

    def test_readiness_has_findings_list(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert isinstance(r.json()["readiness"]["findings"], list)

    def test_readiness_has_recommended_actions(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        actions = r.json()["readiness"]["recommended_actions"]
        assert isinstance(actions, list)

    def test_readiness_deficiency_count_non_negative(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["readiness"]["deficiency_count"] >= 0

    def test_readiness_critical_deficiency_non_negative(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["readiness"]["critical_deficiency_count"] >= 0

    def test_readiness_requires_auth(self):
        r = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)

    def test_readiness_tenant_isolation(self):
        r1 = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT}, headers=AUTH)
        r2 = client.get("/api/regulatory/readiness", params={"tenant_id": TENANT_B}, headers=AUTH)
        assert r1.status_code == 200
        assert r2.status_code == 200


# ── TestDeficiencyFindingsAPI ─────────────────────────────────────────────────

class TestDeficiencyFindingsAPI:
    def test_findings_status_ok(self):
        r = client.get("/api/regulatory/readiness/findings", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_findings_returns_success(self):
        r = client.get("/api/regulatory/readiness/findings", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_findings_has_list(self):
        r = client.get("/api/regulatory/readiness/findings", params={"tenant_id": TENANT}, headers=AUTH)
        assert isinstance(r.json()["findings"], list)

    def test_findings_has_total(self):
        r = client.get("/api/regulatory/readiness/findings", params={"tenant_id": TENANT}, headers=AUTH)
        assert "total" in r.json()

    def test_findings_severity_filter(self):
        r = client.get("/api/regulatory/readiness/findings", params={"tenant_id": TENANT, "severity": "high"}, headers=AUTH)
        findings = r.json()["findings"]
        for f in findings:
            assert f["severity"] == "high"

    def test_findings_each_has_standard_code(self):
        r = client.get("/api/regulatory/readiness/findings", params={"tenant_id": TENANT}, headers=AUTH)
        for f in r.json()["findings"]:
            assert "standard_code" in f
            assert f["standard_code"]

    def test_findings_each_has_citation_text(self):
        r = client.get("/api/regulatory/readiness/findings", params={"tenant_id": TENANT}, headers=AUTH)
        for f in r.json()["findings"]:
            assert "citation_text" in f

    def test_findings_requires_auth(self):
        r = client.get("/api/regulatory/readiness/findings", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)


# ── TestStandardsCatalogueAPI ─────────────────────────────────────────────────

class TestStandardsCatalogueAPI:
    def test_standards_status_ok(self):
        r = client.get("/api/regulatory/standards", headers=AUTH)
        assert r.status_code == 200

    def test_standards_returns_success(self):
        r = client.get("/api/regulatory/standards", headers=AUTH)
        assert r.json()["status"] == "success"

    def test_standards_has_list(self):
        r = client.get("/api/regulatory/standards", headers=AUTH)
        assert isinstance(r.json()["standards"], list)
        assert len(r.json()["standards"]) > 0

    def test_standards_each_has_code(self):
        r = client.get("/api/regulatory/standards", headers=AUTH)
        for s in r.json()["standards"]:
            assert "code" in s and s["code"]

    def test_standards_body_filter(self):
        r = client.get("/api/regulatory/standards", params={"body": "aami"}, headers=AUTH)
        for s in r.json()["standards"]:
            assert s["body"] == "aami"

    def test_standards_category_filter(self):
        r = client.get("/api/regulatory/standards", params={"category": "infection_control"}, headers=AUTH)
        for s in r.json()["standards"]:
            assert s["category"] == "infection_control"

    def test_standards_requires_auth(self):
        r = client.get("/api/regulatory/standards")
        assert r.status_code in (401, 403)

    def test_standards_covers_multiple_bodies(self):
        r = client.get("/api/regulatory/standards", headers=AUTH)
        bodies = {s["body"] for s in r.json()["standards"]}
        assert len(bodies) >= 3


# ── TestFindingClauseMappingAPI ───────────────────────────────────────────────

class TestFindingClauseMappingAPI:
    def test_mapping_status_ok(self):
        r = client.get("/api/regulatory/standards/mapping", params={"finding_category": "blood"}, headers=AUTH)
        assert r.status_code == 200

    def test_mapping_returns_success(self):
        r = client.get("/api/regulatory/standards/mapping", params={"finding_category": "blood"}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_mapping_has_clauses(self):
        r = client.get("/api/regulatory/standards/mapping", params={"finding_category": "blood"}, headers=AUTH)
        assert isinstance(r.json()["clauses"], list)
        assert len(r.json()["clauses"]) > 0

    def test_mapping_each_has_standard_code(self):
        r = client.get("/api/regulatory/standards/mapping", params={"finding_category": "blood"}, headers=AUTH)
        for c in r.json()["clauses"]:
            assert "standard_code" in c and c["standard_code"]

    def test_mapping_each_has_body(self):
        r = client.get("/api/regulatory/standards/mapping", params={"finding_category": "blood"}, headers=AUTH)
        for c in r.json()["clauses"]:
            assert "body" in c and c["body"]

    def test_mapping_crack_finding(self):
        r = client.get("/api/regulatory/standards/mapping", params={"finding_category": "crack"}, headers=AUTH)
        assert r.status_code == 200
        assert len(r.json()["clauses"]) > 0

    def test_mapping_unknown_category_empty(self):
        r = client.get("/api/regulatory/standards/mapping", params={"finding_category": "xyzunknown"}, headers=AUTH)
        assert r.status_code == 200
        assert r.json()["clauses"] == []

    def test_mapping_requires_auth(self):
        r = client.get("/api/regulatory/standards/mapping", params={"finding_category": "blood"})
        assert r.status_code in (401, 403)


# ── TestAuditPackageAPI ───────────────────────────────────────────────────────

class TestAuditPackageAPI:
    def _post(self, package_type="joint_commission", tenant_id=TENANT):
        return client.post("/api/regulatory/audit-package", json={
            "tenant_id": tenant_id,
            "package_type": package_type,
            "period_label": "2026-06",
            "generated_by": "test-suite",
        }, headers=AUTH)

    def test_create_package_status_ok(self):
        r = self._post()
        assert r.status_code == 200

    def test_create_package_returns_success(self):
        r = self._post()
        assert r.json()["status"] == "success"

    def test_create_package_has_package(self):
        r = self._post()
        assert "package" in r.json()

    def test_create_package_has_standards_covered(self):
        r = self._post()
        assert isinstance(r.json()["package"]["standards_covered"], list)

    def test_create_package_score_range(self):
        r = self._post()
        score = r.json()["package"]["accreditation_score"]
        assert 0 <= score <= 100

    def test_create_package_tier_valid(self):
        r = self._post()
        assert r.json()["package"]["readiness_tier"] in VALID_TIERS

    def test_create_package_findings_count(self):
        r = self._post()
        pkg = r.json()["package"]
        assert pkg["findings_count"] == len(pkg["findings"])

    def test_create_package_aami_type(self):
        r = self._post(package_type="aami")
        assert r.status_code == 200

    def test_create_package_full_type(self):
        r = self._post(package_type="full")
        assert r.status_code == 200

    def test_list_packages_status_ok(self):
        r = client.get("/api/regulatory/audit-packages", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_list_packages_has_packages(self):
        r = client.get("/api/regulatory/audit-packages", params={"tenant_id": TENANT}, headers=AUTH)
        assert "packages" in r.json()

    def test_create_package_requires_auth(self):
        r = client.post("/api/regulatory/audit-package", json={
            "tenant_id": TENANT, "package_type": "joint_commission"
        })
        assert r.status_code in (401, 403)


# ── TestFDASubmissionsAPI ─────────────────────────────────────────────────────

class TestFDASubmissionsAPI:
    def test_list_submissions_status_ok(self):
        r = client.get("/api/regulatory/fda-submissions", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_list_submissions_returns_success(self):
        r = client.get("/api/regulatory/fda-submissions", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_list_submissions_has_list(self):
        r = client.get("/api/regulatory/fda-submissions", params={"tenant_id": TENANT}, headers=AUTH)
        assert isinstance(r.json()["submissions"], list)

    def test_list_submissions_empty_when_no_real_data(self):
        """No fabricated FDA record should ever be returned for a tenant with no real submissions."""
        r = client.get("/api/regulatory/fda-submissions", params={"tenant_id": "no-submissions-tenant-p8"}, headers=AUTH)
        body = r.json()
        assert body["submissions"] == []
        assert body["is_synthetic"] is False
        assert body["data_available"] is False

    def test_list_submissions_has_status_field(self):
        r = client.get("/api/regulatory/fda-submissions", params={"tenant_id": TENANT}, headers=AUTH)
        for s in r.json()["submissions"]:
            assert "status" in s

    def test_create_submission_status_ok(self):
        r = client.post("/api/regulatory/fda-submissions", json={
            "tenant_id": TENANT,
            "submission_type": "510k",
            "device_name": "Test Device",
            "manufacturer": "Test Mfr",
            "status": "pending",
        }, headers=AUTH)
        assert r.status_code == 200

    def test_create_submission_has_id(self):
        r = client.post("/api/regulatory/fda-submissions", json={
            "tenant_id": TENANT,
            "submission_type": "mdr",
            "device_name": "MDR Device",
            "manufacturer": "Test Corp",
            "status": "pending",
        }, headers=AUTH)
        assert "id" in r.json()

    def test_list_submissions_reflects_real_data_only(self):
        """Once a real submission exists, it's returned honestly -- never a fabricated record."""
        r = client.get("/api/regulatory/fda-submissions", params={"tenant_id": TENANT}, headers=AUTH)
        body = r.json()
        assert body["data_available"] is True
        assert body["is_synthetic"] is False
        assert len(body["submissions"]) > 0
        assert all(s["submission_number"] != "K253421" for s in body["submissions"])

    def test_list_submissions_requires_auth(self):
        r = client.get("/api/regulatory/fda-submissions", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)


# ── TestRegulatoryDashboardAPI ────────────────────────────────────────────────

class TestRegulatoryDashboardAPI:
    def test_dashboard_status_ok(self):
        r = client.get("/api/regulatory/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.status_code == 200

    def test_dashboard_returns_success(self):
        r = client.get("/api/regulatory/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert r.json()["status"] == "success"

    def test_dashboard_has_dashboard_key(self):
        r = client.get("/api/regulatory/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert "dashboard" in r.json()

    def test_dashboard_overall_score_range(self):
        r = client.get("/api/regulatory/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        score = r.json()["dashboard"]["overall_readiness_score"]
        assert 0 <= score <= 100

    def test_dashboard_has_fda_submissions(self):
        r = client.get("/api/regulatory/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert isinstance(r.json()["dashboard"]["fda_submissions"], list)

    def test_dashboard_has_standards_summary(self):
        r = client.get("/api/regulatory/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert isinstance(r.json()["dashboard"]["standards_summary"], list)

    def test_dashboard_has_top_findings(self):
        r = client.get("/api/regulatory/dashboard", params={"tenant_id": TENANT}, headers=AUTH)
        assert isinstance(r.json()["dashboard"]["top_findings"], list)

    def test_dashboard_requires_auth(self):
        r = client.get("/api/regulatory/dashboard", params={"tenant_id": TENANT})
        assert r.status_code in (401, 403)


# ── TestAccreditationEngine ───────────────────────────────────────────────────

class TestAccreditationEngine:
    def test_compute_readiness_returns_object(self):
        from app.services.accreditation_engine import compute_accreditation_readiness
        result = compute_accreditation_readiness(TENANT)
        assert result is not None

    def test_compute_readiness_score_range(self):
        from app.services.accreditation_engine import compute_accreditation_readiness
        result = compute_accreditation_readiness(TENANT)
        assert 0 <= result.overall_score <= 100

    def test_compute_readiness_tier_valid(self):
        from app.services.accreditation_engine import compute_accreditation_readiness
        result = compute_accreditation_readiness(TENANT)
        assert result.readiness_tier in VALID_TIERS

    def test_findings_have_required_fields(self):
        from app.services.accreditation_engine import compute_accreditation_readiness
        result = compute_accreditation_readiness(TENANT)
        for f in result.findings:
            assert f.standard_code
            assert f.citation_text
            assert f.remediation_guidance
            assert isinstance(f.auto_capa_required, bool)

    def test_map_finding_to_clauses_blood(self):
        from app.services.accreditation_engine import map_finding_to_clauses
        clauses = map_finding_to_clauses("blood")
        assert len(clauses) > 0
        for c in clauses:
            assert "standard_code" in c
            assert "body" in c

    def test_map_finding_to_clauses_crack(self):
        from app.services.accreditation_engine import map_finding_to_clauses
        clauses = map_finding_to_clauses("crack")
        assert len(clauses) > 0

    def test_generate_audit_package_returns_result(self):
        from app.services.accreditation_engine import generate_audit_package
        result = generate_audit_package(TENANT, package_type="joint_commission")
        assert result is not None
        assert result.tenant_id == TENANT

    def test_generate_audit_package_full(self):
        from app.services.accreditation_engine import generate_audit_package
        result = generate_audit_package(TENANT, package_type="full")
        assert result.standards_covered is not None

    def test_readiness_tier_logic(self):
        from app.services.accreditation_engine import _readiness_tier
        assert _readiness_tier(95) == "survey_ready"
        assert _readiness_tier(80) == "conditional"
        assert _readiness_tier(65) == "needs_improvement"
        assert _readiness_tier(50) == "at_risk"

    def test_fda_submissions_no_real_data_returns_empty(self):
        """With db=None (no real records reachable), the honest answer is an empty list -- not a fabricated one."""
        from app.services.accreditation_engine import list_fda_submissions
        subs = list_fda_submissions(TENANT)
        assert subs == []


# ── TestTierGating ────────────────────────────────────────────────────────────

class TestTierGating:
    def test_regulatory_readiness_in_standard_tier(self):
        from app.tier_guard import TIER_FEATURES
        assert "regulatory_readiness" in TIER_FEATURES["standard"]

    def test_regulatory_findings_in_professional_tier(self):
        from app.tier_guard import TIER_FEATURES
        assert "regulatory_findings" in TIER_FEATURES["professional"]

    def test_audit_package_in_enterprise_only(self):
        from app.tier_guard import TIER_FEATURES
        assert "audit_package" in TIER_FEATURES["enterprise"]
        assert "audit_package" not in TIER_FEATURES["standard"]
        assert "audit_package" not in TIER_FEATURES["professional"]

    def test_fda_tracking_in_enterprise_tier(self):
        from app.tier_guard import TIER_FEATURES
        assert "fda_tracking" in TIER_FEATURES["enterprise"]

    def test_regulatory_dashboard_in_enterprise_tier(self):
        from app.tier_guard import TIER_FEATURES
        assert "regulatory_dashboard" in TIER_FEATURES["enterprise"]


# ── TestPDFGeneration ─────────────────────────────────────────────────────────

class TestPDFGeneration:
    def test_pdf_endpoint_status_ok(self):
        r = client.post("/api/regulatory/audit-package/pdf", json={
            "tenant_id": TENANT,
            "package_type": "joint_commission",
            "period_label": "2026-06",
        }, headers=AUTH)
        assert r.status_code == 200

    def test_pdf_endpoint_content_type(self):
        r = client.post("/api/regulatory/audit-package/pdf", json={
            "tenant_id": TENANT,
            "package_type": "joint_commission",
            "period_label": "2026-06",
        }, headers=AUTH)
        assert "application/pdf" in r.headers.get("content-type", "")

    def test_pdf_endpoint_has_content(self):
        r = client.post("/api/regulatory/audit-package/pdf", json={
            "tenant_id": TENANT,
            "package_type": "full",
            "period_label": "2026-06",
        }, headers=AUTH)
        assert len(r.content) > 100

    def test_pdf_starts_with_pdf_header(self):
        r = client.post("/api/regulatory/audit-package/pdf", json={
            "tenant_id": TENANT,
            "package_type": "aami",
            "period_label": "2026-06",
        }, headers=AUTH)
        assert r.content[:4] == b"%PDF"

    def test_build_regulatory_audit_pdf_direct(self):
        from app.services.report_pdf import build_regulatory_audit_pdf
        package = {
            "package_type": "joint_commission",
            "period_label": "2026-06",
            "generated_at": "2026-06-20T00:00:00+00:00",
            "accreditation_score": 85.0,
            "readiness_tier": "conditional",
            "standards_covered": ["JC-IC.02.02.01", "AAMI-ST79-4"],
            "findings": [
                {
                    "severity": "high",
                    "standard_code": "JC-IC.02.02.01",
                    "finding_category": "blood",
                    "occurrence_count": 3,
                    "rate_pct": 2.1,
                    "remediation_guidance": "Re-decontaminate immediately.",
                }
            ],
            "recommended_actions": ["Fix critical findings."],
            "attestation": {
                "statement": "Auto-generated by LumenAI.",
                "generated_by": "test",
                "system_version": "P8.1",
            },
        }
        pdf = build_regulatory_audit_pdf(package)
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 100
