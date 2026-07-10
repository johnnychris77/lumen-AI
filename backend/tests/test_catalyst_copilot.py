"""v4.4 — LumenAI OS: Project Catalyst — AI Copilot & Natural Language
Operations tests.

Covers: intent recognition, conversation memory, role-based responses,
explainability, report generation, workflow execution, Digital Twin
retrieval, Knowledge Graph lookup, natural language actions, and session
isolation.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.services import (
    catalyst_action_engine,
    catalyst_conversation_service,
    catalyst_persona_service,
    catalyst_query_engine,
    catalyst_skills_service,
    forge_workflow_service,
    knowledge_repository_service,
)

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


def _make_inspection(tenant_id: str, *, instrument_type: str = "kerrison_rongeur") -> int:
    db = SessionLocal()
    try:
        insp = Inspection(
            tenant_id=tenant_id, file_name="x.jpg", instrument_type=instrument_type, vendor_name="AcmeSurgical",
            status="pending", coverage_pct=90, confidence=0.9, facility_name="Main Hospital",
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_finding(inspection_id: int, tenant_id: str, *, finding_type: str = "blood") -> None:
    db = SessionLocal()
    try:
        db.add(InspectionFinding(
            tenant_id=tenant_id, inspection_id=inspection_id, instrument_type="kerrison_rongeur",
            finding_type=finding_type, zone="serration", severity_index=2,
        ))
        db.commit()
    finally:
        db.close()


_SIMPLE_WORKFLOW_NODES = [
    {"key": "start", "type": "start", "label": "Start", "x": 0, "y": 0},
    {"key": "inspection", "type": "inspection", "label": "Inspection", "x": 200, "y": 0},
    {"key": "end", "type": "end", "label": "End", "x": 400, "y": 0},
]
_SIMPLE_WORKFLOW_EDGES = [{"from": "start", "to": "inspection"}, {"from": "inspection", "to": "end"}]


# ── 1. Intent recognition ────────────────────────────────────────────────────

def test_intent_recognition_covers_named_example_queries():
    assert catalyst_query_engine.classify_intent("How many instruments are awaiting supervisor review?") == catalyst_query_engine.INTENT_SUPERVISOR_BACKLOG
    assert catalyst_query_engine.classify_intent("Give me the executive summary for this week.") == catalyst_query_engine.INTENT_EXECUTIVE_SUMMARY
    assert catalyst_query_engine.classify_intent("Which Digital Twins are showing declining health?") == catalyst_query_engine.INTENT_DIGITAL_TWIN_HEALTH
    assert catalyst_query_engine.classify_intent("What's our contamination rate by anatomy zone?") == catalyst_query_engine.INTENT_ANATOMY_CONTAMINATION
    assert catalyst_query_engine.classify_intent("Show me recurring corrosion findings.") == catalyst_query_engine.INTENT_RECURRING_FINDING_TREND
    assert catalyst_query_engine.classify_intent("Which kerrison had blood findings this week?") == catalyst_query_engine.INTENT_INSTRUMENT_FINDING_SEARCH
    assert catalyst_query_engine.classify_intent("What's the workload forecast for next week?") == catalyst_query_engine.INTENT_FORECAST
    assert catalyst_query_engine.classify_intent("gibberish that matches nothing") == catalyst_query_engine.INTENT_UNKNOWN


def test_instrument_finding_search_returns_matching_inspection():
    tenant_id = uid("cat-tenant")
    insp_id = _make_inspection(tenant_id)
    _make_finding(insp_id, tenant_id, finding_type="blood")

    db = SessionLocal()
    try:
        result = catalyst_query_engine.answer_query(db, tenant_id, "Which kerrison had blood findings this week?")
    finally:
        db.close()

    assert result["intent"] == catalyst_query_engine.INTENT_INSTRUMENT_FINDING_SEARCH
    assert result["data"]["count"] >= 1


# ── 2. Conversation memory ───────────────────────────────────────────────────

def test_chat_persists_conversation_and_recalls_history():
    tenant_id = uid("cat-tenant")
    headers = _headers(AUTH_ADMIN, tenant_id)

    first = client.post("/api/catalyst/chat", json={"message": "What's our contamination rate by anatomy zone?"}, headers=headers)
    assert first.status_code == 200
    conversation_id = first.json()["conversation_id"]

    second = client.post(
        "/api/catalyst/chat", json={"message": "Show me recurring corrosion findings.", "conversation_id": conversation_id}, headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id

    history = client.get(f"/api/catalyst/conversations/{conversation_id}/messages", headers=headers)
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert len(messages) == 4  # 2 user + 2 assistant turns
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_conversation_retention_archives_stale_conversations():
    tenant_id = uid("cat-tenant")
    db = SessionLocal()
    try:
        conv = catalyst_conversation_service.get_or_create_active_conversation(db, tenant_id, "tech@example.com")
        from datetime import datetime, timedelta, timezone
        conv.updated_at = datetime.now(timezone.utc) - timedelta(days=catalyst_conversation_service.CONVERSATION_RETENTION_DAYS + 1)
        db.commit()

        archived_count = catalyst_conversation_service.apply_retention(db, tenant_id)
        assert archived_count >= 1

        active = catalyst_conversation_service.list_conversations(db, tenant_id, "tech@example.com")
        assert all(c["id"] != conv.id for c in active)
    finally:
        db.close()


# ── 3. Role-based responses ──────────────────────────────────────────────────

def test_persona_for_role_mapping():
    assert catalyst_persona_service.persona_for_role("facility_director") == catalyst_persona_service.PERSONA_EXECUTIVE
    assert catalyst_persona_service.persona_for_role("spd_manager") == catalyst_persona_service.PERSONA_SUPERVISOR
    assert catalyst_persona_service.persona_for_role("technician") == catalyst_persona_service.PERSONA_TECHNICIAN
    assert catalyst_persona_service.persona_for_role("unknown_role_xyz") == catalyst_persona_service.PERSONA_TECHNICIAN


def test_executive_briefing_requires_leadership_role():
    tenant_id = uid("cat-tenant")
    denied = client.get("/api/catalyst/persona/executive-briefing", headers=_headers(AUTH_VIEWER, tenant_id))
    assert denied.status_code == 403

    allowed = client.get("/api/catalyst/persona/executive-briefing?cadence=monthly", headers=_headers(AUTH_MGR, tenant_id))
    assert allowed.status_code == 200
    body = allowed.json()
    assert "quality" in body and "risk" in body and "forecast" in body and "emerging_trends" in body


def test_technician_contextual_help_never_overrides_supervisor_authority():
    tenant_id = uid("cat-tenant")
    _make_inspection(tenant_id)
    res = client.get("/api/catalyst/persona/technician-help?instrument_type=kerrison_rongeur", headers=_headers(AUTH_VIEWER, tenant_id))
    assert res.status_code == 200
    assert "supervisor review authority is unchanged" in res.json()["note"].lower()


# ── 4. Explainability ─────────────────────────────────────────────────────────

def test_chat_response_always_carries_evidence_envelope():
    tenant_id = uid("cat-tenant")
    res = client.post("/api/catalyst/chat", json={"message": "How many instruments are awaiting supervisor review?"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200
    evidence = res.json()["evidence"]
    for key in ["evidence_used", "knowledge_sources", "digital_twin_factors", "workflow_rules", "reasoning_path", "confidence", "references", "human_review_required"]:
        assert key in evidence
    assert evidence["human_review_required"] is True


# ── 5. Report generation ─────────────────────────────────────────────────────

def test_reporting_skill_falls_back_to_live_dashboard_without_enterprise_facility():
    tenant_id = uid("cat-tenant")
    db = SessionLocal()
    try:
        result = catalyst_skills_service.reporting_skill(db, tenant_id)
    finally:
        db.close()
    assert result["source"] == "pulse_executive_dashboard"
    assert "live_kpis" in result


# ── 6. Workflow execution (via Natural Language Actions) ────────────────────

def test_publish_workflow_action_requires_confirmation_then_executes():
    tenant_id = uid("cat-tenant")
    db = SessionLocal()
    try:
        workflow = forge_workflow_service.create_workflow(
            db, tenant_id, name="Catalyst test workflow", nodes=_SIMPLE_WORKFLOW_NODES, edges=_SIMPLE_WORKFLOW_EDGES, author="tester",
        )
    finally:
        db.close()

    headers = _headers(AUTH_MGR, tenant_id)
    proposal = client.post(
        "/api/catalyst/actions/propose",
        json={"action_type": "publish_workflow", "params": {"workflow_id": workflow["id"]}},
        headers=headers,
    )
    assert proposal.status_code == 200
    body = proposal.json()
    assert body["requires_confirmation"] is True
    token = body["confirm_token"]

    confirmed = client.post("/api/catalyst/actions/confirm", json={"confirm_token": token}, headers=headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["result"]["status"] == "published"


# ── 7. Digital Twin retrieval ─────────────────────────────────────────────────

def test_digital_twin_skill_returns_real_dashboard_shape():
    tenant_id = uid("cat-tenant")
    db = SessionLocal()
    try:
        result = catalyst_skills_service.digital_twin_skill(db, tenant_id, facility_id="")
    finally:
        db.close()
    assert result["skill"] == "digital_twin"
    assert "twin_state" in result["dashboard"]


# ── 8. Knowledge Graph lookup ─────────────────────────────────────────────────

def test_knowledge_search_skill_finds_seeded_article():
    tenant_id = uid("cat-tenant")
    db = SessionLocal()
    try:
        knowledge_repository_service.create_article(
            db, tenant_id=tenant_id, category="best_practice", title="Kerrison cleaning best practice",
            body="Clean the serration zone thoroughly.", author="tester", approval_status="approved",
        )
        db.commit()
        result = catalyst_skills_service.knowledge_search_skill(db, tenant_id, query="kerrison")
    finally:
        db.close()
    assert result["skill"] == "knowledge_search"
    assert len(result["articles"]) >= 1


# ── 9. Natural language actions (critical vs non-critical, cancel flow) ─────

def test_notify_supervisor_action_requires_confirmation():
    tenant_id = uid("cat-tenant")
    headers = _headers(AUTH_ADMIN, tenant_id)
    proposal = client.post(
        "/api/catalyst/actions/propose",
        json={"action_type": "notify_supervisor", "params": {"message": "Please review this Kerrison."}},
        headers=headers,
    )
    assert proposal.status_code == 200
    assert proposal.json()["requires_confirmation"] is True


def test_open_digital_twin_action_executes_immediately_without_confirmation():
    tenant_id = uid("cat-tenant")
    headers = _headers(AUTH_ADMIN, tenant_id)
    proposal = client.post(
        "/api/catalyst/actions/propose", json={"action_type": "open_digital_twin", "params": {}}, headers=headers,
    )
    assert proposal.status_code == 200
    body = proposal.json()
    assert body["requires_confirmation"] is False
    assert "dashboard" in body["result"]


def test_cancel_action_prevents_execution():
    tenant_id = uid("cat-tenant")
    headers = _headers(AUTH_ADMIN, tenant_id)
    proposal = client.post(
        "/api/catalyst/actions/propose", json={"action_type": "create_capa_draft", "params": {"title": "Test CAPA"}}, headers=headers,
    )
    token = proposal.json()["confirm_token"]

    cancelled = client.post("/api/catalyst/actions/cancel", json={"confirm_token": token}, headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    confirm_after_cancel = client.post("/api/catalyst/actions/confirm", json={"confirm_token": token}, headers=headers)
    assert confirm_after_cancel.status_code == 409


def test_unknown_action_type_is_rejected():
    tenant_id = uid("cat-tenant")
    res = client.post(
        "/api/catalyst/actions/propose", json={"action_type": "not_a_real_action", "params": {}}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 422


# ── 10. Session isolation ────────────────────────────────────────────────────

def test_conversations_isolated_by_tenant_and_user():
    tenant_a = uid("cat-tenant-a")
    tenant_b = uid("cat-tenant-b")

    chat_a = client.post("/api/catalyst/chat", json={"message": "What's our contamination rate by anatomy zone?"}, headers=_headers(AUTH_ADMIN, tenant_a))
    conversation_id = chat_a.json()["conversation_id"]

    # Same conversation_id, different tenant -> cannot read the other tenant's messages.
    cross_tenant = client.get(f"/api/catalyst/conversations/{conversation_id}/messages", headers=_headers(AUTH_ADMIN, tenant_b))
    assert cross_tenant.json()["messages"] == []

    same_tenant_list = client.get("/api/catalyst/conversations", headers=_headers(AUTH_ADMIN, tenant_b))
    assert all(c["id"] != conversation_id for c in same_tenant_list.json()["conversations"])


def test_pending_actions_isolated_by_user_email():
    tenant_id = uid("cat-tenant")
    db = SessionLocal()
    try:
        catalyst_action_engine.propose_action(
            db, tenant_id, "user-one@example.com", conversation_id=0, action_type="notify_supervisor",
            params={"message": "hello"}, actor="user-one@example.com",
        )
        pending_for_other_user = catalyst_action_engine.list_pending_actions(db, tenant_id, "user-two@example.com")
    finally:
        db.close()
    assert pending_for_other_user == []
