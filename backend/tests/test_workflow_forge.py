"""v4.1 — LumenAI OS: Project Forge — AI Workflow Builder & No-Code
Clinical Rules Engine tests."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.services import forge_rule_engine

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


def _make_inspection(tenant_id: str, *, instrument_type: str = "kerrison_rongeur", vendor_name: str = "AcmeSurgical", coverage_pct: int = 90) -> int:
    db = SessionLocal()
    try:
        insp = Inspection(
            tenant_id=tenant_id, file_name="x.jpg", instrument_type=instrument_type, vendor_name=vendor_name,
            status="pending", coverage_pct=coverage_pct, confidence=0.9, facility_name="Main Hospital",
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_finding(inspection_id: int, tenant_id: str, *, finding_type: str = "blood", zone: str = "serration", severity_index: int = 2) -> None:
    db = SessionLocal()
    try:
        db.add(InspectionFinding(
            tenant_id=tenant_id, inspection_id=inspection_id, instrument_type="kerrison_rongeur",
            finding_type=finding_type, zone=zone, severity_index=severity_index,
        ))
        db.commit()
    finally:
        db.close()


_SIMPLE_WORKFLOW_NODES = [
    {"key": "start", "type": "start", "label": "Start", "x": 0, "y": 0},
    {"key": "inspection", "type": "inspection", "label": "Inspection", "x": 200, "y": 0},
    {"key": "notify", "type": "notification", "label": "Notification", "x": 400, "y": 0},
    {"key": "end", "type": "end", "label": "End", "x": 600, "y": 0},
]
_SIMPLE_WORKFLOW_EDGES = [
    {"from": "start", "to": "inspection"},
    {"from": "inspection", "to": "notify"},
    {"from": "notify", "to": "end"},
]


def _create_workflow(tenant_id: str, *, nodes=None, edges=None) -> dict:
    res = client.post(
        "/api/forge/workflows",
        json={"name": uid("Workflow"), "nodes": nodes or _SIMPLE_WORKFLOW_NODES, "edges": edges or _SIMPLE_WORKFLOW_EDGES},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 200, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Workflow creation
# ---------------------------------------------------------------------------


def test_create_workflow_creates_draft_version_one():
    tenant_id = uid("hospital")
    workflow = _create_workflow(tenant_id)
    assert workflow["status"] == "draft"
    assert workflow["version"] == 1
    assert len(workflow["nodes"]) == 4


def test_create_workflow_rejects_unknown_node_type():
    tenant_id = uid("hospital")
    res = client.post(
        "/api/forge/workflows",
        json={"name": "Bad Workflow", "nodes": [{"key": "x", "type": "not_a_real_node_type"}], "edges": []},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 422


def test_list_workflows_includes_templates():
    tenant_id = uid("hospital")
    client.get("/api/forge/workflow-templates", headers=AUTH_VIEWER)  # ensures templates are seeded
    res = client.get("/api/forge/workflows", headers=_headers(AUTH_VIEWER, tenant_id))
    assert res.status_code == 200, res.text
    categories = {w["category"] for w in res.json()["workflows"]}
    assert "general_instrument_inspection" in categories


# ---------------------------------------------------------------------------
# Rule evaluation + nested conditions
# ---------------------------------------------------------------------------


def test_nested_and_or_not_condition_evaluation():
    condition = {
        "op": "and",
        "conditions": [
            {"field": "instrument_family", "operator": "eq", "value": "kerrison"},
            {
                "op": "or",
                "conditions": [
                    {"field": "finding", "operator": "eq", "value": "blood"},
                    {"field": "finding", "operator": "eq", "value": "corrosion"},
                ],
            },
            {"op": "not", "conditions": [{"field": "severity", "operator": "gte", "value": 5}]},
        ],
    }
    assert forge_rule_engine.evaluate_condition(condition, {"instrument_family": "kerrison", "finding": "blood", "severity": 2}) is True
    assert forge_rule_engine.evaluate_condition(condition, {"instrument_family": "kerrison", "finding": "rust", "severity": 2}) is False
    assert forge_rule_engine.evaluate_condition(condition, {"instrument_family": "kerrison", "finding": "blood", "severity": 6}) is False


def test_condition_missing_field_fails_closed():
    condition = {"field": "confidence", "operator": "gte", "value": 0.5}
    assert forge_rule_engine.evaluate_condition(condition, {}) is False


def test_invalid_condition_rejected_at_creation():
    tenant_id = uid("hospital")
    res = client.post(
        "/api/forge/workflow-rules",
        json={"name": "Bad Rule", "condition": {"field": "not_a_real_field", "operator": "eq", "value": "x"}, "actions": []},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 422


def test_create_and_evaluate_rule_via_api():
    tenant_id = uid("hospital")
    condition = {
        "op": "and",
        "conditions": [
            {"field": "instrument_family", "operator": "eq", "value": "kerrison_rongeur"},
            {"field": "finding", "operator": "eq", "value": "blood"},
            {"field": "inspection_zone", "operator": "eq", "value": "serration"},
        ],
    }
    actions = [{"type": "require_supervisor_review", "params": {}}, {"type": "recommend_reclean", "params": {}}]
    create = client.post(
        "/api/forge/workflow-rules",
        json={"name": "Kerrison Blood Serration Rule", "condition": condition, "actions": actions},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert create.status_code == 200, create.text
    rule_id = create.json()["id"]

    approve = client.post(f"/api/forge/workflow-rules/{rule_id}/approve", headers=_headers(AUTH_ADMIN, tenant_id))
    assert approve.status_code == 200
    assert approve.json()["approval_status"] == "approved"

    match = client.post(
        f"/api/forge/workflow-rules/{rule_id}/evaluate",
        json={"context": {"instrument_family": "kerrison_rongeur", "finding": "blood", "inspection_zone": "serration"}},
        headers=_headers(AUTH_VIEWER, tenant_id),
    )
    assert match.status_code == 200, match.text
    assert match.json()["matched"] is True
    assert len(match.json()["actions"]) == 2

    no_match = client.post(
        f"/api/forge/workflow-rules/{rule_id}/evaluate",
        json={"context": {"instrument_family": "kerrison_rongeur", "finding": "rust", "inspection_zone": "serration"}},
        headers=_headers(AUTH_VIEWER, tenant_id),
    )
    assert no_match.json()["matched"] is False


# ---------------------------------------------------------------------------
# Workflow execution
# ---------------------------------------------------------------------------


def test_execute_workflow_walks_start_to_end_and_notifies():
    tenant_id = uid("hospital")
    workflow = _create_workflow(tenant_id)
    client.post(f"/api/forge/workflows/{workflow['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    inspection_id = _make_inspection(tenant_id)

    res = client.post(
        "/api/forge/workflow-execution",
        json={"workflow_id": workflow["id"], "inspection_id": inspection_id},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "completed"
    assert body["decision_path"] == ["start", "inspection", "notify", "end"]
    assert body["execution_time_ms"] is not None and body["execution_time_ms"] >= 0


def test_execute_unknown_workflow_404():
    tenant_id = uid("hospital")
    res = client.post("/api/forge/workflow-execution", json={"workflow_id": 999999999}, headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 404


def test_conditional_branch_takes_matching_path_and_runs_actions():
    tenant_id = uid("hospital")
    condition = {"field": "finding", "operator": "eq", "value": "blood"}
    rule = client.post(
        "/api/forge/workflow-rules",
        json={"name": "Blood Rule", "condition": condition, "actions": [{"type": "notify_supervisor", "params": {"message": "Blood detected"}}]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    ).json()
    client.post(f"/api/forge/workflow-rules/{rule['id']}/approve", headers=_headers(AUTH_ADMIN, tenant_id))

    nodes = [
        {"key": "start", "type": "start", "label": "Start", "x": 0, "y": 0},
        {"key": "branch", "type": "conditional_branch", "label": "Branch", "x": 200, "y": 0, "config": {"rule_id": rule["id"]}},
        {"key": "end", "type": "end", "label": "End", "x": 400, "y": 0},
    ]
    edges = [{"from": "start", "to": "branch"}, {"from": "branch", "to": "end", "condition": "true"}]
    workflow = _create_workflow(tenant_id, nodes=nodes, edges=edges)
    client.post(f"/api/forge/workflows/{workflow['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))

    inspection_id = _make_inspection(tenant_id)
    _make_finding(inspection_id, tenant_id, finding_type="blood")

    res = client.post(
        "/api/forge/workflow-execution", json={"workflow_id": workflow["id"], "inspection_id": inspection_id},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    branch_step = next(s for s in body["execution_log"] if s.get("node_key") == "branch")
    assert branch_step["rule_result"]["matched"] is True
    assert len(branch_step["actions"]) == 1


def test_repair_referral_node_creates_repair_request():
    tenant_id = uid("hospital")
    nodes = [
        {"key": "start", "type": "start", "label": "Start", "x": 0, "y": 0},
        {"key": "repair", "type": "repair_referral", "label": "Repair", "x": 200, "y": 0, "config": {"instrument_identity": "barcode:123", "vendor_name": "RepairCo"}},
        {"key": "end", "type": "end", "label": "End", "x": 400, "y": 0},
    ]
    edges = [{"from": "start", "to": "repair"}, {"from": "repair", "to": "end"}]
    workflow = _create_workflow(tenant_id, nodes=nodes, edges=edges)
    client.post(f"/api/forge/workflows/{workflow['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    inspection_id = _make_inspection(tenant_id)

    res = client.post(
        "/api/forge/workflow-execution", json={"workflow_id": workflow["id"], "inspection_id": inspection_id},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 200, res.text
    repair_step = next(s for s in res.json()["execution_log"] if s.get("node_key") == "repair")
    assert repair_step["repair_request_id"] is not None


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def test_simulate_workflow_records_expected_vs_actual():
    tenant_id = uid("hospital")
    workflow = _create_workflow(tenant_id)
    client.post(f"/api/forge/workflows/{workflow['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    inspection_id = _make_inspection(tenant_id)

    res = client.post(
        "/api/forge/workflow-execution/simulate",
        json={"workflow_id": workflow["id"], "inspection_id": inspection_id, "expected_outcome": "completed"},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["expected_outcome"] == "completed"
    assert body["actual_outcome"] == "completed"
    assert body["outcome_matched"] is True
    assert body["decision_path"]

    history = client.get(f"/api/forge/workflow-history/{workflow['id']}", headers=_headers(AUTH_ADMIN, tenant_id))
    assert history.status_code == 200
    assert len(history.json()["simulations"]) == 1
    assert len(history.json()["executions"]) == 0  # simulations are excluded from the real-execution list


# ---------------------------------------------------------------------------
# Version rollback
# ---------------------------------------------------------------------------


def test_version_rollback_restores_prior_version_as_current():
    tenant_id = uid("hospital")
    v1 = _create_workflow(tenant_id)
    publish1 = client.post(f"/api/forge/workflows/{v1['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id)).json()
    assert publish1["is_current"] is True

    revise = client.post(
        f"/api/forge/workflows/{v1['id']}/revise",
        json={"nodes": _SIMPLE_WORKFLOW_NODES + [{"key": "extra", "type": "knowledge_capture", "x": 800, "y": 0}]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert revise.status_code == 200, revise.text
    v2 = revise.json()
    assert v2["version"] == 2
    assert v2["id"] != v1["id"]
    client.post(f"/api/forge/workflows/{v2['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))

    versions = client.get(f"/api/forge/workflows/{v1['id']}/versions", headers=_headers(AUTH_VIEWER, tenant_id))
    assert len(versions.json()["versions"]) == 2

    rollback = client.post(
        f"/api/forge/workflows/{v2['id']}/rollback", json={"target_version_id": v1["id"]}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["id"] == v1["id"]
    assert rollback.json()["is_current"] is True

    v2_after = client.get(f"/api/forge/workflows/{v2['id']}", headers=_headers(AUTH_VIEWER, tenant_id)).json()
    assert v2_after["is_current"] is False
    assert v2_after["status"] == "archived"


def test_rollback_rejects_version_from_a_different_workflow():
    tenant_id = uid("hospital")
    wf_a = _create_workflow(tenant_id)
    client.post(f"/api/forge/workflows/{wf_a['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    wf_b = _create_workflow(tenant_id)
    client.post(f"/api/forge/workflows/{wf_b['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))

    res = client.post(
        f"/api/forge/workflows/{wf_a['id']}/rollback", json={"target_version_id": wf_b["id"]}, headers=_headers(AUTH_ADMIN, tenant_id),
    )
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# Approval routing
# ---------------------------------------------------------------------------


def test_approval_chain_advances_through_steps_and_completes():
    tenant_id = uid("hospital")
    chain = client.post(
        "/api/forge/approval-chains", json={"name": "Standard", "steps": ["technician", "supervisor", "manager"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    ).json()

    workflow = _create_workflow(tenant_id)
    client.post(f"/api/forge/workflows/{workflow['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))

    from app.services import forge_approval_service
    db = SessionLocal()
    try:
        instance = forge_approval_service.start_instance(db, tenant_id, chain["id"])
    finally:
        db.close()

    step1 = client.post(
        f"/api/forge/approval-instances/{instance['id']}/decide",
        json={"decided_role": "technician", "decision": "approved"}, headers=_headers(AUTH_MGR, tenant_id),
    )
    assert step1.status_code == 200, step1.text
    assert step1.json()["status"] == "pending"
    assert step1.json()["current_step_index"] == 1

    step2 = client.post(
        f"/api/forge/approval-instances/{instance['id']}/decide",
        json={"decided_role": "supervisor", "decision": "approved"}, headers=_headers(AUTH_MGR, tenant_id),
    )
    assert step2.json()["current_step_index"] == 2

    step3 = client.post(
        f"/api/forge/approval-instances/{instance['id']}/decide",
        json={"decided_role": "manager", "decision": "approved"}, headers=_headers(AUTH_MGR, tenant_id),
    )
    assert step3.status_code == 200
    assert step3.json()["status"] == "approved"
    assert len(step3.json()["decisions"]) == 3


def test_approval_rejection_stops_the_chain_immediately():
    tenant_id = uid("hospital")
    chain = client.post(
        "/api/forge/approval-chains", json={"name": "Standard", "steps": ["technician", "supervisor"]},
        headers=_headers(AUTH_ADMIN, tenant_id),
    ).json()

    from app.services import forge_approval_service
    db = SessionLocal()
    try:
        instance = forge_approval_service.start_instance(db, tenant_id, chain["id"])
    finally:
        db.close()

    reject = client.post(
        f"/api/forge/approval-instances/{instance['id']}/decide",
        json={"decided_role": "technician", "decision": "rejected"}, headers=_headers(AUTH_MGR, tenant_id),
    )
    assert reject.json()["status"] == "rejected"

    already_decided = client.post(
        f"/api/forge/approval-instances/{instance['id']}/decide",
        json={"decided_role": "supervisor", "decision": "approved"}, headers=_headers(AUTH_MGR, tenant_id),
    )
    assert already_decided.status_code == 409


# ---------------------------------------------------------------------------
# API permissions
# ---------------------------------------------------------------------------


def test_create_workflow_requires_leadership_role():
    tenant_id = uid("hospital")
    res = client.post(
        "/api/forge/workflows", json={"name": "x", "nodes": _SIMPLE_WORKFLOW_NODES, "edges": []},
        headers=_headers(AUTH_VIEWER, tenant_id),
    )
    assert res.status_code == 403


def test_get_workflows_permitted_for_viewer():
    tenant_id = uid("hospital")
    res = client.get("/api/forge/workflows", headers=_headers(AUTH_VIEWER, tenant_id))
    assert res.status_code == 200


def test_approve_share_requires_admin_role():
    tenant_id = uid("hospital")
    workflow = _create_workflow(tenant_id)
    client.post(f"/api/forge/workflows/{workflow['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    client.post(f"/api/forge/workflows/{workflow['id']}/share", headers=_headers(AUTH_ADMIN, tenant_id))

    denied = client.post(f"/api/forge/workflows/{workflow['id']}/approve-share", headers=_headers(AUTH_MGR, tenant_id))
    assert denied.status_code == 403

    allowed = client.post(f"/api/forge/workflows/{workflow['id']}/approve-share", headers=_headers(AUTH_ADMIN, tenant_id))
    assert allowed.status_code == 200


# ---------------------------------------------------------------------------
# Marketplace import
# ---------------------------------------------------------------------------


def test_import_template_clones_into_tenant_as_draft():
    tenant_id = uid("hospital")
    client.get("/api/forge/workflow-templates", headers=AUTH_VIEWER)  # ensure seeded

    res = client.post("/api/forge/workflow-templates/rigid_scope/import", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 200, res.text
    imported = res.json()
    assert imported["tenant_id"] == tenant_id
    assert imported["status"] == "draft"
    assert imported["marketplace_status"] == "private"


def test_share_requires_published_workflow():
    tenant_id = uid("hospital")
    workflow = _create_workflow(tenant_id)  # still draft, never published
    res = client.post(f"/api/forge/workflows/{workflow['id']}/share", headers=_headers(AUTH_ADMIN, tenant_id))
    assert res.status_code == 409


def test_marketplace_lists_only_approved_published_shares():
    tenant_id = uid("hospital")
    workflow = _create_workflow(tenant_id)
    client.post(f"/api/forge/workflows/{workflow['id']}/publish", headers=_headers(AUTH_ADMIN, tenant_id))
    client.post(f"/api/forge/workflows/{workflow['id']}/share", headers=_headers(AUTH_ADMIN, tenant_id))

    before = client.get("/api/forge/marketplace", headers=AUTH_VIEWER)
    assert workflow["id"] not in {w["id"] for w in before.json()["listings"]}

    client.post(f"/api/forge/workflows/{workflow['id']}/approve-share", headers=_headers(AUTH_ADMIN, tenant_id))
    after = client.get("/api/forge/marketplace", headers=AUTH_VIEWER)
    assert workflow["id"] in {w["id"] for w in after.json()["listings"]}


def test_export_workflow_returns_portable_json():
    tenant_id = uid("hospital")
    workflow = _create_workflow(tenant_id)
    res = client.get(f"/api/forge/workflows/{workflow['id']}/export", headers=_headers(AUTH_VIEWER, tenant_id))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["nodes"] == _SIMPLE_WORKFLOW_NODES
    assert "exported_at" in body
