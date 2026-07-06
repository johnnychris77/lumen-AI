"""v1.5 — Quality Intelligence & Continuous Improvement."""
from datetime import date

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.models.inspection_finding import InspectionFinding
from app.models.root_cause import ROOT_CAUSES
from app.services.capa_suggestion_service import generate_capa_suggestions
from app.services.finding_trend_service import finding_trends
from app.services.anatomy_risk_service import anatomy_risk_dashboard

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "a1b2c3d4" + "0" * 56
TENANT = "default-tenant"


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"qi-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


_next_synthetic_inspection_id = [900000]


def _seed_finding(finding_type: str, zone: str, instrument_type: str = "kerrison_rongeur", severity: int = 2) -> None:
    _next_synthetic_inspection_id[0] += 1
    db = SessionLocal()
    try:
        db.add(InspectionFinding(
            inspection_id=_next_synthetic_inspection_id[0],
            tenant_id=TENANT, instrument_type=instrument_type,
            finding_type=finding_type, zone=zone, severity_index=severity,
        ))
        db.commit()
    finally:
        db.close()


class TestFindingTrends:
    def test_finding_trends_aggregate_correctly(self):
        for _ in range(3):
            _seed_finding("blood", "box lock")
        trends = finding_trends(SessionLocal(), TENANT, granularity="monthly")
        assert trends["totals"]["blood"] >= 3
        assert "wear" in trends["totals"]  # full taxonomy always present, even at 0
        assert trends["granularity"] == "monthly"

    def test_unknown_granularity_falls_back_to_monthly(self):
        trends = finding_trends(SessionLocal(), TENANT, granularity="bogus")
        assert trends["granularity"] == "monthly"


class TestAnatomyRisk:
    def test_anatomy_trends_aggregate_correctly(self):
        # anatomy_risk_dashboard truncates to the top 10 zones by count, so
        # asserting against it directly isn't robust once the shared test
        # database accumulates real InspectionFinding rows from every other
        # test in the full suite. Use a tenant no other test writes to, so
        # this test's aggregation is isolated and its own zone is always #1.
        isolated_tenant = "quality-intelligence-anatomy-test-tenant"
        db = SessionLocal()
        try:
            db.add(InspectionFinding(
                inspection_id=999999, tenant_id=isolated_tenant,
                instrument_type="kerrison_rongeur", finding_type="blood",
                zone="serrations", severity_index=2,
            ))
            for _ in range(4):
                db.add(InspectionFinding(
                    inspection_id=999998, tenant_id=isolated_tenant,
                    instrument_type="kerrison_rongeur", finding_type="blood",
                    zone="box lock", severity_index=2,
                ))
            db.commit()
        finally:
            db.close()

        dashboard = anatomy_risk_dashboard(SessionLocal(), isolated_tenant)
        top_zone = dashboard["highest_risk_anatomy_zones"][0]
        assert top_zone["zone"] == "box lock"
        assert top_zone["count"] == 4
        assert any(z["zone"] == "box lock" for z in dashboard["most_frequent_contamination_zones"])


class TestQualityDashboard:
    def _create(self, itype, declared=None):
        _baseline(itype)
        r = client.post("/api/inspections", json={
            "instrument_type": itype, "site_name": "Mercy",
            "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
            "finding_categories": declared or [],
        }, headers=AUTH_OPERATOR)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def test_dashboard_returns_kpis(self):
        self._create("scissors")
        r = client.get("/api/quality/dashboard", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "inspection_volume", "pass_rate_pct", "reclean_rate_pct",
            "repair_rate_pct", "remove_from_service_rate_pct",
            "supervisor_override_rate_pct", "baseline_compliance_pct",
            "coverage_compliance_pct", "ai_confidence_trend_pct",
        ):
            assert key in body

    def test_benchmark_compares_reporting_periods(self):
        self._create("forceps")
        r = client.get("/api/quality/benchmark", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert "current_month" in body
        assert "previous_month" in body
        assert "quarter" in body
        assert "rolling_12_months" in body
        assert "pass_rate_pct" in body["comparison_current_vs_previous_month"]

    def test_executive_quality_score_calculates(self):
        self._create("needle_holder")
        r = client.get("/api/quality/executive-score", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["score"] is None or 0 <= body["score"] <= 100

    def test_technician_quality_leadership_only(self):
        self._create("scissors")
        r = client.get("/api/quality/technician-quality", headers=AUTH_OPERATOR)
        assert r.status_code == 403
        r2 = client.get("/api/quality/technician-quality", headers=AUTH_MGR)
        assert r2.status_code == 200
        technicians = r2.json()["technicians"]
        assert any(t["technician"] == "operator@local.dev" for t in technicians)

    def test_technician_metrics_calculate_correctly(self):
        iid = self._create("scissors", declared=["blood"])
        client.post(
            f"/api/inspections/{iid}/supervisor-review",
            json={"agreement": "agree"}, headers=AUTH_MGR,
        )
        r = client.get("/api/quality/technician-quality", headers=AUTH_MGR)
        tech = next(t for t in r.json()["technicians"] if t["technician"] == "operator@local.dev")
        assert tech["inspection_count"] >= 1
        assert tech["supervisor_agreement_pct"] is not None

    def test_supervisor_quality_dashboard(self):
        iid = self._create("scissors")
        client.post(
            f"/api/inspections/{iid}/supervisor-review",
            json={"agreement": "disagree", "rationale": "Debris still present.", "corrected_zone": "box lock"},
            headers=AUTH_MGR,
        )
        r = client.get("/api/quality/supervisor-quality", headers=AUTH_MGR)
        assert r.status_code == 200
        supervisors = r.json()["supervisors"]
        assert any(s["reviewer"] == "spd_manager@local.dev" for s in supervisors)


class TestRootCause:
    def test_root_cause_categories_stored_correctly(self):
        iid = self._create_inspection()
        r = client.post(
            "/api/quality/root-cause",
            json={"inspection_id": iid, "finding_type": "blood", "root_cause": "improper_brushing"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text
        assert r.json()["root_cause"] == "improper_brushing"

        r2 = client.get("/api/quality/root-cause-trends", headers=AUTH_ADMIN)
        assert r2.status_code == 200
        assert r2.json()["overall"].get("improper_brushing", 0) >= 1

    def test_invalid_root_cause_rejected(self):
        iid = self._create_inspection()
        r = client.post(
            "/api/quality/root-cause",
            json={"inspection_id": iid, "finding_type": "blood", "root_cause": "not_a_real_cause"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 422

    def test_all_root_causes_are_valid_choices(self):
        assert "unknown" in ROOT_CAUSES
        assert "incomplete_manual_cleaning" in ROOT_CAUSES

    def _create_inspection(self):
        _baseline("scissors")
        r = client.post("/api/inspections", json={
            "instrument_type": "scissors", "site_name": "Mercy",
            "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        }, headers=AUTH_OPERATOR)
        return r.json()["id"]


class TestCapaSuggestions:
    def test_capa_recommendations_generated(self):
        for _ in range(4):
            _seed_finding("rust", "hinge", instrument_type="rigid_scope")
        suggestions = generate_capa_suggestions(SessionLocal(), TENANT)
        assert any("rust" in s["trigger"].lower() for s in suggestions)
        assert all("recommendation" in s for s in suggestions)

    def test_capa_suggestion_endpoint_and_create(self):
        for _ in range(4):
            _seed_finding("blood", "serration", instrument_type="needle_holder")
        r = client.get("/api/quality/capa-suggestions", headers=AUTH_MGR)
        assert r.status_code == 200
        suggestions = r.json()["suggestions"]
        assert len(suggestions) > 0

        r2 = client.post("/api/quality/capa-suggestions/create", json=suggestions[0], headers=AUTH_MGR)
        assert r2.status_code == 201, r2.text
        assert r2.json()["title"] == suggestions[0]["suggested_title"]


class TestContinuousImprovement:
    def test_create_and_update_initiative(self):
        r = client.post(
            "/api/quality/improvement-initiatives",
            json={
                "initiative": "Retrain on Kerrison box-lock brushing",
                "owner": "SPD Manager", "target_date": str(date(2026, 9, 1)),
                "expected_impact": "Reduce repeated blood findings in box locks by 50%.",
            },
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text
        initiative_id = r.json()["id"]

        r2 = client.get("/api/quality/improvement-initiatives", headers=AUTH_MGR)
        assert any(i["id"] == initiative_id for i in r2.json()["initiatives"])

        r3 = client.patch(
            f"/api/quality/improvement-initiatives/{initiative_id}",
            json={"status": "completed", "actual_impact": "Reduced by 60%."},
            headers=AUTH_MGR,
        )
        assert r3.status_code == 200
        assert r3.json()["status"] == "completed"
