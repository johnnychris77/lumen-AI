"""v4.7 — LumenAI OS: Project Apollo — Autonomous Clinical Quality
Management System (CQMS) tests.

Covers: CAPA Engine, Root Cause Intelligence, Audit workflows, Competency
Center, Policy Intelligence, Standards Library, Quality Digital Twin, and
the Executive Quality Dashboard.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.apollo_quality import CustomerComplaint
from app.models.inspection import Inspection
from app.models.or_connect import RepairRequest
from app.models.supervisor_review import SupervisorReview
from app.services import (
    apollo_audit_center_service,
    apollo_capa_engine_service,
    apollo_competency_center_service,
    apollo_executive_quality_service,
    apollo_improvement_portfolio_service,
    apollo_policy_service,
    apollo_quality_twin_service,
    apollo_rca_intelligence_service,
    apollo_standards_library_service,
)
from app.services.capa_suggestion_service import generate_capa_suggestions

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


# ── 1. CAPA Engine ────────────────────────────────────────────────────────────

def test_capa_engine_summary_composes_lifecycle_and_suggestions():
    tenant_id = uid("apollo-capa")
    db = SessionLocal()
    try:
        result = apollo_capa_engine_service.capa_engine_summary(db, tenant_id)
    finally:
        db.close()
    assert "lifecycle_counts" in result
    assert "pending_suggestions" in result
    assert result["human_review_required"] is True


def test_repeat_repairs_detector_triggers_capa_suggestion():
    tenant_id = uid("apollo-repairs")
    db = SessionLocal()
    try:
        for _ in range(3):
            db.add(RepairRequest(
                tenant_id=tenant_id, inspection_id=1, instrument_identity="SCOPE-XYZ-001",
                vendor_name="Acme Repairs", repair_type="general",
            ))
        db.commit()
        suggestions = generate_capa_suggestions(db, tenant_id)
    finally:
        db.close()
    triggers = [s["trigger"] for s in suggestions]
    assert any("Repeated repairs" in t for t in triggers)


def test_supervisor_overrides_detector_triggers_capa_suggestion():
    tenant_id = uid("apollo-overrides")
    db = SessionLocal()
    try:
        for i in range(3):
            db.add(SupervisorReview(
                inspection_id=i + 1, tenant_id=tenant_id, reviewer_name="Dr. Smith",
                agreement="disagree", override_action="reprocess",
            ))
        db.commit()
        suggestions = generate_capa_suggestions(db, tenant_id)
    finally:
        db.close()
    triggers = [s["trigger"] for s in suggestions]
    assert any("supervisor overrides" in t for t in triggers)


def test_inspection_failures_detector_triggers_capa_suggestion():
    tenant_id = uid("apollo-failures")
    db = SessionLocal()
    try:
        for _ in range(3):
            db.add(Inspection(
                file_name="test.jpg", tenant_id=tenant_id, instrument_type="Kerrison Rongeur",
                disposition="REMOVE FROM SERVICE",
            ))
        db.commit()
        suggestions = generate_capa_suggestions(db, tenant_id)
    finally:
        db.close()
    triggers = [s["trigger"] for s in suggestions]
    assert any("inspection failures" in t for t in triggers)


def test_customer_complaint_lifecycle():
    tenant_id = uid("apollo-complaint")
    db = SessionLocal()
    try:
        complaint = apollo_capa_engine_service.create_complaint(
            db, tenant_id, source="clinical_staff", description="Instrument arrived damaged",
            severity="high", instrument_type="Forceps",
        )
        assert complaint.status == "open"
        linked = apollo_capa_engine_service.link_complaint_to_capa(db, tenant_id, complaint.id, capa_id="42")
        assert linked.status == "linked_to_capa"
        assert linked.linked_capa_id == "42"
    finally:
        db.close()


def test_repeated_customer_complaints_detector_triggers_capa_suggestion():
    tenant_id = uid("apollo-complaints-repeat")
    db = SessionLocal()
    try:
        for _ in range(3):
            db.add(CustomerComplaint(
                tenant_id=tenant_id, source="clinic", description="damaged on arrival",
                severity="medium", instrument_type="Retractor",
            ))
        db.commit()
        suggestions = generate_capa_suggestions(db, tenant_id)
    finally:
        db.close()
    triggers = [s["trigger"] for s in suggestions]
    assert any("customer complaints" in t for t in triggers)


def test_capa_summary_route_requires_auth():
    tenant_id = uid("apollo-capa-route")
    resp = client.get("/api/apollo/capa/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 200
    assert "lifecycle_counts" in resp.json()

    resp_noauth = client.get("/api/apollo/capa/summary")
    assert resp_noauth.status_code in (401, 403)


# ── 2. Root Cause Intelligence ────────────────────────────────────────────────

def test_pareto_view_returns_ranked_root_causes():
    tenant_id = uid("apollo-rca-pareto")
    db = SessionLocal()
    try:
        result = apollo_rca_intelligence_service.pareto_view(db, tenant_id)
    finally:
        db.close()
    assert result["methodology"] == "pareto"
    assert "rows" in result
    assert result["human_review_required"] is True


def test_trend_view_returns_by_finding_type():
    tenant_id = uid("apollo-rca-trend")
    db = SessionLocal()
    try:
        result = apollo_rca_intelligence_service.trend_view(db, tenant_id)
    finally:
        db.close()
    assert result["methodology"] == "trend_analysis"
    assert "by_finding_type" in result


def test_rca_summary_composes_pareto_and_trend():
    tenant_id = uid("apollo-rca-summary")
    db = SessionLocal()
    try:
        result = apollo_rca_intelligence_service.rca_intelligence_summary(db, tenant_id)
    finally:
        db.close()
    assert "pareto" in result
    assert "trend_analysis" in result
    assert "pending_draft_count" in result


def test_rca_route_pareto():
    tenant_id = uid("apollo-rca-route")
    resp = client.get("/api/apollo/rca/pareto", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 200
    assert resp.json()["methodology"] == "pareto"


def test_five_whys_view_missing_draft_raises_404_via_route():
    tenant_id = uid("apollo-rca-404")
    resp = client.get("/api/apollo/rca/five-whys/999999", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 404


# ── 3. Audit workflows ────────────────────────────────────────────────────────

def test_audit_center_summary_lists_all_package_types():
    tenant_id = uid("apollo-audit-summary")
    db = SessionLocal()
    try:
        result = apollo_audit_center_service.audit_center_summary(db, tenant_id)
    finally:
        db.close()
    for pkg_type in ("aami_st91", "aorn", "dnv", "internal", "vendor"):
        assert pkg_type in result["supported_package_types"]


def test_generate_audit_for_new_package_types():
    tenant_id = uid("apollo-audit-gen")
    db = SessionLocal()
    try:
        for package_type in ("aami_st91", "aorn", "dnv", "internal", "vendor"):
            result = apollo_audit_center_service.generate_audit(
                tenant_id, package_type=package_type, generated_by="tester", db=db,
            )
            assert result["package_type"] == package_type
    finally:
        db.close()


def test_generate_audit_rejects_unsupported_package_type():
    tenant_id = uid("apollo-audit-bad")
    db = SessionLocal()
    try:
        try:
            apollo_audit_center_service.generate_audit(tenant_id, package_type="not_a_real_body", db=db)
            assert False, "expected UnsupportedAuditPackageTypeError"
        except apollo_audit_center_service.UnsupportedAuditPackageTypeError:
            pass
    finally:
        db.close()


def test_audit_generate_route():
    tenant_id = uid("apollo-audit-route")
    resp = client.post(
        "/api/apollo/audit/generate", json={"package_type": "dnv"}, headers=_headers(AUTH_MGR, tenant_id),
    )
    assert resp.status_code == 200
    assert resp.json()["package_type"] == "dnv"


def test_audit_generate_route_forbidden_for_viewer():
    tenant_id = uid("apollo-audit-viewer")
    resp = client.post(
        "/api/apollo/audit/generate", json={"package_type": "internal"}, headers=_headers(AUTH_VIEWER, tenant_id),
    )
    assert resp.status_code == 403


# ── 4. Competencies ────────────────────────────────────────────────────────────

def test_record_annual_competency_and_summary():
    tenant_id = uid("apollo-competency")
    db = SessionLocal()
    try:
        result = apollo_competency_center_service.record_annual_competency(
            db, tenant_id=tenant_id, technician="tech-apollo-1", competency_area="endoscope reprocessing",
        )
        assert result["annual_competencies"] == 1
    finally:
        db.close()


def test_record_simulation_result_pass_and_fail():
    tenant_id = uid("apollo-sim")
    db = SessionLocal()
    try:
        passed = apollo_competency_center_service.record_simulation_result(
            db, tenant_id=tenant_id, technician="tech-apollo-2", scenario="mock_recall_drill", passed=True,
        )
        assert passed["simulations_passed"] == 1
        failed = apollo_competency_center_service.record_simulation_result(
            db, tenant_id=tenant_id, technician="tech-apollo-2", scenario="mock_recall_drill", passed=False,
        )
        assert failed["simulations_failed"] == 1
    finally:
        db.close()


def test_record_knowledge_contribution():
    tenant_id = uid("apollo-knowledge")
    db = SessionLocal()
    try:
        result = apollo_competency_center_service.record_knowledge_contribution(
            db, tenant_id=tenant_id, technician="tech-apollo-3", topic="Best practice: lumen brushing",
        )
        assert result["knowledge_contributions"] == 1
    finally:
        db.close()


def test_competency_route_requires_leadership_role():
    tenant_id = uid("apollo-competency-route")
    resp = client.post(
        "/api/apollo/competency/annual", json={"technician": "tech-route", "competency_area": "sterilization"},
        headers=_headers(AUTH_VIEWER, tenant_id),
    )
    assert resp.status_code == 403

    resp_admin = client.post(
        "/api/apollo/competency/annual", json={"technician": "tech-route", "competency_area": "sterilization"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert resp_admin.status_code == 200


# ── 5. Policies ────────────────────────────────────────────────────────────────

def test_create_and_publish_policy_versioning():
    tenant_id = uid("apollo-policy")
    db = SessionLocal()
    try:
        v1 = apollo_policy_service.create_policy(db, tenant_id, title="Endoscope Reprocessing Policy", owner="Quality Director")
        assert v1["version"] == 1
        assert v1["status"] == "draft"

        published = apollo_policy_service.publish_policy(db, tenant_id, v1["id"], published_by="qa-lead")
        assert published["status"] == "published"

        v2 = apollo_policy_service.create_policy(
            db, tenant_id, title="Endoscope Reprocessing Policy v2", owner="Quality Director", supersedes_id=v1["id"],
        )
        assert v2["version"] == 2
        apollo_policy_service.publish_policy(db, tenant_id, v2["id"], published_by="qa-lead")

        prior = apollo_policy_service.get_policy(db, tenant_id, v1["id"])
        assert prior["status"] == "superseded"

        history = apollo_policy_service.version_history(db, tenant_id, v2["id"])
        assert len(history) == 2
    finally:
        db.close()


def test_policies_due_for_review():
    tenant_id = uid("apollo-policy-review")
    db = SessionLocal()
    try:
        overdue = apollo_policy_service.create_policy(
            db, tenant_id, title="Overdue Policy", owner="QA",
            review_date=datetime.now(timezone.utc) - timedelta(days=5),
        )
        apollo_policy_service.publish_policy(db, tenant_id, overdue["id"], published_by="qa-lead")

        due = apollo_policy_service.policies_due_for_review(db, tenant_id, within_days=30)
        assert any(p["id"] == overdue["id"] for p in due)
    finally:
        db.close()


def test_policy_route_create_and_list():
    tenant_id = uid("apollo-policy-route")
    resp = client.post(
        "/api/apollo/policies", json={"title": "Route Policy", "owner": "QA"}, headers=_headers(AUTH_MGR, tenant_id),
    )
    assert resp.status_code == 201
    resp_list = client.get("/api/apollo/policies", headers=_headers(AUTH_MGR, tenant_id))
    assert resp_list.status_code == 200
    assert len(resp_list.json()["policies"]) >= 1


# ── 6. Standards ───────────────────────────────────────────────────────────────

def test_regulatory_catalogue_includes_new_bodies():
    from app.services.regulatory_standards_catalogue import get_standards

    bodies = {s.body for s in get_standards()}
    assert "aami_st91" in bodies
    assert "aorn" in bodies
    assert "dnv" in bodies


def test_standards_library_summary_composes_all_sources():
    tenant_id = uid("apollo-standards")
    db = SessionLocal()
    try:
        result = apollo_standards_library_service.standards_library_summary(db, tenant_id)
    finally:
        db.close()
    assert "regulatory_standards" in result
    assert "beacon_guidance" in result
    assert "internal_classification_standards" in result
    assert result["regulatory_body_counts"].get("aorn", 0) >= 1


def test_standards_library_route():
    tenant_id = uid("apollo-standards-route")
    resp = client.get("/api/apollo/standards/library", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 200
    assert "regulatory_standards" in resp.json()


# ── 7. Digital Twin ────────────────────────────────────────────────────────────

def test_compute_quality_twin_returns_eight_dimensions():
    tenant_id = uid("apollo-twin")
    db = SessionLocal()
    try:
        result = apollo_quality_twin_service.compute_quality_twin(db, tenant_id, "sterile_processing")
    finally:
        db.close()
    for key in (
        "compliance_score", "competency_score", "audit_readiness_score", "policy_maturity_score",
        "capa_health_score", "education_score", "knowledge_score", "continuous_improvement_score",
    ):
        assert key in result["scores"]
    assert result["overall_score"] >= 0
    assert result["human_review_required"] is True


def test_quality_twin_history_returns_snapshots():
    tenant_id = uid("apollo-twin-history")
    db = SessionLocal()
    try:
        apollo_quality_twin_service.compute_quality_twin(db, tenant_id, "unspecified")
        apollo_quality_twin_service.compute_quality_twin(db, tenant_id, "unspecified")
        history = apollo_quality_twin_service.twin_history(db, tenant_id, "unspecified")
    finally:
        db.close()
    assert len(history) == 2


def test_quality_twin_route():
    tenant_id = uid("apollo-twin-route")
    resp = client.get("/api/apollo/quality-twin/unspecified", headers=_headers(AUTH_MGR, tenant_id))
    assert resp.status_code == 200
    assert "overall_score" in resp.json()


# ── 8. Executive Dashboard ─────────────────────────────────────────────────────

def test_executive_quality_dashboard_composes_command_center_and_governance():
    tenant_id = uid("apollo-exec")
    db = SessionLocal()
    try:
        result = apollo_executive_quality_service.executive_quality_dashboard(db, tenant_id)
    finally:
        db.close()
    assert "quality_maturity_index" in result
    assert "quality_maturity_index_weights" in result
    assert "audit_readiness" in result
    assert "continuous_improvement" in result
    assert result["human_review_required"] is True


def test_executive_quality_dashboard_index_within_bounds():
    tenant_id = uid("apollo-exec-bounds")
    db = SessionLocal()
    try:
        result = apollo_executive_quality_service.executive_quality_dashboard(db, tenant_id)
    finally:
        db.close()
    assert 0 <= result["quality_maturity_index"] <= 100


def test_executive_dashboard_route_requires_leadership():
    tenant_id = uid("apollo-exec-route")
    resp = client.get("/api/apollo/executive-dashboard", headers=_headers(AUTH_VIEWER, tenant_id))
    assert resp.status_code == 403

    resp_admin = client.get("/api/apollo/executive-dashboard", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp_admin.status_code == 200


def test_improvement_portfolio_summary_used_by_executive_dashboard():
    tenant_id = uid("apollo-portfolio")
    db = SessionLocal()
    try:
        apollo_improvement_portfolio_service.create_project(
            db, tenant_id=tenant_id, initiative="Reduce reprocessing cycle time", owner="Quality",
            methodology="lean", cost_savings_usd=15000.0, executive_visible=True,
        )
        summary = apollo_improvement_portfolio_service.portfolio_summary(db, tenant_id)
    finally:
        db.close()
    assert summary["total_projects"] == 1
    assert summary["by_methodology"]["lean"] == 1
    assert summary["total_cost_savings_usd"] == 15000.0
    assert len(summary["executive_visible_projects"]) == 1
