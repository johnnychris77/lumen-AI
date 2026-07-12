"""LumenAI AI Leadership Platform — Project Steward: Governed Action
Execution, Change Management & Benefits Realization tests.

Covers the 20 named scenarios from the sprint brief's Section 29, plus a
route smoke test. Steward is a governed execution layer over decisions
already approved elsewhere -- see `app/models/governed_action.py` for the
naming disambiguation from the pre-existing CAPA and customer/product
"pilot" domains.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.governed_action import (
    BENEFITS_ACHIEVED,
    BENEFITS_EXCEEDED,
    BENEFITS_INCONCLUSIVE,
    BENEFITS_PARTIALLY_ACHIEVED,
    CATEGORY_OPERATIONAL,
    CATEGORY_RELIABILITY,
    SOURCE_LEADERSHIP_DIRECTIVE,
    STATUS_AT_RISK,
    STATUS_BLOCKED,
    STATUS_CLOSED,
    STATUS_DRAFT,
)
from app.models.sage_education import SageLearningPlan
from app.services import (
    steward_action_service,
    steward_benefits_realization_service,
    steward_closure_service,
    steward_council_integration_service,
    steward_escalation_service,
    steward_residual_risk_service,
    steward_specialist_integration_service,
    steward_unintended_consequence_service,
    steward_verification_service,
)
from app.services.council_human_decision_service import finalize_decision
from app.services.council_orchestration_service import open_case

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


def _approved_action_kwargs(**overrides) -> dict:
    base = dict(
        source_type=SOURCE_LEADERSHIP_DIRECTIVE, source_id="ld-1", source_decision="Reduce recurring corrosion findings.",
        approved_by="director@local.dev", approval_timestamp=datetime.now(timezone.utc),
        action_title="Increase inspection frequency for kerrison rongeurs",
        category=CATEGORY_RELIABILITY, action_type="increased_inspection_frequency", risk_level="medium",
    )
    base.update(overrides)
    return base


def _mk_inspection(db, tenant_id, *, barcode, instrument_type="kerrison rongeur"):
    row = models.Inspection(
        tenant_id=tenant_id, file_name="t.jpg", instrument_type=instrument_type, instrument_barcode=barcode,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── 1. Approved Council decision creates draft action ─────────────────────

def test_approved_council_decision_creates_draft_action():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        case = open_case(db, tenant_id, case_type="recurring_instrument_failure", source_event="Recurring corrosion", risk_level="high", urgency="urgent")
        finalize_decision(db, tenant_id, case.id, approver="director@local.dev", approver_role="admin", decision="Increase inspection frequency and retrain staff.")
        action = steward_council_integration_service.create_action_from_council_decision(
            db, tenant_id, case.id, category=CATEGORY_RELIABILITY, action_type="increased_inspection_frequency",
            action_title="Increase inspection frequency",
        )
        assert action.status == STATUS_DRAFT
        assert action.source_type == "council_case"
        assert action.source_decision == "Increase inspection frequency and retrain staff."
    finally:
        db.close()


# ── 2. Unapproved recommendation cannot activate an action ────────────────

def test_unapproved_recommendation_cannot_activate_action():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        with pytest.raises(ValueError):
            steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs(approved_by="", approval_timestamp=None))
    finally:
        db.close()


# ── 3. Action requires owner and accountable leader ───────────────────────

def test_action_requires_owner_and_accountable_leader():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        with pytest.raises(ValueError):
            steward_action_service.transition_status(db, tenant_id, action.id, new_status="READY_TO_START", changed_by="a", changed_by_role="spd_manager")
        steward_action_service.assign_owner(db, tenant_id, action.id, owner="tech@local.dev", accountable_leader="mgr@local.dev", changed_by="a", changed_by_role="spd_manager")
        action = steward_action_service.transition_status(db, tenant_id, action.id, new_status="READY_TO_START", changed_by="a", changed_by_role="spd_manager")
        assert action.status == "READY_TO_START"
    finally:
        db.close()


# ── 4. High-risk action requires implementation evidence ──────────────────

def test_high_risk_action_requires_implementation_evidence():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs(risk_level="high"))
        steward_action_service.assign_owner(db, tenant_id, action.id, owner="tech@local.dev", accountable_leader="mgr@local.dev", changed_by="a", changed_by_role="spd_manager")
        with pytest.raises(ValueError):
            steward_closure_service.close_action(db, tenant_id, action.id, closure_decision="close_and_sustain", closed_by="mgr@local.dev", closed_by_role="spd_manager", owner_comments="Done.")
    finally:
        db.close()


# ── 5. Blocked dependency changes action status ───────────────────────────

def test_blocked_dependency_changes_action_status():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        action = steward_action_service.transition_status(db, tenant_id, action.id, new_status=STATUS_BLOCKED, changed_by="a", changed_by_role="operator", reason="Awaiting parts.")
        assert action.status == STATUS_BLOCKED
    finally:
        db.close()


# ── 6. Overdue critical action escalates ──────────────────────────────────

def test_overdue_critical_action_escalates():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(
            db, tenant_id, **_approved_action_kwargs(risk_level="critical", due_date=datetime.now(timezone.utc) - timedelta(days=2)),
        )
        escalations = steward_escalation_service.evaluate_escalations(db, tenant_id)
        matching = [e for e in escalations if e["governed_action_id"] == action.id and e["rule"] == "critical_action_overdue"]
        assert matching
        assert matching[0]["next_accountable_role"] == "admin"
    finally:
        db.close()


# ── 7. Supervisor (manager-tier) can approve only within configured scope ─

def test_manager_tier_approver_scope_limited_to_own_facility():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs(facility_id="facility-A"))
        with pytest.raises(ValueError):
            steward_action_service.transition_status(
                db, tenant_id, action.id, new_status="APPROVED", changed_by="mgr@local.dev", changed_by_role="spd_manager",
                actor_facility_id="facility-B",
            )
        action = steward_action_service.transition_status(
            db, tenant_id, action.id, new_status="APPROVED", changed_by="mgr@local.dev", changed_by_role="spd_manager",
            actor_facility_id="facility-A",
        )
        assert action.status == "APPROVED"
    finally:
        db.close()


# ── 8. Technician cannot close high-risk action ───────────────────────────

def test_technician_cannot_close_high_risk_action():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs(risk_level="critical"))
        with pytest.raises(ValueError):
            steward_action_service.transition_status(db, tenant_id, action.id, new_status=STATUS_CLOSED, changed_by="tech@local.dev", changed_by_role="operator")
    finally:
        db.close()


# ── 9. Veritas evidence limitation prevents unsupported closure ──────────

def test_veritas_evidence_limitation_prevents_unsupported_closure():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs(risk_level="high"))
        steward_action_service.assign_owner(db, tenant_id, action.id, owner="tech@local.dev", accountable_leader="mgr@local.dev", changed_by="a", changed_by_role="spd_manager")
        insp = _mk_inspection(db, tenant_id, barcode=uid("BC"))
        row = steward_verification_service.record_verification(
            db, tenant_id, action.id, evidence_type="inspection_evidence", verified_by="mgr@local.dev",
            sufficient=True, inspection_id=insp.id,
        )
        assert row.sufficient is False
        assert row.insufficiency_reason
        with pytest.raises(ValueError):
            steward_closure_service.close_action(db, tenant_id, action.id, closure_decision="close_and_sustain", closed_by="mgr@local.dev", closed_by_role="spd_manager", owner_comments="Done.")
    finally:
        db.close()


# ── 10. Sentinel-X residual-risk review is stored ─────────────────────────

def test_sentinelx_residual_risk_review_is_stored():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs(risk_level="high"))
        steward_residual_risk_service.record_residual_risk_review(
            db, tenant_id, action.id, risk_before=80.0, risk_during=60.0, risk_after=40.0, reviewed_by="mgr@local.dev", notes="Improved.",
        )
        assert steward_residual_risk_service.has_reviewed_residual_risk(db, tenant_id, action.id)
        rows = steward_residual_risk_service.list_residual_risk_reviews(db, tenant_id, action.id)
        assert rows[0]["risk_before"] == 80.0 and rows[0]["risk_after"] == 40.0
    finally:
        db.close()


# ── 11. Aegis process outcome remains separately traceable ───────────────

def test_aegis_process_outcome_remains_separately_traceable():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs(category=CATEGORY_OPERATIONAL, action_type="workflow_redesign"))
        result = steward_specialist_integration_service.get_aegis_process_outcome(db, tenant_id, "barcode:AEGIS-1")
        assert "process_variation_detected" in result
        # Confirms Aegis's finding is never merged into Steward's own outcome-review ledger.
        assert steward_benefits_realization_service.list_outcome_reviews(db, tenant_id, action.id) == []
    finally:
        db.close()


# ── 12. Sage competency completion can satisfy training dependency ───────

def test_sage_competency_completion_can_satisfy_training_dependency():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        learner = uid("tech")
        assert steward_specialist_integration_service.check_sage_training_dependency_satisfied(db, tenant_id, learner) is False
        db.add(SageLearningPlan(tenant_id=tenant_id, learner_or_group=learner, completion_status="completed"))
        db.commit()
        assert steward_specialist_integration_service.check_sage_training_dependency_satisfied(db, tenant_id, learner) is True
    finally:
        db.close()


# ── 13. Vulcan repair outcome updates action effectiveness ───────────────

def test_vulcan_repair_outcome_updates_action_effectiveness():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        instrument_identity = uid("barcode")
        result = steward_specialist_integration_service.update_action_effectiveness_from_vulcan(
            db, tenant_id, action.id, instrument_identity=instrument_identity, instrument_type="kerrison rongeur",
        )
        assert "Vulcan reliability outcome" in result["actual_outcomes"]
    finally:
        db.close()


# ── 14. Benefits realization compares expected and actual metrics ────────

def test_benefits_realization_compares_expected_and_actual_metrics():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        exceeded = steward_benefits_realization_service.record_outcome_review(
            db, tenant_id, action.id, metric_name="inspection_coverage_pct", baseline_value=72, expected_value=90, actual_value=95,
        )
        assert exceeded.classification == BENEFITS_EXCEEDED
        achieved = steward_benefits_realization_service.record_outcome_review(
            db, tenant_id, action.id, metric_name="inspection_coverage_pct", baseline_value=72, expected_value=90, actual_value=90,
        )
        assert achieved.classification == BENEFITS_ACHIEVED
        partial = steward_benefits_realization_service.record_outcome_review(
            db, tenant_id, action.id, metric_name="inspection_coverage_pct", baseline_value=72, expected_value=90, actual_value=80,
        )
        assert partial.classification == BENEFITS_PARTIALLY_ACHIEVED
    finally:
        db.close()


# ── 15. Inconclusive evidence does not claim success ──────────────────────

def test_inconclusive_evidence_does_not_claim_success():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        row = steward_benefits_realization_service.record_outcome_review(
            db, tenant_id, action.id, metric_name="repeat_bone_findings", baseline_value=12, expected_value=4, actual_value=None,
        )
        assert row.classification == BENEFITS_INCONCLUSIVE
        assert row.classification != BENEFITS_ACHIEVED
    finally:
        db.close()


# ── 16. Unintended consequence triggers review ────────────────────────────

def test_unintended_consequence_triggers_review():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        steward_unintended_consequence_service.flag_consequence(
            db, tenant_id, action.id, consequence_type="increased_supervisor_workload", description="Reviews taking longer.",
            changed_by="tech@local.dev", changed_by_role="operator",
        )
        refreshed = steward_action_service.get_action(db, tenant_id, action.id)
        assert refreshed.status == STATUS_AT_RISK
    finally:
        db.close()


# ── 17. Closure requires authorized approval ──────────────────────────────

def test_closure_requires_authorized_approval():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        steward_action_service.assign_owner(db, tenant_id, action.id, owner="tech@local.dev", accountable_leader="mgr@local.dev", changed_by="a", changed_by_role="spd_manager")
        with pytest.raises(ValueError):
            steward_closure_service.close_action(db, tenant_id, action.id, closure_decision="close_and_sustain", closed_by="tech@local.dev", closed_by_role="operator", owner_comments="Done.")
        row = steward_closure_service.close_action(db, tenant_id, action.id, closure_decision="close_and_sustain", closed_by="mgr@local.dev", closed_by_role="spd_manager", owner_comments="Done.")
        assert row.status == STATUS_CLOSED
    finally:
        db.close()


# ── 18. Rollback preserves complete audit history ─────────────────────────

def test_rollback_preserves_complete_audit_history():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        steward_action_service.assign_owner(db, tenant_id, action.id, owner="tech@local.dev", accountable_leader="mgr@local.dev", changed_by="a", changed_by_role="spd_manager")
        steward_action_service.transition_status(db, tenant_id, action.id, new_status=STATUS_BLOCKED, changed_by="a", changed_by_role="operator")
        steward_action_service.transition_status(db, tenant_id, action.id, new_status="IN_PROGRESS", changed_by="a", changed_by_role="operator")
        steward_closure_service.close_action(db, tenant_id, action.id, closure_decision="rollback", closed_by="mgr@local.dev", closed_by_role="spd_manager", owner_comments="Rolling back.")
        history = steward_action_service.audit_history(db, tenant_id, action.id)
        # created + owner assignment + BLOCKED + IN_PROGRESS + CLOSED = 5 events, none removed.
        assert len(history) == 5
        assert history[0]["to_status"] == STATUS_DRAFT
        assert history[-1]["to_status"] == STATUS_CLOSED
    finally:
        db.close()


# ── 19. Cross-tenant action access is denied ──────────────────────────────

def test_cross_tenant_action_access_is_denied():
    tenant_a = uid("steward-t")
    tenant_b = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_a, **_approved_action_kwargs())
        assert steward_action_service.get_action(db, tenant_b, action.id) is None
        assert steward_action_service.get_action(db, tenant_a, action.id) is not None
    finally:
        db.close()


# ── 20. Action scope cannot expand without new authorization ─────────────

def test_action_scope_cannot_expand_without_new_authorization():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        action = steward_action_service.create_action(db, tenant_id, **_approved_action_kwargs())
        with pytest.raises(ValueError):
            steward_action_service.update_scope(db, tenant_id, action.id, action_description="Expanded scope.", changed_by="tech@local.dev", changed_by_role="operator")
        updated = steward_action_service.update_scope(db, tenant_id, action.id, action_description="Expanded scope.", changed_by="mgr@local.dev", changed_by_role="spd_manager")
        assert updated.action_description == "Expanded scope."
    finally:
        db.close()


# ── Route smoke test ───────────────────────────────────────────────────────

def test_steward_route_smoke():
    tenant_id = uid("steward-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="admin")
    finally:
        db.close()

    payload = {
        "source_type": SOURCE_LEADERSHIP_DIRECTIVE, "source_id": "ld-1", "source_decision": "Approved via smoke test.",
        "approved_by": "director@local.dev", "approval_timestamp": datetime.now(timezone.utc).isoformat(),
        "action_title": "Smoke test action", "category": CATEGORY_OPERATIONAL, "action_type": "workload_reassignment",
        "risk_level": "medium",
    }
    r1 = client.post("/api/steward/actions", json=payload, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r1.status_code == 201, r1.text
    action_id = r1.json()["id"]

    r2 = client.get(f"/api/steward/actions/{action_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["action"]["id"] == action_id

    r3 = client.get("/api/steward/workspace", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200

    r4 = client.get("/api/steward/boards/supervisor", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200

    r5 = client.get("/api/steward/notifications", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r5.status_code == 200

    r6 = client.get(f"/api/steward/actions/{action_id}/plan", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r6.status_code == 200
    assert r6.json()["governed_action_id"] == action_id
