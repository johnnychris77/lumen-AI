"""LumenAI AI Leadership Platform — Project Council: Multi-Agent
Leadership Teams & Governed Consensus Intelligence tests.

Covers the 17 named scenarios from the sprint brief's Section 22, plus a
route smoke test. Council is a pure read-and-synthesize leadership layer
over already-built specialists -- see `app/models/council_leadership.py`
for the naming disambiguation from Olympus's unrelated Network
Governance Council.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.council_leadership import (
    CONSENSUS_INSUFFICIENT_EVIDENCE,
    CONSENSUS_SAFETY_DISSENT,
    CONSENSUS_SPLIT,
    CONSENSUS_UNANIMOUS,
    DEFAULT_TEAM_DEFINITIONS,
    OUTCOME_INEFFECTIVE,
)
from app.models.inspection_finding import InspectionFinding
from app.services import (
    council_consensus_service,
    council_decision_options_service,
    council_dissent_service,
    council_human_decision_service,
    council_orchestration_service,
    council_outcome_service,
    council_specialist_assessment_service,
    council_team_registry_service,
)
from app.services.council_brief_service import executive_brief, manager_brief, supervisor_brief

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}

_counter = [0]


def uid(prefix: str) -> str:
    _counter[0] += 1
    return f"{prefix}-{int(time.time() * 1000) % 1_000_000}-{_counter[0]}"


def _seed_membership(db, tenant_id: str, *, role: str = "admin") -> None:
    db.add(models.TenantMembership(tenant_id=tenant_id, user_email=f"{role}@local.dev", role=role, is_enabled=True))
    db.commit()


def _headers(base: dict, tenant_id: str) -> dict:
    return {**base, "x-tenant-id": tenant_id}


def _mk_inspection(db, tenant_id, *, barcode="BC1", instrument_type="kerrison rongeur"):
    row = models.Inspection(
        tenant_id=tenant_id, file_name="t.jpg", instrument_type=instrument_type, instrument_barcode=barcode,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _mk_finding(db, tenant_id, inspection_id, *, finding_type="corrosion", zone="jaw", severity_index=2):
    row = InspectionFinding(tenant_id=tenant_id, inspection_id=inspection_id, finding_type=finding_type, zone=zone, severity_index=severity_index)
    db.add(row)
    db.commit()
    return row


def _open_and_convene_reliability_case(db, tenant_id):
    insp = _mk_inspection(db, tenant_id, barcode=uid("BC"))
    _mk_finding(db, tenant_id, insp.id)
    case = council_orchestration_service.open_case(
        db, tenant_id, case_type="recurring_instrument_failure", source_event="Recurring corrosion in O-ring region",
        inspection_ids=[insp.id], instrument_ids=[f"barcode:{insp.instrument_barcode}"], risk_level="high", urgency="urgent",
    )
    return council_orchestration_service.convene(db, tenant_id, case.id)


# ── 1. Council selects appropriate specialists by case type ──────────────

def test_council_selects_appropriate_specialists_by_case_type():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        team_key, specialists = council_orchestration_service.select_specialists_for_case(db, tenant_id, "education_need")
        assert team_key == "education"
        assert set(specialists) == set(DEFAULT_TEAM_DEFINITIONS["education"]["required_specialists"])

        team_key2, specialists2 = council_orchestration_service.select_specialists_for_case(db, tenant_id, "enterprise_trend")
        assert team_key2 == "executive"
        assert set(specialists2) == set(DEFAULT_TEAM_DEFINITIONS["executive"]["required_specialists"])
    finally:
        db.close()


# ── 2. specialist assessments are captured independently ─────────────────

def test_specialist_assessments_captured_independently():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        insp = _mk_inspection(db, tenant_id, barcode=uid("BC"))
        _mk_finding(db, tenant_id, insp.id)
        case = council_orchestration_service.open_case(
            db, tenant_id, case_type="recurring_instrument_failure",
            inspection_ids=[insp.id], instrument_ids=[f"barcode:{insp.instrument_barcode}"],
        )
        rows = council_specialist_assessment_service.run_independent_assessments(db, tenant_id, case, case_specialists := ["vulcan", "veritas", "sentinelx"])
        assert len(rows) == len(case_specialists)
        assert {r.specialist_key for r in rows} == set(case_specialists)
        for row in rows:
            assert row.is_revision is False
            assert row.supersedes_assessment_id is None
    finally:
        db.close()


# ── 3. original assessments remain immutable ──────────────────────────────

def test_original_assessments_remain_immutable():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        insp = _mk_inspection(db, tenant_id, barcode=uid("BC"))
        case = council_orchestration_service.open_case(db, tenant_id, case_type="repair_recurrence", inspection_ids=[insp.id])

        original = council_specialist_assessment_service.submit_assessment(
            db, tenant_id, case.id, "vulcan", {"conclusion": "Initial read: reliable.", "recommended_action": "Continue monitoring."},
        )
        revision = council_specialist_assessment_service.submit_revision(
            db, tenant_id, case, "vulcan", {"conclusion": "Revised after seeing Sentinel-X: elevated concern.", "recommended_action": "Hold for repair evaluation."},
        )
        assert revision.supersedes_assessment_id == original.id
        assert revision.is_revision is True

        db.refresh(original)
        assert original.conclusion == "Initial read: reliable."
        assert original.is_revision is False

        all_rows = council_specialist_assessment_service.assessments_for_case(db, tenant_id, case.id)
        assert len(all_rows) == 2
        latest = council_specialist_assessment_service.latest_assessments_for_case(db, tenant_id, case.id)
        assert len(latest) == 1
        assert latest[0]["conclusion"].startswith("Revised")
    finally:
        db.close()


# ── 4. unanimous agreement produces UNANIMOUS status ──────────────────────

def test_unanimous_agreement_produces_unanimous_status():
    assessments = [
        {"specialist_key": "vulcan", "recommended_action": "Reclean and repeat inspection.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
        {"specialist_key": "veritas", "recommended_action": "Reclean and repeat inspection.", "confidence": "high", "urgency": "routine", "evidence_limitations": ""},
    ]
    result = council_consensus_service.classify_consensus(assessments, ["vulcan", "veritas"])
    assert result["status"] == CONSENSUS_UNANIMOUS


# ── 5. material disagreement produces SPLIT_DECISION ──────────────────────

def test_material_disagreement_produces_split_decision():
    assessments = [
        {"specialist_key": "vulcan", "recommended_action": "Hold for repair evaluation.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
        {"specialist_key": "veritas", "recommended_action": "Manufacturer evaluation.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
        {"specialist_key": "sage", "recommended_action": "Reclean and repeat inspection.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
    ]
    result = council_consensus_service.classify_consensus(assessments, ["vulcan", "veritas", "sage"])
    assert result["status"] == CONSENSUS_SPLIT


# ── 6. missing evidence produces INSUFFICIENT_EVIDENCE ────────────────────

def test_missing_evidence_produces_insufficient_evidence():
    assessments = [
        {"specialist_key": "vulcan", "recommended_action": "Hold for repair evaluation.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
    ]
    result = council_consensus_service.classify_consensus(assessments, ["vulcan", "veritas"])
    assert result["status"] == CONSENSUS_INSUFFICIENT_EVIDENCE


# ── 7. unresolved safety dissent cannot be majority-overridden ───────────

def test_unresolved_safety_dissent_cannot_be_majority_overridden():
    assessments = [
        {"specialist_key": "vulcan", "recommended_action": "Proceed with increased monitoring.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
        {"specialist_key": "veritas", "recommended_action": "Proceed with increased monitoring.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
        {"specialist_key": "aegis", "recommended_action": "Proceed with increased monitoring.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
        {"specialist_key": "sage", "recommended_action": "Proceed with increased monitoring.", "confidence": "moderate", "urgency": "routine", "evidence_limitations": ""},
        {"specialist_key": "sentinelx", "recommended_action": "Hold for supervisor review.", "confidence": "high", "urgency": "urgent", "evidence_limitations": ""},
    ]
    result = council_consensus_service.classify_consensus(assessments, ["vulcan", "veritas", "aegis", "sage", "sentinelx"])
    assert result["status"] == CONSENSUS_SAFETY_DISSENT
    assert "sentinelx" in result["dissenting_specialists"]


# ── 8. dissent remains visible in final report ────────────────────────────

def test_dissent_remains_visible_in_final_report():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_id)
        dissent = council_dissent_service.dissent_for_case(db, tenant_id, case.id)
        if case.consensus_status in (CONSENSUS_SAFETY_DISSENT, CONSENSUS_SPLIT):
            assert dissent
        for d in dissent:
            assert d["dissenting_specialist"]
            assert d["proposed_alternative_action"] or d["additional_evidence_required"]
    finally:
        db.close()


# ── 9. decision options include tradeoffs and authority requirements ─────

def test_decision_options_include_tradeoffs_and_authority():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_id)
        options = council_decision_options_service.options_for_case(db, tenant_id, case.id)
        assert options
        for opt in options:
            assert opt["option_title"]
            assert opt["required_authority"]
            assert opt["evidence_strength"] in ("low", "moderate", "high")
            assert opt["reversibility"] in ("reversible", "irreversible")
            assert opt["financial_impact"] == ""
    finally:
        db.close()


# ── 10. technician cannot finalize Council decision ───────────────────────

def test_technician_cannot_finalize_council_decision():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_id)
        assert council_human_decision_service.can_approve("viewer", case.required_approval_tier) is False
        assert council_human_decision_service.can_approve("operator", case.required_approval_tier) is False

        raised = False
        try:
            council_human_decision_service.finalize_decision(
                db, tenant_id, case.id, approver="tech@local.dev", approver_role="operator", decision="Proceed.",
            )
        except PermissionError:
            raised = True
        assert raised
    finally:
        db.close()


# ── 11. correct human role can approve within scope ───────────────────────

def test_correct_human_role_can_approve_within_scope():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_id)
        assert council_human_decision_service.can_approve("admin", case.required_approval_tier) is True

        decision = council_human_decision_service.finalize_decision(
            db, tenant_id, case.id, approver="admin@local.dev", approver_role="admin", decision="Hold for repair evaluation.",
        )
        assert decision.decision == "Hold for repair evaluation."
        db.refresh(case)
        assert case.status == "resolved"
    finally:
        db.close()


# ── 12. cross-tenant Council access is denied ─────────────────────────────

def test_cross_tenant_council_access_is_denied():
    tenant_a = uid("council-t")
    tenant_b = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_a)
        case_id = case.id
        assert council_orchestration_service.get_case(db, tenant_b, case_id) is None
        assert council_orchestration_service.list_cases(db, tenant_b) == []

        _seed_membership(db, tenant_a)
        _seed_membership(db, tenant_b)
    finally:
        db.close()

    r = client.get(f"/api/council/cases/{case_id}", headers=_headers(AUTH_ADMIN, tenant_b))
    assert r.status_code == 404


# ── 13. outcome review links back to original recommendation ─────────────

def test_outcome_review_links_back_to_original_recommendation():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_id)
        row = council_outcome_service.record_outcome_review(db, tenant_id, case.id, issue_resolved=True, recurred=False)
        reviews = council_outcome_service.outcome_reviews_for_case(db, tenant_id, case.id)
        assert len(reviews) == 1
        assert reviews[0]["council_case_id"] == case.id
        assert reviews[0]["id"] == row.id
    finally:
        db.close()


# ── 14. ineffective recommendation creates learning signal ───────────────

def test_ineffective_recommendation_creates_learning_signal():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_id)
        before_action = case.recommended_action

        row = council_outcome_service.record_outcome_review(db, tenant_id, case.id, issue_resolved=False, recurred=True)
        assert row.classification == OUTCOME_INEFFECTIVE
        assert row.knowledge_update_recommended is True

        db.refresh(case)
        assert case.recommended_action == before_action  # never automatically rewritten
    finally:
        db.close()


# ── 15. Council configuration changes are versioned ───────────────────────

def test_council_configuration_changes_are_versioned():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        council_team_registry_service.ensure_default_teams(db, tenant_id)
        original = council_team_registry_service.get_team_config(db, tenant_id, "reliability")
        assert original.version == 1

        updated = council_team_registry_service.update_team_config(
            db, tenant_id, "reliability", quorum_requirement=4, owner="qa@local.dev",
        )
        assert updated.version == 2
        assert updated.is_current is True

        history = council_team_registry_service.team_config_history(db, tenant_id, "reliability")
        assert len(history) == 2
        assert history[0]["version"] == 1
        assert history[0]["is_current"] is False

        raised = False
        try:
            council_team_registry_service.update_team_config(
                db, tenant_id, "reliability", required_specialists=["vulcan", "aegis", "maestro"],
            )
        except ValueError:
            raised = True
        assert raised  # can't drop mandatory safety specialists (veritas, sentinelx)
    finally:
        db.close()


# ── 16. no agent automatically changes clinical rules ─────────────────────

def test_no_agent_automatically_changes_clinical_rules():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_id)
        team_before = council_team_registry_service.get_team_config(db, tenant_id, case.team_key)
        version_before = team_before.version

        council_outcome_service.record_outcome_review(db, tenant_id, case.id, issue_resolved=False, recurred=True)

        team_after = council_team_registry_service.get_team_config(db, tenant_id, case.team_key)
        assert team_after.version == version_before  # outcome review never mutates team/rule configuration
    finally:
        db.close()


# ── 17. Council brief remains grounded in case evidence ───────────────────

def test_council_brief_remains_grounded_in_case_evidence():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        case = _open_and_convene_reliability_case(db, tenant_id)

        sup = supervisor_brief(db, tenant_id, case.id)
        assert sup["council_case_id"] == case.id
        assert sup["specialist_recommendation"] == case.recommended_action

        mgr = manager_brief(db, tenant_id, case.id)
        assert mgr["council_case_id"] == case.id
        assert mgr["recommended_owner"] == case.required_human_approver

        exe = executive_brief(db, tenant_id, case.id)
        assert exe["council_case_id"] == case.id
        assert exe["recommended_strategic_action"] == case.recommended_action
    finally:
        db.close()


# ── Route smoke test ──────────────────────────────────────────────────────

def test_open_convene_and_workspace_routes():
    tenant_id = uid("council-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
        insp = _mk_inspection(db, tenant_id, barcode=uid("BC"))
        _mk_finding(db, tenant_id, insp.id)
        barcode = insp.instrument_barcode
        inspection_id = insp.id
    finally:
        db.close()

    r = client.post(
        "/api/council/cases",
        json={"case_type": "recurring_instrument_failure", "inspection_ids": [inspection_id], "instrument_ids": [f"barcode:{barcode}"], "urgency": "urgent"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    case_id = r.json()["id"]

    r2 = client.post(f"/api/council/cases/{case_id}/convene", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    body = r2.json()
    assert body["consensus_status"]
    assert body["human_review_required"] is True

    r3 = client.get("/api/council/workspace", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert "active_case_count" in r3.json()

    r4 = client.get(f"/api/council/cases/{case_id}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r4.status_code == 200
    assert "dissent" in r4.json()

    r5 = client.get("/api/council/teams", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r5.status_code == 200
