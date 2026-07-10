"""v3.1 — Project Atlas: Enterprise Intelligence & Multi-Site Operations tests."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.enterprise_hierarchy import EnterpriseFacility, EnterpriseMarket, HealthSystem
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.knowledge import APPROVED, KnowledgeArticle

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
AUTH_VENDOR = {"Authorization": "Bearer vendor-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _make_system(system_id: str) -> None:
    db = SessionLocal()
    try:
        db.add(HealthSystem(system_id=system_id, system_name="Atlas Test System", admin_email="admin@atlas-test.org"))
        db.commit()
    finally:
        db.close()


def _make_market(market_id: str, system_id: str) -> None:
    db = SessionLocal()
    try:
        db.add(EnterpriseMarket(market_id=market_id, market_name="Atlas Test Market", system_id=system_id))
        db.commit()
    finally:
        db.close()


def _make_facility(facility_id: str, *, system_id: str, market_id: str, tenant_id: str, facility_name: str = "") -> None:
    db = SessionLocal()
    try:
        db.add(EnterpriseFacility(
            facility_id=facility_id, facility_name=facility_name or facility_id, region_id="",
            market_id=market_id, system_id=system_id, tenant_id=tenant_id,
        ))
        db.commit()
    finally:
        db.close()


def _make_inspection(**overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id="atlas-tenant", file_name="x.jpg", instrument_type="kerrison_rongeur",
            has_image=True, image_sha256="a1" * 32, score_status="scored", risk_score=10,
            detected_issue="none", stain_detected=False, supervisor_review_required=False,
            qa_review_status="pending", status="pending", inspected_zones_json="null",
            coverage_pct=100, baseline_status="approved", disposition="PASS", technician="Alex Tech",
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_finding(inspection_id: int, tenant_id: str, **overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(tenant_id=tenant_id, inspection_id=inspection_id, instrument_type="kerrison_rongeur", finding_type="corrosion", zone="serrations")
        defaults.update(overrides)
        db.add(InspectionFinding(**defaults))
        db.commit()
    finally:
        db.close()


def _make_article(tenant_id: str, **overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(tenant_id=tenant_id, category="best_practice", title="Test Article", body="Body text.", author="tech@x.org", approval_status=APPROVED)
        defaults.update(overrides)
        row = KnowledgeArticle(**defaults)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _setup_system() -> tuple[str, str, str, str]:
    """Returns (system_id, market_id, facility_id, tenant_id) for a fresh, isolated system."""
    system_id = uid("sys")
    market_id = uid("mkt")
    facility_id = uid("fac")
    tenant_id = uid("tenant")
    _make_system(system_id)
    _make_market(market_id, system_id)
    _make_facility(facility_id, system_id=system_id, market_id=market_id, tenant_id=tenant_id, facility_name="Test Hospital One")
    return system_id, market_id, facility_id, tenant_id


class TestOrganizationHierarchy:
    """Section 1 — reuses the existing enterprise hierarchy; Atlas adds no new tables for it."""

    def test_facility_links_system_and_market(self):
        system_id, market_id, facility_id, tenant_id = _setup_system()
        db = SessionLocal()
        try:
            facility = db.query(EnterpriseFacility).filter(EnterpriseFacility.facility_id == facility_id).first()
            assert facility.system_id == system_id
            assert facility.market_id == market_id
            assert facility.tenant_id == tenant_id
        finally:
            db.close()

    def test_existing_enterprise_routes_see_the_system(self):
        system_id, *_ = _setup_system()
        res = client.get(f"/api/enterprise/systems/{system_id}", headers=AUTH_ADMIN)
        assert res.status_code == 200
        assert res.json()["system_id"] == system_id


class TestFacilityIsolation:
    def test_dashboard_never_leaks_across_tenants(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        fac_b = uid("fac-b")
        tenant_b = uid("tenant-b")
        _make_facility(fac_b, system_id=system_id, market_id=market_id, tenant_id=tenant_b, facility_name="Test Hospital Two")

        _make_inspection(tenant_id=tenant_a, disposition="PASS")
        _make_inspection(tenant_id=tenant_b, disposition="FAIL")
        _make_inspection(tenant_id=tenant_b, disposition="FAIL")

        dash = client.get(f"/api/atlas/dashboard/{system_id}", headers=AUTH_ADMIN).json()
        assert dash["facility_count"] == 2
        assert dash["inspection_volume"] == 3

        by_facility = {f["facility_id"]: f for f in dash["facility_comparison"]}
        assert by_facility[fac_a]["tenant_id"] == tenant_a
        assert by_facility[fac_b]["tenant_id"] == tenant_b

    def test_facility_intelligence_scoped_to_own_tenant(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        result = client.get(f"/api/atlas/facility-intelligence/{system_id}/{fac_a}", headers=AUTH_ADMIN).json()
        assert result["tenant_id"] == tenant_a
        assert result["facility_id"] == fac_a

    def test_unknown_facility_404s(self):
        system_id, *_ = _setup_system()
        res = client.get(f"/api/atlas/facility-intelligence/{system_id}/does-not-exist", headers=AUTH_ADMIN)
        assert res.status_code == 404


class TestEnterpriseDashboard:
    def test_dashboard_requires_auth_role(self):
        system_id, *_ = _setup_system()
        res = client.get(f"/api/atlas/dashboard/{system_id}", headers=AUTH_VENDOR)
        assert res.status_code == 403

    def test_dashboard_shape(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        _make_inspection(tenant_id=tenant_a, disposition="PASS")
        dash = client.get(f"/api/atlas/dashboard/{system_id}", headers=AUTH_VIEWER).json()
        for key in (
            "enterprise_quality_score", "enterprise_risk_score", "inspection_volume", "pass_rate_pct",
            "coverage_quality_pct", "supervisor_agreement_rate", "digital_twin_health_pct", "facility_comparison",
        ):
            assert key in dash
        assert dash["human_review_required"] is True
        assert dash["disclaimer"]


class TestBenchmarking:
    def test_cross_facility_benchmark_returns_all_facilities(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        insp_id = _make_inspection(tenant_id=tenant_a, disposition="FAIL")
        _make_finding(insp_id, tenant_a, finding_type="corrosion")
        _make_finding(insp_id, tenant_a, finding_type="corrosion")
        _make_finding(insp_id, tenant_a, finding_type="blood")

        result = client.get(f"/api/atlas/benchmarking/{system_id}", headers=AUTH_ADMIN).json()
        assert result["facility_count"] == 1
        facility = result["facilities"][0]
        assert facility["facility_id"] == fac_a
        assert facility["corrosion_finding_count"] == 2
        assert facility["blood_finding_count"] == 1
        assert result["human_review_required"] is True


class TestWatchlists:
    def test_refresh_watchlist_flags_high_repair_facility(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        for _ in range(3):
            _make_inspection(tenant_id=tenant_a, disposition="REPROCESS")

        res = client.post(f"/api/atlas/watchlist/{system_id}/refresh", headers=AUTH_MGR)
        assert res.status_code == 200
        entity_types = {e["entity_type"] for e in res.json()["watchlist"]}
        assert "facility_reclean" in entity_types

    def test_watchlist_entry_resolve(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        for _ in range(3):
            _make_inspection(tenant_id=tenant_a, disposition="REPROCESS")
        watchlist = client.post(f"/api/atlas/watchlist/{system_id}/refresh", headers=AUTH_MGR).json()["watchlist"]
        entry_id = watchlist[0]["id"]
        res = client.post(f"/api/atlas/watchlist/{system_id}/{entry_id}/resolve", headers=AUTH_MGR)
        assert res.status_code == 200
        assert res.json()["status"] == "resolved"

    def test_resolve_unknown_entry_404s(self):
        system_id, *_ = _setup_system()
        res = client.post(f"/api/atlas/watchlist/{system_id}/999999/resolve", headers=AUTH_MGR)
        assert res.status_code == 404


class TestKnowledgeSharing:
    def test_share_approved_article(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        article_id = _make_article(tenant_a)
        res = client.post("/api/atlas/knowledge/share", json={
            "system_id": system_id, "source_tenant_id": tenant_a, "source_article_id": article_id,
            "owner": "author@x.org", "sharing_scope": "system_wide",
        }, headers=AUTH_MGR)
        assert res.status_code == 200
        body = res.json()
        assert body["system_id"] == system_id
        assert body["title"] == "Test Article"

        listed = client.get(f"/api/atlas/knowledge/{system_id}", headers=AUTH_VIEWER).json()["articles"]
        assert any(a["id"] == body["id"] for a in listed)

    def test_cannot_share_unapproved_article(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        article_id = _make_article(tenant_a, approval_status="draft")
        res = client.post("/api/atlas/knowledge/share", json={
            "system_id": system_id, "source_tenant_id": tenant_a, "source_article_id": article_id, "owner": "author@x.org",
        }, headers=AUTH_MGR)
        assert res.status_code == 422

    def test_retract_shared_article(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        article_id = _make_article(tenant_a)
        shared = client.post("/api/atlas/knowledge/share", json={
            "system_id": system_id, "source_tenant_id": tenant_a, "source_article_id": article_id, "owner": "author@x.org",
        }, headers=AUTH_MGR).json()
        res = client.post(f"/api/atlas/knowledge/{system_id}/{shared['id']}/retract", headers=AUTH_MGR)
        assert res.status_code == 200
        listed = client.get(f"/api/atlas/knowledge/{system_id}", headers=AUTH_VIEWER).json()["articles"]
        assert all(a["id"] != shared["id"] for a in listed)


class TestAnalytics:
    def test_trend_returns_series_after_dashboard_snapshot(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        client.get(f"/api/atlas/dashboard/{system_id}", headers=AUTH_ADMIN)
        res = client.get(f"/api/atlas/analytics/{system_id}/trend", params={"metric": "quality_score"}, headers=AUTH_ADMIN)
        assert res.status_code == 200
        body = res.json()
        assert body["metric"] == "quality_score"
        assert isinstance(body["series"], list)

    def test_invalid_metric_rejected(self):
        system_id, *_ = _setup_system()
        res = client.get(f"/api/atlas/analytics/{system_id}/trend", params={"metric": "not_a_metric"}, headers=AUTH_ADMIN)
        assert res.status_code == 422


class TestAlerts:
    def test_generate_and_list_alerts(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        for _ in range(3):
            insp_id = _make_inspection(tenant_id=tenant_a, disposition="FAIL")
            _make_finding(insp_id, tenant_a, finding_type="corrosion")

        client.post(f"/api/atlas/watchlist/{system_id}/refresh", headers=AUTH_MGR)
        res = client.post(f"/api/atlas/alerts/{system_id}/generate", headers=AUTH_MGR)
        assert res.status_code == 200
        listed = client.get(f"/api/atlas/alerts/{system_id}", headers=AUTH_ADMIN).json()["alerts"]
        assert isinstance(listed, list)

    def test_acknowledge_unknown_alert_404s(self):
        system_id, *_ = _setup_system()
        res = client.post(f"/api/atlas/alerts/{system_id}/999999/acknowledge", headers=AUTH_ADMIN)
        assert res.status_code == 404


class TestExecutiveReports:
    def test_generate_report_and_export(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        _make_inspection(tenant_id=tenant_a, disposition="PASS")

        res = client.post(f"/api/atlas/reports/{system_id}/generate", json={"audience": "ceo", "cadence": "monthly"}, headers=AUTH_MGR)
        assert res.status_code == 200
        report = res.json()
        assert report["audience"] == "ceo"
        report_id = report["id"]

        fetched = client.get(f"/api/atlas/reports/{system_id}/{report_id}", headers=AUTH_VIEWER)
        assert fetched.status_code == 200
        assert "summary" in fetched.json()

        csv_res = client.get(f"/api/atlas/reports/{system_id}/{report_id}.csv", headers=AUTH_VIEWER)
        assert csv_res.status_code == 200
        assert csv_res.headers["content-type"].startswith("text/csv")

        xlsx_res = client.get(f"/api/atlas/reports/{system_id}/{report_id}.xlsx", headers=AUTH_VIEWER)
        assert xlsx_res.status_code == 200

        pdf_res = client.get(f"/api/atlas/reports/{system_id}/{report_id}.pdf", headers=AUTH_VIEWER)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"

    def test_invalid_audience_rejected(self):
        system_id, *_ = _setup_system()
        res = client.post(f"/api/atlas/reports/{system_id}/generate", json={"audience": "ceo-nope", "cadence": "monthly"}, headers=AUTH_MGR)
        assert res.status_code == 422

    def test_hospital_summary_report_scopes_to_one_facility(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        _make_inspection(tenant_id=tenant_a, disposition="PASS")
        client.get(f"/api/atlas/dashboard/{system_id}", headers=AUTH_ADMIN)
        res = client.post(f"/api/atlas/reports/{system_id}/generate", json={
            "audience": "hospital_summary", "cadence": "monthly", "facility_id": fac_a,
        }, headers=AUTH_MGR)
        assert res.status_code == 200
        summary = res.json()["summary"]
        assert summary["facility_id"] == fac_a


class TestRolePermissions:
    def test_grant_list_revoke_role(self):
        system_id, *_ = _setup_system()
        user_email = f"{uid('user')}@atlas-test.org"

        granted = client.post("/api/atlas/roles/grant", json={
            "user_email": user_email, "role": "regional_administrator", "scope_type": "system", "scope_id": system_id,
        }, headers=AUTH_ADMIN)
        assert granted.status_code == 200
        assignment_id = granted.json()["id"]

        listed = client.get(f"/api/atlas/roles/{user_email}", headers=AUTH_ADMIN).json()["roles"]
        assert any(r["id"] == assignment_id for r in listed)

        revoked = client.post(f"/api/atlas/roles/{assignment_id}/revoke", headers=AUTH_ADMIN)
        assert revoked.status_code == 200
        listed_after = client.get(f"/api/atlas/roles/{user_email}", headers=AUTH_ADMIN).json()["roles"]
        assert all(r["id"] != assignment_id for r in listed_after)

    def test_system_scope_grants_facility_access(self):
        system_id, market_id, fac_a, tenant_a = _setup_system()
        user_email = f"{uid('user2')}@atlas-test.org"
        client.post("/api/atlas/roles/grant", json={
            "user_email": user_email, "role": "market_director", "scope_type": "system", "scope_id": system_id,
        }, headers=AUTH_ADMIN)

        check = client.get("/api/atlas/roles/access-check", params={
            "user_email": user_email, "scope_type": "facility", "scope_id": fac_a,
        }, headers=AUTH_ADMIN)
        assert check.status_code == 200
        assert check.json()["has_access"] is True

    def test_invalid_role_rejected(self):
        system_id, *_ = _setup_system()
        res = client.post("/api/atlas/roles/grant", json={
            "user_email": "x@x.org", "role": "not_a_real_role", "scope_type": "system", "scope_id": system_id,
        }, headers=AUTH_ADMIN)
        assert res.status_code == 422
