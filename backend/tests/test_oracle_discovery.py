"""Project Oracle: Clinical Intelligence Scientist & Discovery Engine tests.

Covers the validation-pipeline invariants ("Oracle may not bypass any
stage"), the composition points with Sentinel-X/Apollo/Vulcan/GovernanceApproval,
and a route smoke test. See `app/models/oracle_discovery.py` for the naming
disambiguation from Horizon's network-wide trend detection and the
pre-existing customer/product "pilot" namespace.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.oracle_discovery import (
    CONFIDENCE_EXPLORATORY,
    OUTCOME_INCONCLUSIVE,
    OUTCOME_PROMOTED,
    STAGE_OBSERVATION,
    STAGE_PRODUCTION_KNOWLEDGE,
    STAGE_REJECTED,
)
from app.services import (
    oracle_collaboration_service,
    oracle_digital_twin_research_service,
    oracle_hypothesis_service,
    oracle_innovation_dashboard_service,
    oracle_knowledge_evolution_service,
    oracle_model_observatory_service,
    oracle_registry_service,
    oracle_trend_detection_service,
    oracle_validation_pipeline_service,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    db.add(models.TenantMembership(tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True))
    db.commit()


def _mk_inspection(db, tenant_id, *, created_at, coverage_pct=None, coverage_quality=None):
    row = models.Inspection(
        tenant_id=tenant_id, file_name="t.jpg", instrument_type="kerrison rongeur", created_at=created_at,
        coverage_pct=coverage_pct, coverage_quality=coverage_quality,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mk_finding(db, tenant_id, inspection_id, *, finding_type="corrosion", severity_index=2):
    from app.models.inspection_finding import InspectionFinding
    row = InspectionFinding(
        tenant_id=tenant_id, inspection_id=inspection_id, finding_type=finding_type, severity_index=severity_index,
    )
    db.add(row)
    db.commit()
    return row


def _advance_n(db, tenant_id, hypothesis_id, n, *, role="spd_manager", notes="reviewed"):
    row = None
    for _ in range(n):
        row = oracle_validation_pipeline_service.advance_stage(
            db, tenant_id, hypothesis_id, changed_by="mgr@local.dev", changed_by_role=role, gate_check_notes=notes,
        )
    return row


# ── 1. A new hypothesis starts at OBSERVATION with exploratory confidence ────

def test_hypothesis_starts_at_observation_with_exploratory_confidence():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        hyp = oracle_hypothesis_service.create_hypothesis(
            db, tenant_id, discovery_category="process_pattern", title="T1",
            changed_by="a@local.dev", changed_by_role="operator",
        )
        assert hyp.current_stage == STAGE_OBSERVATION
        assert hyp.confidence_level == CONFIDENCE_EXPLORATORY
        assert hyp.hypothesis_code == f"ORC-{hyp.id:05d}"
        history = oracle_validation_pipeline_service.stage_history(db, tenant_id, hyp.id)
        assert len(history) == 1 and history[0]["to_stage"] == STAGE_OBSERVATION
    finally:
        db.close()


# ── 2. Advancing the pipeline moves exactly one stage at a time ─────────────

def test_advance_stage_moves_one_step_at_a_time():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        hyp = oracle_hypothesis_service.create_hypothesis(db, tenant_id, discovery_category="process_pattern", title="T2", changed_by="a", changed_by_role="operator")
        hyp = oracle_validation_pipeline_service.advance_stage(db, tenant_id, hyp.id, changed_by="a", changed_by_role="operator")
        assert hyp.current_stage == "HYPOTHESIS"
        hyp = oracle_validation_pipeline_service.advance_stage(db, tenant_id, hyp.id, changed_by="a", changed_by_role="operator")
        assert hyp.current_stage == "EVIDENCE_REVIEW"
    finally:
        db.close()


# ── 3. Promotion to PRODUCTION_KNOWLEDGE requires leadership tier + gate notes ─

def test_promotion_to_production_knowledge_requires_leadership_tier_and_notes():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        hyp = oracle_hypothesis_service.create_hypothesis(db, tenant_id, discovery_category="process_pattern", title="T3", changed_by="a", changed_by_role="operator")
        hyp = _advance_n(db, tenant_id, hyp.id, 6, role="operator")
        assert hyp.current_stage == "GOVERNANCE_APPROVAL"

        with pytest.raises(ValueError):
            oracle_validation_pipeline_service.advance_stage(db, tenant_id, hyp.id, changed_by="a", changed_by_role="operator", gate_check_notes="x")
        with pytest.raises(ValueError):
            oracle_validation_pipeline_service.advance_stage(db, tenant_id, hyp.id, changed_by="mgr", changed_by_role="spd_manager")

        hyp = oracle_validation_pipeline_service.advance_stage(db, tenant_id, hyp.id, changed_by="mgr", changed_by_role="spd_manager", gate_check_notes="Reviewed evidence and clinical sign-off.")
        assert hyp.current_stage == STAGE_PRODUCTION_KNOWLEDGE
        assert hyp.outcome == OUTCOME_PROMOTED
    finally:
        db.close()


# ── 4. Close-out is reachable from any non-terminal stage ───────────────────

def test_close_out_reachable_from_any_non_terminal_stage():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        hyp = oracle_hypothesis_service.create_hypothesis(db, tenant_id, discovery_category="process_pattern", title="T4", changed_by="a", changed_by_role="operator")
        closed = oracle_validation_pipeline_service.close_out_hypothesis(
            db, tenant_id, hyp.id, outcome=OUTCOME_INCONCLUSIVE, changed_by="a", changed_by_role="operator", reason="Not enough data yet.",
        )
        assert closed.current_stage == STAGE_REJECTED
        assert closed.outcome == OUTCOME_INCONCLUSIVE
        assert closed.rejected_reason == "Not enough data yet."
    finally:
        db.close()


# ── 5. A terminal-stage hypothesis cannot advance or close again ────────────

def test_terminal_hypothesis_cannot_advance_or_close_again():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        hyp = oracle_hypothesis_service.create_hypothesis(db, tenant_id, discovery_category="process_pattern", title="T5", changed_by="a", changed_by_role="operator")
        hyp = _advance_n(db, tenant_id, hyp.id, 7, role="spd_manager")
        assert hyp.current_stage == STAGE_PRODUCTION_KNOWLEDGE
        with pytest.raises(ValueError):
            oracle_validation_pipeline_service.advance_stage(db, tenant_id, hyp.id, changed_by="a", changed_by_role="spd_manager")
        with pytest.raises(ValueError):
            oracle_validation_pipeline_service.close_out_hypothesis(db, tenant_id, hyp.id, outcome=OUTCOME_INCONCLUSIVE, changed_by="a", changed_by_role="operator", reason="x")
    finally:
        db.close()


# ── 6. Trend detection promotes into a linked, association-only hypothesis ──

def test_trend_detection_promotes_into_linked_hypothesis():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        insp = _mk_inspection(db, tenant_id, created_at=now - timedelta(days=5))
        _mk_finding(db, tenant_id, insp.id)
        _mk_finding(db, tenant_id, insp.id)

        trend = oracle_trend_detection_service.detect_finding_rate_trend(db, tenant_id, trend_category="emerging_risk_signal", metric_name="corrosion_findings")
        assert trend.direction == "increasing"

        hyp = oracle_trend_detection_service.promote_to_hypothesis(db, tenant_id, trend.id, title="Rising corrosion findings", changed_by="a", changed_by_role="operator")
        assert hyp.discovery_category == "emerging_risk_signal"
        assert "possible association" in hyp.hypothesis_statement or "potential association" in hyp.hypothesis_statement

        with pytest.raises(ValueError):
            oracle_trend_detection_service.promote_to_hypothesis(db, tenant_id, trend.id, title="Again", changed_by="a", changed_by_role="operator")
    finally:
        db.close()


# ── 7. Digital twin research composes Vulcan's progression, never re-derives it ─

def test_digital_twin_research_composes_vulcan_progression():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        insight = oracle_digital_twin_research_service.record_vulcan_insight(db, tenant_id, "barcode:NOHISTORY")
        assert insight.source_service == "vulcan_progression"
        assert "Insufficient" in insight.insight_summary

        hyp = oracle_digital_twin_research_service.promote_to_hypothesis(
            db, tenant_id, insight.id, discovery_category="digital_twin_divergence", title="From twin", changed_by="a", changed_by_role="operator",
        )
        assert oracle_hypothesis_service.to_dict(hyp)["digital_twin_refs"] == [insight.id]
    finally:
        db.close()


# ── 8. Model observatory flags a coverage gap from Sentinel-X's own data ────

def test_model_observatory_flags_coverage_gap_from_low_coverage_data():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        for _ in range(4):
            _mk_inspection(db, tenant_id, created_at=now, coverage_pct=40, coverage_quality="poor")

        obs = oracle_model_observatory_service.record_observation(db, tenant_id)
        assert obs.observation_type == "coverage_gap"

        hyp = oracle_model_observatory_service.promote_to_hypothesis(db, tenant_id, obs.id, title="Low coverage quality", changed_by="a", changed_by_role="operator")
        assert hyp.discovery_category == "ai_model_performance_drift"
    finally:
        db.close()


# ── 9. Knowledge suggestions require leadership approval and route through governance ─

def test_knowledge_suggestion_requires_leadership_and_creates_pending_review_article():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        hyp = oracle_hypothesis_service.create_hypothesis(db, tenant_id, discovery_category="process_pattern", title="T9", changed_by="a", changed_by_role="operator")
        sugg = oracle_knowledge_evolution_service.create_suggestion(
            db, tenant_id, "Test Tenant", hypothesis_id=hyp.id, suggested_article_title="New teaching point",
            suggested_article_body="Body text.", rationale="Observed pattern.", submitted_by="a@local.dev",
        )
        assert sugg.governance_approval_id is not None

        with pytest.raises(ValueError):
            oracle_knowledge_evolution_service.approve_suggestion(db, tenant_id, sugg.id, reviewer="a", reviewer_role="operator", article_category="lesson_learned")

        approved = oracle_knowledge_evolution_service.approve_suggestion(db, tenant_id, sugg.id, reviewer="mgr", reviewer_role="spd_manager", article_category="lesson_learned")
        assert approved.status == "approved"
        article = db.query(models.KnowledgeArticle).filter(models.KnowledgeArticle.id == approved.knowledge_article_id).first()
        assert article is not None and article.approval_status == "pending_review"

        approval = db.query(models.GovernanceApproval).filter(models.GovernanceApproval.id == sugg.governance_approval_id).first()
        assert approval.status == "approved"
    finally:
        db.close()


# ── 10. Registry and dashboard rollups reflect a promoted hypothesis ────────

def test_registry_and_dashboard_reflect_promoted_hypothesis():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        hyp = oracle_hypothesis_service.create_hypothesis(db, tenant_id, discovery_category="process_pattern", title="T10", changed_by="a", changed_by_role="operator")
        oracle_collaboration_service.reassign_research_owner(db, tenant_id, hyp.id, new_owner="researcher@local.dev", changed_by="a", changed_by_role="operator")
        _advance_n(db, tenant_id, hyp.id, 7, role="spd_manager")

        summary = oracle_registry_service.registry_summary(db, tenant_id)
        assert summary["by_outcome"][OUTCOME_PROMOTED] >= 1

        dashboard = oracle_innovation_dashboard_service.innovation_dashboard(db, tenant_id)
        assert dashboard["promoted_to_production_count"] >= 1
        assert dashboard["avg_time_to_validation_days"] is not None
        assert dashboard["top_research_owners"][0]["research_owner"] == "researcher@local.dev"
    finally:
        db.close()


# ── Route smoke test ──────────────────────────────────────────────────────

def test_oracle_route_smoke():
    tenant_id = uid("oracle-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()

    payload = {"discovery_category": "process_pattern", "title": "Smoke test hypothesis", "observation_summary": "obs"}
    r1 = client.post("/api/oracle/hypotheses", json=payload, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r1.status_code == 201, r1.text
    hyp_id = r1.json()["id"]

    r2 = client.get(f"/api/oracle/hypotheses/{hyp_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["hypothesis"]["id"] == hyp_id

    r3 = client.get("/api/oracle/workspace", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200

    r4 = client.get("/api/oracle/registry/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200

    r5 = client.get("/api/oracle/dashboard", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r5.status_code == 200

    r6 = client.post(f"/api/oracle/hypotheses/{hyp_id}/advance", json={}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r6.status_code == 200
    assert r6.json()["current_stage"] == "HYPOTHESIS"
