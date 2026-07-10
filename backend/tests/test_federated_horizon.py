"""v3.4 — Project Horizon: Federated Clinical Intelligence & Global Learning Network tests."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import RepairRequest

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


def _enroll(tenant_id: str) -> dict:
    res = client.post("/api/horizon/participation/enroll", json={
        "participant_type": "hospital", "region": "north_america", "contribution_categories": ["benchmark", "research"],
    }, headers=_headers(AUTH_MGR, tenant_id))
    assert res.status_code == 200, res.text
    return res.json()


def _make_inspection(tenant_id: str, *, days_ago: int = 0, **overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, file_name="x.jpg", instrument_type="kerrison_rongeur",
            has_image=True, image_sha256="d4" * 32, score_status="scored", risk_score=10,
            detected_issue="none", stain_detected=False, supervisor_review_required=False,
            qa_review_status="pending", status="pending", inspected_zones_json="null",
            coverage_pct=90, baseline_status="approved", disposition="PASS", technician="Alex Tech",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_finding(tenant_id: str, inspection_id: int, *, days_ago: int = 0, **overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, inspection_id=inspection_id, instrument_type="kerrison_rongeur",
            finding_type="blood", zone="serrations", created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        db.add(InspectionFinding(**defaults))
        db.commit()
    finally:
        db.close()


def _make_repair(tenant_id: str, inspection_id: int, *, days_ago: int = 0, **overrides) -> None:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=tenant_id, inspection_id=inspection_id, instrument_identity="barcode:x", vendor_name="AcmeSurgical",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        defaults.update(overrides)
        db.add(RepairRequest(**defaults))
        db.commit()
    finally:
        db.close()


def _enroll_k_tenants(k: int, *, instrument_type: str = "kerrison_rongeur", finding_type: str = "corrosion") -> list[str]:
    tenant_ids = []
    for _ in range(k):
        tenant_id = uid("tenant")
        _enroll(tenant_id)
        insp_id = _make_inspection(tenant_id, instrument_type=instrument_type, days_ago=5)
        _make_finding(tenant_id, insp_id, finding_type=finding_type, zone="box-lock", instrument_type=instrument_type, days_ago=5)
        tenant_ids.append(tenant_id)
    return tenant_ids


class TestParticipationAndDeIdentification:
    def test_enroll_creates_participant_and_agreement(self):
        tenant_id = uid("tenant")
        result = _enroll(tenant_id)
        assert result["participant"]["enrollment_status"] == "pending"
        assert result["sharing_agreement"]["status"] == "active"

    def test_enroll_is_idempotent(self):
        tenant_id = uid("tenant")
        first = _enroll(tenant_id)
        second = _enroll(tenant_id)
        assert first["participant"]["id"] == second["participant"]["id"]

    def test_withdraw_organization(self):
        tenant_id = uid("tenant")
        _enroll(tenant_id)
        res = client.post("/api/horizon/participation/withdraw", headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        assert res.json()["sharing_agreement"]["status"] == "withdrawn"

    def test_unenrolled_organization_has_no_participation(self):
        tenant_id = uid("tenant")
        res = client.get("/api/horizon/participation/status", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200
        assert res.json()["enrolled"] is False


class TestKnowledgeContributionWorkflowAndVersioning:
    def test_submit_contribution_starts_pending_review(self):
        tenant_id = uid("tenant")
        res = client.post("/api/horizon/contributions", json={
            "contribution_type": "anatomy_guidance", "category": "hip_zone", "title": "Hip zone inspection guidance",
            "body": "Detailed guidance text.",
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 200
        body = res.json()
        assert body["approval_status"] == "pending_review"
        assert body["version"] == 1

    def test_de_identification_hides_source_tenant_from_other_orgs(self):
        tenant_a = uid("tenant-a")
        tenant_b = uid("tenant-b")
        client.post("/api/horizon/contributions", json={
            "contribution_type": "best_practice", "category": "cleaning", "title": "Best practice X", "body": "Body.",
        }, headers=_headers(AUTH_MGR, tenant_a))

        listed_by_other_org = client.get("/api/horizon/contributions", headers=_headers(AUTH_VIEWER, tenant_b)).json()["contributions"]
        assert all("source_tenant_id" not in c for c in listed_by_other_org)

        listed_by_own_org = client.get("/api/horizon/contributions", headers=_headers(AUTH_VIEWER, tenant_a)).json()["contributions"]
        own = next(c for c in listed_by_own_org if c["title"] == "Best practice X")
        assert own["source_tenant_id"] == tenant_a

    def test_invalid_contribution_type_rejected(self):
        tenant_id = uid("tenant")
        res = client.post("/api/horizon/contributions", json={
            "contribution_type": "not_a_real_type", "title": "X", "body": "Y",
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 422


class TestGovernanceApproval:
    def test_approve_contribution(self):
        tenant_id = uid("tenant")
        contribution = client.post("/api/horizon/contributions", json={
            "contribution_type": "educational_content", "title": "Training Module", "body": "Content.",
        }, headers=_headers(AUTH_MGR, tenant_id)).json()

        approved = client.post(f"/api/horizon/contributions/{contribution['id']}/approve", headers=_headers(AUTH_ADMIN, tenant_id))
        assert approved.status_code == 200
        assert approved.json()["approval_status"] == "approved"

    def test_reject_contribution_with_reason(self):
        tenant_id = uid("tenant")
        contribution = client.post("/api/horizon/contributions", json={
            "contribution_type": "failure_pattern", "title": "Pattern A", "body": "Content.",
        }, headers=_headers(AUTH_MGR, tenant_id)).json()

        rejected = client.post(f"/api/horizon/contributions/{contribution['id']}/reject", json={
            "reason": "Insufficient supporting evidence.",
        }, headers=_headers(AUTH_ADMIN, tenant_id))
        assert rejected.status_code == 200
        assert rejected.json()["approval_status"] == "rejected"
        assert rejected.json()["rejection_reason"] == "Insufficient supporting evidence."

    def test_cannot_approve_already_reviewed_contribution(self):
        tenant_id = uid("tenant")
        contribution = client.post("/api/horizon/contributions", json={
            "contribution_type": "best_practice", "title": "Pattern B", "body": "Content.",
        }, headers=_headers(AUTH_MGR, tenant_id)).json()
        client.post(f"/api/horizon/contributions/{contribution['id']}/approve", headers=_headers(AUTH_ADMIN, tenant_id))

        second_attempt = client.post(f"/api/horizon/contributions/{contribution['id']}/approve", headers=_headers(AUTH_ADMIN, tenant_id))
        assert second_attempt.status_code == 409

    def test_approve_unknown_contribution_404s(self):
        tenant_id = uid("tenant")
        res = client.post("/api/horizon/contributions/999999/approve", headers=_headers(AUTH_ADMIN, tenant_id))
        assert res.status_code == 404


class TestKnowledgeVersioning:
    def test_revise_creates_new_version_and_links_chain(self):
        tenant_id = uid("tenant")
        original = client.post("/api/horizon/contributions", json={
            "contribution_type": "anatomy_guidance", "title": "Guidance V1", "body": "V1 body.",
        }, headers=_headers(AUTH_MGR, tenant_id)).json()
        client.post(f"/api/horizon/contributions/{original['id']}/approve", headers=_headers(AUTH_ADMIN, tenant_id))

        revised = client.post(f"/api/horizon/contributions/{original['id']}/revise", json={
            "title": "Guidance V2", "body": "V2 body.",
        }, headers=_headers(AUTH_MGR, tenant_id))
        assert revised.status_code == 200
        revised_body = revised.json()
        assert revised_body["version"] == 2
        assert revised_body["supersedes_ref"] == original["contribution_ref"]

        history = client.get(f"/api/horizon/contributions/{original['contribution_ref']}/versions", headers=_headers(AUTH_VIEWER, tenant_id))
        assert history.status_code == 200
        versions = history.json()["versions"]
        assert [v["version"] for v in versions] == [1, 2]
        assert all("source_tenant_id" not in v for v in versions)

    def test_cannot_revise_pending_contribution(self):
        tenant_id = uid("tenant")
        pending = client.post("/api/horizon/contributions", json={
            "contribution_type": "best_practice", "title": "Pending Item", "body": "Body.",
        }, headers=_headers(AUTH_MGR, tenant_id)).json()

        res = client.post(f"/api/horizon/contributions/{pending['id']}/revise", json={"title": "New title"}, headers=_headers(AUTH_MGR, tenant_id))
        assert res.status_code == 409


class TestFederatedAggregationAndBenchmarking:
    def test_federated_signal_suppressed_below_k_threshold(self):
        tenant_ids = _enroll_k_tenants(3)  # below GLOBAL_K_THRESHOLD (10)
        res = client.post("/api/horizon/federated-signals/generate", headers=_headers(AUTH_MGR, tenant_ids[0]))
        assert res.status_code == 200
        signals = res.json()["signals"]
        assert len(signals) > 0
        assert all(not s["published"] and s["value"] is None for s in signals)

    def test_benchmark_computation_shape(self):
        tenant_ids = _enroll_k_tenants(3)
        res = client.get("/api/horizon/benchmarks", headers=_headers(AUTH_VIEWER, tenant_ids[0]))
        assert res.status_code == 200
        benchmarks = res.json()["benchmarks"]
        # 8, not 6: Project Beacon (v3.5) extended BENCHMARK_METRICS with
        # "repair_category_rate" and "digital_twin_health_score".
        assert len(benchmarks) == 8
        assert all(b["suppressed"] for b in benchmarks if b["n_facilities"] < 5)

    def test_benchmark_percentile_never_returns_raw_org_data(self):
        tenant_ids = _enroll_k_tenants(3)
        res = client.get(
            "/api/horizon/benchmarks/percentile", params={"metric_name": "coverage_trend"}, headers=_headers(AUTH_VIEWER, tenant_ids[0]),
        )
        assert res.status_code == 200
        body = res.json()
        assert "network_p90" not in body
        assert "tenant_value" not in body  # never the raw number, only a percentile band once unsuppressed

    def test_invalid_benchmark_metric_rejected(self):
        tenant_id = uid("tenant")
        res = client.get("/api/horizon/benchmarks/percentile", params={"metric_name": "not_a_metric"}, headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 422


class TestEmergingTrendDetection:
    def test_detect_emerging_trend_across_enrolled_orgs(self):
        tenant_ids = _enroll_k_tenants(5, instrument_type="orthopedic_drill", finding_type="corrosion")
        res = client.post("/api/horizon/emerging-trends/detect", headers=_headers(AUTH_MGR, tenant_ids[0]))
        assert res.status_code == 200
        trends = res.json()["trends"]
        assert any(t["trend_type"] == "new_corrosion_pattern" for t in trends)

    def test_notified_organizations_can_see_their_trend(self):
        tenant_ids = _enroll_k_tenants(5, instrument_type="laparoscope", finding_type="corrosion")
        client.post("/api/horizon/emerging-trends/detect", headers=_headers(AUTH_MGR, tenant_ids[0]))
        mine = client.get("/api/horizon/emerging-trends", params={"mine_only": True}, headers=_headers(AUTH_VIEWER, tenant_ids[0])).json()["trends"]
        assert len(mine) > 0

    def test_acknowledge_trend(self):
        tenant_ids = _enroll_k_tenants(5, instrument_type="cystoscope", finding_type="corrosion")
        trends = client.post("/api/horizon/emerging-trends/detect", headers=_headers(AUTH_MGR, tenant_ids[0])).json()["trends"]
        trend_id = trends[0]["id"]
        res = client.post(f"/api/horizon/emerging-trends/{trend_id}/acknowledge", headers=_headers(AUTH_VIEWER, tenant_ids[0]))
        assert res.status_code == 200
        assert tenant_ids[0] in res.json()["acknowledged_tenant_ids_json"]


class TestResearchPortal:
    def test_research_portal_summary_shape(self):
        res = client.get("/api/horizon/research/portal", headers=AUTH_VIEWER)
        assert res.status_code == 200
        body = res.json()
        for key in ("global_trend_summaries", "global_benchmarks", "emerging_risks", "published_knowledge", "released_datasets", "disclaimer"):
            assert key in body


class TestEvidenceLinking:
    def test_add_and_link_evidence_to_recommendation(self):
        evidence = client.post("/api/horizon/evidence", json={
            "evidence_type": "aami", "title": "AAMI ST79", "citation_text": "AAMI ST79:2seventeen guidance on cleaning validation.",
        }, headers=AUTH_ADMIN)
        assert evidence.status_code == 200
        evidence_id = evidence.json()["id"]

        link = client.post("/api/horizon/evidence/link", json={
            "source_type": "sentinel_recommendation", "source_id": "42", "evidence_id": evidence_id, "relevance_note": "Supports cleaning guidance.",
        }, headers=AUTH_ADMIN)
        assert link.status_code == 200

        linked = client.get("/api/horizon/evidence/for/sentinel_recommendation/42", headers=AUTH_VIEWER)
        assert linked.status_code == 200
        assert len(linked.json()["evidence"]) == 1
        assert linked.json()["evidence"][0]["title"] == "AAMI ST79"

    def test_private_evidence_not_visible_to_other_tenants(self):
        tenant_a = uid("tenant-a")
        tenant_b = uid("tenant-b")
        client.post("/api/horizon/evidence", json={
            "evidence_type": "org_sop", "title": "Internal SOP", "citation_text": "Our SOP.", "private": True,
        }, headers=_headers(AUTH_MGR, tenant_a))

        visible_to_b = client.get("/api/horizon/evidence", headers=_headers(AUTH_VIEWER, tenant_b)).json()["evidence"]
        assert all(e["title"] != "Internal SOP" for e in visible_to_b)

        visible_to_a = client.get("/api/horizon/evidence", headers=_headers(AUTH_VIEWER, tenant_a)).json()["evidence"]
        assert any(e["title"] == "Internal SOP" for e in visible_to_a)

    def test_invalid_evidence_type_rejected(self):
        res = client.post("/api/horizon/evidence", json={
            "evidence_type": "not_a_real_type", "title": "X", "citation_text": "Y",
        }, headers=AUTH_ADMIN)
        assert res.status_code == 422

    def test_link_to_unknown_evidence_rejected(self):
        res = client.post("/api/horizon/evidence/link", json={
            "source_type": "insight_recommendation", "source_id": "1", "evidence_id": 999999,
        }, headers=AUTH_ADMIN)
        assert res.status_code == 422


class TestGlobalKnowledgeGraphAndImprovement:
    def test_generate_global_graph_gated_by_k_anonymity(self):
        tenant_ids = _enroll_k_tenants(3, instrument_type="bronchoscope", finding_type="blood")
        res = client.post("/api/horizon/knowledge-graph/global/generate", headers=_headers(AUTH_MGR, tenant_ids[0]))
        assert res.status_code == 200
        edges = res.json()["edges"]
        assert all(not e["published"] for e in edges if e["tenant_count"] < 10)

    def test_local_graph_reuses_existing_knowledge_graph_service(self):
        tenant_id = uid("tenant")
        res = client.get("/api/horizon/knowledge-graph/local", headers=_headers(AUTH_VIEWER, tenant_id))
        assert res.status_code == 200
        assert "explore" in res.json()
        assert "learning_confidence" in res.json()

    def test_ai_improvement_suggestions_shape(self):
        res = client.get("/api/horizon/ai-improvement/suggestions", headers=AUTH_VIEWER)
        assert res.status_code == 200
        body = res.json()
        assert "suggestions" in body
        assert "count_by_target_system" in body


class TestGovernanceCenter:
    def test_governance_overview_shape(self):
        tenant_id = uid("tenant")
        _enroll(tenant_id)
        res = client.get("/api/horizon/governance/overview", headers=_headers(AUTH_ADMIN, tenant_id))
        assert res.status_code == 200
        body = res.json()
        assert body["participation"]["enrolled"] is True
        assert "pending_contribution_approvals" in body
        assert "audit_trail" in body
