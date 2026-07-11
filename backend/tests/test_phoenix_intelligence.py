"""v4.9 — LumenAI OS: Project Phoenix — Self-Improving Healthcare
Intelligence Platform tests.

Covers: Learning Engine, Recommendation generation, Workflow optimization,
Knowledge evolution, Platform health, Innovation tracking, and Maturity
scoring.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.competency_event import CompetencyEvent
from app.models.knowledge import KnowledgeArticle
from app.models.supervisor_review import SupervisorReview
from app.models.workflow_forge import EXECUTION_FAILED, WorkflowExecution
from app.services import (
    phoenix_ai_observatory_service,
    phoenix_competency_intelligence_service,
    phoenix_innovation_pipeline_service,
    phoenix_knowledge_evolution_service,
    phoenix_learning_engine_service,
    phoenix_maturity_index_service,
    phoenix_platform_health_service,
    phoenix_recommendation_engine,
    phoenix_workflow_optimization_service,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    db.add(models.TenantMembership(tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True))
    db.commit()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


# ── 1. Learning Engine ────────────────────────────────────────────────────────

def test_learning_engine_summary_composes_eight_signals():
    tenant_id = uid("phoenix-learning")
    db = SessionLocal()
    try:
        result = phoenix_learning_engine_service.learning_engine_summary(db, tenant_id)
    finally:
        db.close()
    for key in (
        "inspection_outcomes", "ai_confidence", "supervisor_overrides", "knowledge_usage",
        "workflow_efficiency", "digital_twin_health", "enterprise_trends", "education_effectiveness",
    ):
        assert key in result
    assert result["human_review_required"] is True


def test_learning_engine_route_requires_leadership_and_membership():
    tenant_id = uid("phoenix-learning-route")
    resp_no_member = client.get("/api/phoenix/learning-engine/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp_no_member.status_code == 403

    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()
    resp = client.get("/api/phoenix/learning-engine/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 200


# ── 2. Recommendation generation ──────────────────────────────────────────────

def test_generate_recommendations_from_drift_signal():
    tenant_id = uid("phoenix-rec-drift")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        for i in range(15):
            db.add(SupervisorReview(
                inspection_id=i + 1, tenant_id=tenant_id, agreement="agree", ai_confidence=0.9,
                created_at=now - timedelta(days=45),
            ))
        for i in range(15):
            db.add(SupervisorReview(
                inspection_id=i + 100, tenant_id=tenant_id, agreement="disagree", ai_confidence=0.4,
                created_at=now - timedelta(days=1),
            ))
        db.commit()
        recs = phoenix_recommendation_engine.generate_recommendations(db, tenant_id)
    finally:
        db.close()
    assert any(r["recommendation_type"] == "review_ai_confidence" for r in recs)
    for r in recs:
        assert r["status"] == "draft"
        assert r["evidence"]


def test_recommendation_route_generate_and_list():
    tenant_id = uid("phoenix-rec-route")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="spd_manager")
    finally:
        db.close()
    resp = client.post("/api/phoenix/recommendations/generate", headers=_headers(AUTH_MGR, tenant_id))
    assert resp.status_code == 200
    resp_list = client.get("/api/phoenix/recommendations", headers=_headers(AUTH_MGR, tenant_id))
    assert resp_list.status_code == 200


def test_ai_observatory_summary_composes_real_metrics():
    tenant_id = uid("phoenix-observatory")
    db = SessionLocal()
    try:
        for i in range(5):
            db.add(SupervisorReview(inspection_id=i + 1, tenant_id=tenant_id, agreement="agree", ai_confidence=0.85))
        db.commit()
        result = phoenix_ai_observatory_service.observatory_summary(db, tenant_id)
    finally:
        db.close()
    assert result["sample_size"] == 5
    assert "precision" in result
    assert result["coverage"]["total_inspections"] == 0


def test_latency_sample_recorded_and_summarized():
    tenant_id = uid("phoenix-latency")
    db = SessionLocal()
    try:
        phoenix_ai_observatory_service.record_latency_sample(db, tenant_id, stage="detection", latency_ms=120.5)
        phoenix_ai_observatory_service.record_latency_sample(db, tenant_id, stage="detection", latency_ms=90.0)
        summary = phoenix_ai_observatory_service.latency_summary(db, tenant_id, stage="detection")
    finally:
        db.close()
    assert summary["detection"]["sample_size"] == 2
    assert summary["detection"]["avg_ms"] == 105.25


def test_latency_sample_rejects_invalid_stage():
    tenant_id = uid("phoenix-latency-bad")
    db = SessionLocal()
    try:
        try:
            phoenix_ai_observatory_service.record_latency_sample(db, tenant_id, stage="not_a_stage", latency_ms=1.0)
            assert False, "expected ValueError"
        except ValueError:
            pass
    finally:
        db.close()


# ── 3. Workflow optimization ───────────────────────────────────────────────────

def test_duration_analysis_and_repeated_exceptions():
    tenant_id = uid("phoenix-workflow")
    db = SessionLocal()
    try:
        for _ in range(3):
            db.add(WorkflowExecution(tenant_id=tenant_id, workflow_id=42, status=EXECUTION_FAILED, execution_time_ms=500.0))
        db.add(WorkflowExecution(tenant_id=tenant_id, workflow_id=42, status="completed", execution_time_ms=200.0))
        db.commit()
        duration = phoenix_workflow_optimization_service.duration_analysis(db, tenant_id)
        failures = phoenix_workflow_optimization_service.repeated_exceptions(db, tenant_id)
    finally:
        db.close()
    assert duration["sample_size"] == 4
    assert any(f["workflow_id"] == 42 and f["failure_count"] == 3 for f in failures)


def test_recommend_workflow_optimization_cites_evidence():
    tenant_id = uid("phoenix-workflow-rec")
    db = SessionLocal()
    try:
        for _ in range(2):
            db.add(WorkflowExecution(tenant_id=tenant_id, workflow_id=7, status=EXECUTION_FAILED, execution_time_ms=300.0))
        db.commit()
        result = phoenix_workflow_optimization_service.recommend_workflow_optimization(db, tenant_id, 7)
    finally:
        db.close()
    assert result["recommend_review"] is True
    assert result["evidence"]


def test_rule_complexity_counts_nested_conditions():
    tenant_id = uid("phoenix-rule-complexity")
    db = SessionLocal()
    try:
        from app.services import forge_rule_engine

        forge_rule_engine.create_rule(
            db, tenant_id, name="Test Rule",
            condition={"op": "and", "conditions": [
                {"field": "finding", "operator": "eq", "value": "blood"},
                {"field": "severity", "operator": "eq", "value": "high"},
            ]},
            actions=[{"type": "notify_supervisor"}], author="qa",
        )
        db.commit()
        complexity = phoenix_workflow_optimization_service.rule_complexity(db, tenant_id)
    finally:
        db.close()
    assert len(complexity) >= 1
    assert complexity[0]["complexity_score"] >= 3


def test_competency_intelligence_detects_simulation_and_annual_competency():
    tenant_id = uid("phoenix-competency")
    db = SessionLocal()
    try:
        for _ in range(2):
            db.add(CompetencyEvent(tenant_id=tenant_id, technician="tech1", event_type="simulation_failed", finding_type="blood"))
        db.add(CompetencyEvent(tenant_id=tenant_id, technician="tech2", event_type="knowledge_contribution"))
        db.commit()
        result = phoenix_competency_intelligence_service.run_all_detectors(db, tenant_id)
    finally:
        db.close()
    assert any(o["scope_value"] == "tech1" for o in result["simulation"])
    assert any(o["scope_value"] == "tech2" for o in result["annual_competency"])


# ── 4. Knowledge evolution ─────────────────────────────────────────────────────

def test_contradictory_guidance_detects_conflicting_articles():
    tenant_id = uid("phoenix-knowledge-conflict")
    db = SessionLocal()
    try:
        import json as _json

        db.add(KnowledgeArticle(
            tenant_id=tenant_id, category="best_practice", title="Strict Guidance",
            body="If blood residue is found, remove from service immediately.",
            applicable_findings=_json.dumps(["blood"]), anatomy_zone="box_lock", approval_status="approved",
        ))
        db.add(KnowledgeArticle(
            tenant_id=tenant_id, category="best_practice", title="Lenient Guidance",
            body="Blood residue in this area is generally acceptable; monitor and continue use.",
            applicable_findings=_json.dumps(["blood"]), anatomy_zone="box_lock", approval_status="approved",
        ))
        db.commit()
        conflicts = phoenix_knowledge_evolution_service.contradictory_guidance(db, tenant_id)
    finally:
        db.close()
    assert len(conflicts) == 1
    assert conflicts[0]["finding_type"] == "blood"


def test_knowledge_evolution_summary_composes_athena_curator():
    tenant_id = uid("phoenix-knowledge-summary")
    db = SessionLocal()
    try:
        summary = phoenix_knowledge_evolution_service.knowledge_evolution_summary(db, tenant_id)
    finally:
        db.close()
    for key in ("duplicate_candidates", "outdated_guidance", "retirement_candidates", "emerging_best_practices", "contradictory_guidance"):
        assert key in summary


# ── 5. Platform health ─────────────────────────────────────────────────────────

def test_platform_health_dashboard_reports_insufficient_data_when_empty():
    """A brand-new tenant has no supervisor reviews, knowledge articles,
    workflow executions, memberships, connectors, or quality-twin
    snapshots — all of those areas honestly report "insufficient data".
    The instrument-flow Digital Twin is the one exception: `digital_twin_
    engine` auto-bootstraps default station rows for any tenant on first
    call, so it always has *some* real (data_source="real") signal to
    report, and that's the only input feeding `overall_platform_maturity`
    here — not a fabrication, a real quirk of that pre-existing engine."""
    tenant_id = uid("phoenix-health-empty")
    db = SessionLocal()
    try:
        result = phoenix_platform_health_service.platform_health_dashboard(db, tenant_id)
    finally:
        db.close()
    assert result["ai_health"]["score"] is None
    assert "insufficient data" in result["ai_health"]["note"]
    for area in ("knowledge_health", "workflow_health", "security_health", "integration_health", "quality_health"):
        assert result[area]["score"] is None
    assert result["overall_platform_maturity"] == result["digital_twin_health"]["score"]


def test_security_health_score_reflects_membership_ratio():
    tenant_id = uid("phoenix-health-security")
    db = SessionLocal()
    try:
        db.add(models.TenantMembership(tenant_id=tenant_id, user_email="a@local.dev", role="admin", is_enabled=True))
        db.add(models.TenantMembership(tenant_id=tenant_id, user_email="b@local.dev", role="viewer", is_enabled=False))
        db.commit()
        score = phoenix_platform_health_service.compute_security_health_score(db, tenant_id)
    finally:
        db.close()
    assert score["score"] is not None
    assert score["enabled_membership_ratio"] == 0.5


def test_platform_health_route_requires_membership():
    tenant_id = uid("phoenix-health-route")
    resp_denied = client.get("/api/phoenix/platform-health/dashboard", headers=_headers(AUTH_VIEWER, tenant_id))
    assert resp_denied.status_code == 403

    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()
    resp = client.get("/api/phoenix/platform-health/dashboard", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 200
    assert "overall_platform_maturity" in resp.json()


# ── 6. Innovation tracking ─────────────────────────────────────────────────────

def test_create_and_update_innovation_idea():
    tenant_id = uid("phoenix-innovation")
    db = SessionLocal()
    try:
        idea = phoenix_innovation_pipeline_service.create_idea(
            db, tenant_id, title="Automate loaner tray reminders", estimated_roi_usd=15000.0,
            clinical_impact="medium", technical_complexity="low", priority="high", submitted_by="tech1",
        )
        assert idea["approval_status"] == "draft"

        updated = phoenix_innovation_pipeline_service.update_idea_status(
            db, tenant_id, idea["id"], approval_status="approved", roadmap_assignment="Q4 2026",
        )
        assert updated["approval_status"] == "approved"
        assert updated["roadmap_assignment"] == "Q4 2026"

        summary = phoenix_innovation_pipeline_service.pipeline_summary(db, tenant_id)
        assert summary["total_ideas"] == 1
        assert summary["total_estimated_roi_usd"] == 15000.0
    finally:
        db.close()


def test_create_idea_rejects_invalid_priority():
    tenant_id = uid("phoenix-innovation-bad")
    db = SessionLocal()
    try:
        try:
            phoenix_innovation_pipeline_service.create_idea(db, tenant_id, title="Bad idea", priority="not_a_level")
            assert False, "expected ValueError"
        except ValueError:
            pass
    finally:
        db.close()


def test_innovation_idea_not_found_raises():
    tenant_id = uid("phoenix-innovation-404")
    db = SessionLocal()
    try:
        try:
            phoenix_innovation_pipeline_service.get_idea(db, tenant_id, 999999)
            assert False, "expected InnovationIdeaNotFoundError"
        except phoenix_innovation_pipeline_service.InnovationIdeaNotFoundError:
            pass
    finally:
        db.close()


# ── 7. Maturity scoring ────────────────────────────────────────────────────────

def test_compute_platform_maturity_index_returns_nine_dimensions():
    tenant_id = uid("phoenix-maturity")
    db = SessionLocal()
    try:
        result = phoenix_maturity_index_service.compute_platform_maturity_index(db, tenant_id)
    finally:
        db.close()
    for key in (
        "inspection_score", "knowledge_score", "quality_score", "workflow_score", "analytics_score",
        "education_score", "digital_twins_score", "governance_score", "executive_intelligence_score",
    ):
        assert key in result["scores"]
    assert 0 <= result["overall_score"] <= 100


def test_maturity_history_tracks_progression():
    tenant_id = uid("phoenix-maturity-history")
    db = SessionLocal()
    try:
        phoenix_maturity_index_service.compute_platform_maturity_index(db, tenant_id)
        phoenix_maturity_index_service.compute_platform_maturity_index(db, tenant_id)
        history = phoenix_maturity_index_service.maturity_history(db, tenant_id)
    finally:
        db.close()
    assert len(history) == 2


def test_maturity_route():
    tenant_id = uid("phoenix-maturity-route")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()
    resp = client.post("/api/phoenix/maturity/compute", headers=_headers(AUTH_ADMIN, tenant_id))
    assert resp.status_code == 200
    resp_history = client.get("/api/phoenix/maturity/history", headers=_headers(AUTH_ADMIN, tenant_id))
    assert len(resp_history.json()["history"]) == 1


# ── Continuous Validation (Section 9, supporting Recommendation coverage) ─────

def test_validation_pipeline_advances_through_stages_and_rejects():
    tenant_id = uid("phoenix-validation")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()

    db = SessionLocal()
    try:
        from app.models.phoenix_intelligence import ImprovementRecommendation

        row = ImprovementRecommendation(tenant_id=tenant_id, recommendation_type="update_sop", source="knowledge_evolution", title="Test rec")
        db.add(row)
        db.commit()
        db.refresh(row)
        rec_id = row.id
    finally:
        db.close()

    start_resp = client.post(f"/api/phoenix/recommendations/{rec_id}/validation/start", headers=_headers(AUTH_ADMIN, tenant_id))
    assert start_resp.status_code == 200

    advance_resp = client.post(
        f"/api/phoenix/recommendations/{rec_id}/validation/advance",
        json={"decided_role": "review", "decision": "approved"}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert advance_resp.status_code == 200
    assert advance_resp.json()["recommendation_status"] == "clinical_validation"

    reject_resp = client.post(
        f"/api/phoenix/recommendations/{rec_id}/validation/advance",
        json={"decided_role": "clinical_validation", "decision": "rejected", "outcome_notes": "Not clinically sound."},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["recommendation_status"] == "rejected"

    status_resp = client.get(f"/api/phoenix/recommendations/{rec_id}/validation", headers=_headers(AUTH_ADMIN, tenant_id))
    assert status_resp.status_code == 200
    assert len(status_resp.json()["outcomes"]) == 2
