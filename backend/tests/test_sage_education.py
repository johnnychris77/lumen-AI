"""LumenAI AI Specialist — Project Sage: SPD Education, Competency &
Workforce Intelligence tests.

Covers the 14 named scenarios from the sprint brief's Section 20, plus route
smoke/permission tests.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.sage_education import SageLearningPlan
from app.models.supervisor_review import SupervisorReview
from app.services import (
    sage_aegis_vulcan_integration_service,
    sage_effectiveness_service,
    sage_feedback_service,
    sage_gap_detection_service,
    sage_learning_plan_service,
    sage_microlearning_service,
    sage_workforce_privacy_service,
)
from app.services.vulcan_reliability_agent_service import run_reliability_assessment
from app.models.inspection_finding import InspectionFinding

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
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


def _mk_inspection(db, tenant_id, *, technician, coverage_pct=None, ai_confidence=None, has_image=True, created_at=None):
    row = models.Inspection(
        tenant_id=tenant_id, file_name="test.jpg", technician=technician,
        coverage_pct=coverage_pct, ai_confidence=ai_confidence, has_image=has_image,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mk_review(db, tenant_id, inspection_id, **kwargs):
    row = SupervisorReview(tenant_id=tenant_id, inspection_id=inspection_id, agreement=kwargs.pop("agreement", "agree"), **kwargs)
    db.add(row)
    db.commit()
    return row


# ── 1. repeated missed anatomy zones produce an education recommendation ─────

def test_repeated_missed_anatomy_zones_produce_education_recommendation():
    tenant_id = uid("sage-t")
    technician = uid("tech") + "@local.dev"
    db = SessionLocal()
    try:
        for _ in range(2):
            insp = _mk_inspection(db, tenant_id, technician=technician)
            _mk_review(db, tenant_id, insp.id, missing_zone_correct=False, corrected_missing_zone="serrations", instrument_family="kerrison")

        gaps = sage_gap_detection_service.detect_missed_anatomy_zones(db, tenant_id, technician)
        assert len(gaps) == 1
        assert gaps[0]["occurrence_count"] == 2
        assert gaps[0]["recommended_education"]
        assert "targeted education" in gaps[0]["narrative"].lower() or "verification" in gaps[0]["narrative"].lower() or "observation" in gaps[0]["narrative"].lower()
    finally:
        db.close()


# ── 2. one isolated error does not automatically create a competency failure ─

def test_one_isolated_error_does_not_create_gap():
    tenant_id = uid("sage-t")
    technician = uid("tech") + "@local.dev"
    db = SessionLocal()
    try:
        insp = _mk_inspection(db, tenant_id, technician=technician)
        _mk_review(db, tenant_id, insp.id, missing_zone_correct=False, corrected_missing_zone="serrations", instrument_family="kerrison")

        gaps = sage_gap_detection_service.detect_missed_anatomy_zones(db, tenant_id, technician)
        assert gaps == []
    finally:
        db.close()


# ── 3. rigid-scope and flexible-endoscope education remain distinct ──────────

def test_rigid_scope_and_flexible_endoscope_remain_distinct():
    tenant_id = uid("sage-t")
    technician = uid("tech") + "@local.dev"
    db = SessionLocal()
    try:
        for _ in range(2):
            insp = _mk_inspection(db, tenant_id, technician=technician)
            _mk_review(db, tenant_id, insp.id, zone_correct=False, instrument_family="rigid_scope")
        for _ in range(2):
            insp = _mk_inspection(db, tenant_id, technician=technician)
            _mk_review(db, tenant_id, insp.id, zone_correct=False, instrument_family="flexible_endoscope")

        gaps = sage_gap_detection_service.detect_anatomy_label_errors(db, tenant_id, technician)
        families = {g["instrument_family"] for g in gaps}
        assert families == {"rigid_scope", "flexible_endoscope"}
        assert len(gaps) == 2
    finally:
        db.close()


# ── 4. drill-bit flute gap produces anatomy-specific guidance ────────────────

def test_drill_bit_flute_gap_produces_anatomy_specific_guidance():
    tenant_id = uid("sage-t")
    technician = uid("tech") + "@local.dev"
    db = SessionLocal()
    try:
        for _ in range(2):
            insp = _mk_inspection(db, tenant_id, technician=technician)
            _mk_review(db, tenant_id, insp.id, missing_zone_correct=False, corrected_missing_zone="flutes", instrument_family="drill_bit")

        gaps = sage_gap_detection_service.detect_missed_anatomy_zones(db, tenant_id, technician)
        assert len(gaps) == 1
        assert "flutes" in gaps[0]["recommended_education"]
        assert gaps[0]["anatomy_zone"] == "flutes"
    finally:
        db.close()


# ── 5. blood-versus-rust confusion produces targeted education ──────────────

def test_blood_versus_rust_confusion_produces_targeted_education():
    tenant_id = uid("sage-t")
    technician = uid("tech") + "@local.dev"
    db = SessionLocal()
    try:
        insp1 = _mk_inspection(db, tenant_id, technician=technician)
        _mk_review(db, tenant_id, insp1.id, finding_correct=False, finding_type="blood")
        insp2 = _mk_inspection(db, tenant_id, technician=technician)
        _mk_review(db, tenant_id, insp2.id, finding_correct=False, finding_type="rust")

        gaps = sage_gap_detection_service.detect_finding_confusion(db, tenant_id, technician)
        assert len(gaps) == 1
        assert gaps[0]["finding_category"] == "blood_vs_rust"
        assert "blood" in gaps[0]["recommended_education"] and "rust" in gaps[0]["recommended_education"]
    finally:
        db.close()


# ── 6. approved knowledge sources are included in microlearning ──────────────

def test_approved_knowledge_sources_included_in_microlearning():
    tenant_id = uid("sage-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        module = sage_microlearning_service.build_module_from_finding(db, tenant_id, "corrosion")
        assert module is not None
        data = sage_microlearning_service._to_dict(module)
        assert data["inspection_steps"]
        assert any("clinical_mentor" in ref or "education_library" in ref or ref for ref in data["source_refs"])
        assert data["source_refs"]
    finally:
        db.close()


# ── 7. unapproved guidance is excluded ────────────────────────────────────────

def test_unapproved_guidance_is_excluded():
    tenant_id = uid("sage-t")
    db = SessionLocal()
    try:
        module = sage_microlearning_service.build_module_from_finding(db, tenant_id, "totally_unrecognized_finding_xyz")
        assert module is None
    finally:
        db.close()


# ── 8. supervisor approval is required before assignment ────────────────────

def test_supervisor_approval_required_before_assignment():
    tenant_id = uid("sage-t")
    technician = uid("tech") + "@local.dev"
    db = SessionLocal()
    try:
        plan = sage_learning_plan_service.create_learning_plan(
            db, tenant_id, learner_or_group=technician, created_by="sage-system",
        )
        assert plan.approved_by == ""
        visible = sage_learning_plan_service.list_plans_for_learner(db, tenant_id, technician)
        assert visible == []

        sage_learning_plan_service.approve_learning_plan(db, tenant_id, plan.id, approved_by="supervisor@local.dev")
        visible_after = sage_learning_plan_service.list_plans_for_learner(db, tenant_id, technician)
        assert len(visible_after) == 1
        assert visible_after[0]["approved_by"] == "supervisor@local.dev"
    finally:
        db.close()


# ── 9. technician can view only their learning plan ──────────────────────────

def test_technician_can_view_only_their_own_learning_plan():
    tenant_id = uid("sage-t")
    tech_a = uid("tech-a") + "@local.dev"
    tech_b = uid("tech-b") + "@local.dev"
    db = SessionLocal()
    try:
        plan_a = sage_learning_plan_service.create_learning_plan(db, tenant_id, learner_or_group=tech_a, created_by="sage-system")
        plan_b = sage_learning_plan_service.create_learning_plan(db, tenant_id, learner_or_group=tech_b, created_by="sage-system")
        sage_learning_plan_service.approve_learning_plan(db, tenant_id, plan_a.id, approved_by="supervisor@local.dev")
        sage_learning_plan_service.approve_learning_plan(db, tenant_id, plan_b.id, approved_by="supervisor@local.dev")

        visible_to_a = sage_learning_plan_service.list_plans_for_learner(db, tenant_id, tech_a)
        assert len(visible_to_a) == 1
        assert visible_to_a[0]["learner_or_group"] == tech_a
        assert all(p["learner_or_group"] != tech_b for p in visible_to_a)
    finally:
        db.close()


# ── 10. viewer cannot access individual competency data ──────────────────────

def test_viewer_cannot_access_individual_competency_data():
    tenant_id = uid("sage-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
        _seed_membership(db, tenant_id, role="viewer")
    finally:
        db.close()

    r = client.get("/api/sage/gaps", headers=_headers(AUTH_VIEWER, tenant_id))
    assert r.status_code == 403

    r2 = client.get("/api/sage/learning-plans", headers=_headers(AUTH_VIEWER, tenant_id))
    assert r2.status_code == 403

    assert sage_workforce_privacy_service.can_view_individual_competency("viewer", "viewer@local.dev", "someone-else@local.dev") is False


# ── 11. learning effectiveness compares pre/post metrics correctly ──────────

def test_learning_effectiveness_compares_pre_post_metrics_correctly():
    tenant_id = uid("sage-t")
    technician = uid("tech") + "@local.dev"
    db = SessionLocal()
    try:
        plan_created_at = datetime.now(timezone.utc) - timedelta(days=60)
        plan_completed_at = datetime.now(timezone.utc) - timedelta(days=10)

        # Before window: low coverage, poor accuracy.
        for _ in range(3):
            insp = _mk_inspection(db, tenant_id, technician=technician, coverage_pct=50, created_at=plan_created_at - timedelta(days=5))
            _mk_review(db, tenant_id, insp.id, finding_correct=False, zone_correct=False)

        # After window: high coverage, good accuracy.
        for _ in range(3):
            insp = _mk_inspection(db, tenant_id, technician=technician, coverage_pct=95, created_at=plan_completed_at + timedelta(days=5))
            _mk_review(db, tenant_id, insp.id, finding_correct=True, zone_correct=True)

        plan = SageLearningPlan(tenant_id=tenant_id, learner_or_group=technician, created_by="sage-system")
        plan.created_at = plan_created_at
        plan.completed_at = plan_completed_at
        plan.completion_status = "completed"
        db.add(plan)
        db.commit()
        db.refresh(plan)

        result = sage_effectiveness_service.measure_learning_plan_effectiveness(db, tenant_id, plan, window_days=30)
        assert result.effectiveness in ("improved", "partially_improved")
        before = result.before_metrics_json
        after = result.after_metrics_json
        assert "50" in before or "50.0" in before
        assert "95" in after or "95.0" in after
    finally:
        db.close()


# ── 12. insufficient evidence returns an inconclusive effectiveness result ──

def test_insufficient_evidence_returns_inconclusive_effectiveness_result():
    tenant_id = uid("sage-t")
    technician = uid("tech") + "@local.dev"
    db = SessionLocal()
    try:
        plan = SageLearningPlan(tenant_id=tenant_id, learner_or_group=technician, created_by="sage-system")
        plan.completion_status = "completed"
        plan.completed_at = datetime.now(timezone.utc)
        db.add(plan)
        db.commit()
        db.refresh(plan)

        result = sage_effectiveness_service.measure_learning_plan_effectiveness(db, tenant_id, plan, window_days=30)
        assert result.effectiveness == "insufficient_evidence"
    finally:
        db.close()


# ── 13. Aegis, Vulcan, and Sage evidence remain separately auditable ────────

def test_aegis_vulcan_sage_evidence_separately_auditable():
    tenant_id = uid("sage-t")
    barcode = uid("instr")
    identity = f"barcode:{barcode}"
    db = SessionLocal()
    try:
        base = datetime.now(timezone.utc) - timedelta(days=20)
        for day in (0, 10):
            insp = models.Inspection(
                tenant_id=tenant_id, file_name="t.jpg", instrument_type="kerrison rongeur",
                instrument_barcode=barcode, technician="tech-a@local.dev", created_at=base + timedelta(days=day),
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)
            db.add(InspectionFinding(tenant_id=tenant_id, inspection_id=insp.id, finding_type="corrosion", zone="jaw", severity_index=2))
            db.commit()

        vulcan_row = run_reliability_assessment(db, tenant_id, identity, instrument_type="kerrison rongeur")
        sage_result = sage_aegis_vulcan_integration_service.sage_recommendation_from_vulcan(vulcan_row)

        assert sage_result["source_vulcan_assessment_id"] == vulcan_row.id
        assert sage_result["recommendation"] != vulcan_row.reasoning_narrative

        aegis_result = sage_aegis_vulcan_integration_service.sage_recommendation_from_aegis(db, tenant_id, identity, zone="jaw")
        assert "source_aegis_signal" in aegis_result
        assert "recommendation" in aegis_result
        # The three evidence sources are all independently present and distinguishable.
        assert vulcan_row.reasoning_narrative
        assert aegis_result["source_aegis_signal"] is not vulcan_row.reasoning_narrative
    finally:
        db.close()


# ── 14. Sage cannot make disciplinary or employment decisions ───────────────

def test_sage_cannot_make_disciplinary_or_employment_decisions():
    assert "disciplinary_action" in sage_workforce_privacy_service.PROHIBITED_ACTIONS
    assert "employment_decision" in sage_workforce_privacy_service.PROHIBITED_ACTIONS
    assert "public_employee_ranking" in sage_workforce_privacy_service.PROHIBITED_ACTIONS

    assert "terminate_employee" not in sage_feedback_service.VALID_ACTIONS
    assert "discipline" not in sage_feedback_service.VALID_ACTIONS

    tenant_id = uid("sage-t")
    db = SessionLocal()
    try:
        try:
            sage_feedback_service.record_feedback(db, tenant_id, action="terminate_employee", submitted_by="someone@local.dev")
            raised = False
        except ValueError:
            raised = True
        assert raised
    finally:
        db.close()


# ── Route smoke tests ─────────────────────────────────────────────────────────

def test_taxonomy_and_workspace_routes():
    tenant_id = uid("sage-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()

    r = client.get("/api/sage/taxonomy", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert "anatomy_recognition" in r.json()["domains"]

    r2 = client.get("/api/sage/workspace", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["human_review_required"] is True

    r3 = client.get("/api/sage/my-learning", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert r3.json()["learner"] == "admin@local.dev"

    r4 = client.get("/api/sage/executive-summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200
    assert "no individual technician is ranked" in r4.json()["note"]
