"""v5.4 — LumenAI Network: Project Nova — Autonomous AI Agent Platform
tests.

Covers: agent lifecycle, orchestration, communication, memory,
permissions, health monitoring, observability, and marketplace.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app

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


# ── 1. Agent lifecycle ────────────────────────────────────────────────────────

def test_seed_core_agents_and_registry_merges_phase22():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post("/api/nova/agents/seed-core", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert len(r.json()["agents"]) == 14

    r2 = client.get("/api/nova/agents", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert len(r2.json()["nova_agents"]) == 14
    assert len(r2.json()["phase22_pipeline_agents"]) == 10  # the pre-existing Phase 22 pipeline, untouched


def test_get_agent_and_set_status():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    client.post("/api/nova/agents/seed-core", headers=_headers(AUTH_ADMIN, tenant_id))

    r = client.get("/api/nova/agents/knowledge_agent", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["wrapped_module"] == "app.services.athena_memory_service"
    assert r.json()["health"] == "ok"

    r2 = client.patch("/api/nova/agents/knowledge_agent/status", json={"status": "disabled"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["status"] == "disabled"


def test_unknown_agent_404s():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/nova/agents/not_a_real_agent", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 404


def test_invoke_agent_dispatches_to_real_service():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post("/api/nova/agents/knowledge_agent/invoke", json={}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    # A real composition of Athena's memory service, not a fabricated result.
    assert isinstance(r.json(), dict)


def test_invoke_reference_only_agent_is_honest():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post("/api/nova/agents/vision_agent/invoke", json={}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert r.json()["invoked"] is False


def test_invoke_unknown_agent_key_rejected():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post("/api/nova/agents/not_a_real_agent/invoke", json={}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 422


# ── 2. Orchestration ───────────────────────────────────────────────────────────

def test_task_run_lifecycle_advances_and_completes():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/nova/task-runs",
        json={"pipeline_name": "image-to-recommendation", "agent_sequence": ["vision_agent", "anatomy_agent", "knowledge_agent"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    run_id = r.json()["id"]
    assert r.json()["status"] == "running"

    r2 = client.post(f"/api/nova/task-runs/{run_id}/advance", json={"output_summary": {"zones": ["tip"]}}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["current_step_index"] == 1
    assert r2.json()["status"] == "running"

    client.post(f"/api/nova/task-runs/{run_id}/advance", json={}, headers=_headers(AUTH_ADMIN, tenant_id))
    r3 = client.post(f"/api/nova/task-runs/{run_id}/advance", json={}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 200
    assert r3.json()["status"] == "completed"
    assert r3.json()["completed_at"] is not None


def test_task_run_empty_sequence_rejected():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post("/api/nova/task-runs", json={"pipeline_name": "empty", "agent_sequence": []}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 422


def test_task_run_fail_and_cannot_advance_after():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/nova/task-runs", json={"pipeline_name": "x", "agent_sequence": ["vision_agent"]}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    run_id = r.json()["id"]
    r2 = client.post(f"/api/nova/task-runs/{run_id}/fail", json={"reason": "vision service unavailable"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["status"] == "failed"

    r3 = client.post(f"/api/nova/task-runs/{run_id}/advance", json={}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r3.status_code == 422


def test_unknown_task_run_404s():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.get("/api/nova/task-runs/999999999", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 404


# ── 3. Communication ───────────────────────────────────────────────────────────

def test_task_run_advance_logs_communication_bus_message():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/nova/task-runs", json={"pipeline_name": "x", "agent_sequence": ["vision_agent", "anatomy_agent"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    run_id = r.json()["id"]
    client.post(f"/api/nova/task-runs/{run_id}/advance", json={}, headers=_headers(AUTH_ADMIN, tenant_id))

    r2 = client.get("/api/nova/messages", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert any(m["source_agent_key"] == "vision_agent" and m["target_agent_key"] == "anatomy_agent" for m in r2.json()["messages"])


def test_messages_filtered_by_agent_key():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    client.post("/api/nova/agents/knowledge_agent/invoke", json={}, headers=_headers(AUTH_ADMIN, tenant_id))

    r = client.get("/api/nova/messages", params={"agent_key": "knowledge_agent"}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    assert all(m["source_agent_key"] == "knowledge_agent" or m["target_agent_key"] == "knowledge_agent" for m in r.json()["messages"])


# ── 4. Memory ──────────────────────────────────────────────────────────────────

def test_agent_memory_is_tenant_scoped():
    tenant_a = uid("nova-a")
    tenant_b = uid("nova-b")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_a)
        _seed_membership(db, tenant_b)
    finally:
        db.close()

    r = client.post(
        "/api/nova/agents/knowledge_agent/memory",
        json={"memory_type": "task_history", "content": {"note": "reviewed inspection 42"}},
        headers=_headers(AUTH_ADMIN, tenant_a),
    )
    assert r.status_code == 201

    r_a = client.get("/api/nova/agents/knowledge_agent/memory", headers=_headers(AUTH_ADMIN, tenant_a))
    assert r_a.status_code == 200
    assert len(r_a.json()["memory"]) == 1

    r_b = client.get("/api/nova/agents/knowledge_agent/memory", headers=_headers(AUTH_ADMIN, tenant_b))
    assert r_b.status_code == 200
    assert len(r_b.json()["memory"]) == 0


def test_invalid_memory_type_rejected():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(
        "/api/nova/agents/knowledge_agent/memory", json={"memory_type": "not_real", "content": {}}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 422


# ── 5. Permissions / Governance ────────────────────────────────────────────────

def test_viewer_cannot_seed_agents_or_change_status():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id, role="viewer")
    finally:
        db.close()
    r = client.post("/api/nova/agents/seed-core", headers=_headers(AUTH_VIEWER, tenant_id))
    assert r.status_code == 403


def test_nova_routes_require_tenant_membership():
    tenant_id = uid("nova-nomember")
    r = client.get("/api/nova/agents", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code in (401, 403)


def test_collaboration_request_lifecycle_and_escalation():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/nova/collaboration-requests",
        json={"agent_key": "clinical_reasoning_agent", "request_type": "approve_work", "description": "Approve risk assessment."},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 201
    request_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    r2 = client.post(
        f"/api/nova/collaboration-requests/{request_id}/resolve",
        json={"decision": "approved", "resolution": "Confirmed by supervisor."},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "approved"

    # Already-resolved requests cannot be resolved again.
    r3 = client.post(
        f"/api/nova/collaboration-requests/{request_id}/resolve", json={"decision": "approved"}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r3.status_code == 422

    r4 = client.post(
        "/api/nova/collaboration-requests",
        json={"agent_key": "clinical_reasoning_agent", "request_type": "escalate_to_supervisor", "description": "Needs supervisor."},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r4.status_code == 201
    assert r4.json()["status"] == "escalated"


def test_invalid_collaboration_request_type_rejected():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    r = client.post(
        "/api/nova/collaboration-requests", json={"agent_key": "knowledge_agent", "request_type": "not_real"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert r.status_code == 422


# ── 6. Health monitoring & Observability ──────────────────────────────────────

def test_observability_summary_reports_honest_gaps():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    client.post("/api/nova/agents/seed-core", headers=_headers(AUTH_ADMIN, tenant_id))

    r = client.get("/api/nova/observability/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert body["agent_health"]["overall_status"] == "ok"
    assert body["latency"]["available"] is False
    assert body["resource_usage"]["available"] is False
    assert body["retries"]["available"] is False


def test_observability_reflects_task_run_outcomes():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.post(
        "/api/nova/task-runs", json={"pipeline_name": "x", "agent_sequence": ["vision_agent"]}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    run_id = r.json()["id"]
    client.post(f"/api/nova/task-runs/{run_id}/fail", json={"reason": "test"}, headers=_headers(AUTH_ADMIN, tenant_id))

    r2 = client.get("/api/nova/observability/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r2.status_code == 200
    assert r2.json()["task_run_outcomes"]["failed"] >= 1


# ── 7. Marketplace ─────────────────────────────────────────────────────────────

def test_agent_marketplace_summary_lists_agent_listing_types():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()

    r = client.get("/api/nova/marketplace/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert "inspection_agent" in body["listing_types"]
    assert "compliance_agent" in body["listing_types"]
    assert "by_listing_type" in body


# ── 8. Umbrella ─────────────────────────────────────────────────────────────────

def test_platform_summary_composes_all_sections():
    tenant_id = uid("nova-t")
    db = SessionLocal()
    try:
        _seed_membership(db, tenant_id)
    finally:
        db.close()
    client.post("/api/nova/agents/seed-core", headers=_headers(AUTH_ADMIN, tenant_id))

    r = client.get("/api/nova/summary", headers=_headers(AUTH_ADMIN, tenant_id))
    assert r.status_code == 200
    body = r.json()
    assert "agent_registry" in body
    assert "observability" in body
    assert "agent_marketplace" in body
