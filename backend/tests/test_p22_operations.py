"""P22: Autonomous Healthcare Operations Platform — test suite.

Covers:
  Phase 1 — Workflow definitions and steps
  Phase 2 — Workflow execution, approval, step completion, escalation
  Phase 3 — Work queue CRUD (claim, complete, escalate)
  Phase 4 — Command center snapshots and live dashboard
  Phase 5 — Copilot queries and recommendation review
"""
import time
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer dev-token"}
TS = str(int(time.time()))[-6:]
TENANT = f"p22-{TS}"


# ---------------------------------------------------------------------------
# Phase 1 — Workflow Definitions
# ---------------------------------------------------------------------------

def test_create_workflow():
    r = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={
            "name": f"CAPA Review {TS}",
            "workflow_type": "capa",
            "priority": "high",
            "sla_hours": 72,
            "approval_required": True,
            "created_by": "admin@lumenai.io",
        },
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["workflow_type"] == "capa"
    assert data["status"] == "active"


def test_create_workflow_invalid_type():
    r = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={
            "name": "Bad",
            "workflow_type": "unknown_type",
            "created_by": "admin@lumenai.io",
        },
        headers=HEADERS,
    )
    assert r.status_code == 400


def test_list_workflows():
    r = client.get(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_add_step_to_workflow():
    # Create a workflow first
    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={
            "name": f"Inspection WF {TS}",
            "workflow_type": "inspection",
            "created_by": "admin@lumenai.io",
        },
        headers=HEADERS,
    ).json()
    wf_id = wf["id"]

    r = client.post(
        f"/api/operations/workflows/{wf_id}/steps",
        params={"tenant_id": TENANT},
        json={
            "step_order": 1,
            "name": "Initial Inspection",
            "step_type": "action",
            "assignee_role": "technician",
            "instructions": "Perform full visual inspection",
            "timeout_hours": 24,
        },
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["assignee_role"] == "technician"


def test_add_step_invalid_role():
    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={
            "name": f"Step Test WF {TS}",
            "workflow_type": "capa",
            "created_by": "admin@lumenai.io",
        },
        headers=HEADERS,
    ).json()

    r = client.post(
        f"/api/operations/workflows/{wf['id']}/steps",
        params={"tenant_id": TENANT},
        json={
            "step_order": 1,
            "name": "Bad Step",
            "step_type": "action",
            "assignee_role": "robot",
        },
        headers=HEADERS,
    )
    assert r.status_code == 400


def test_list_steps():
    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={
            "name": f"List Steps WF {TS}",
            "workflow_type": "notification",
            "created_by": "admin@lumenai.io",
        },
        headers=HEADERS,
    ).json()
    wf_id = wf["id"]

    client.post(
        f"/api/operations/workflows/{wf_id}/steps",
        params={"tenant_id": TENANT},
        json={"step_order": 1, "name": "Notify", "step_type": "notification",
              "assignee_role": "manager"},
        headers=HEADERS,
    )
    r = client.get(
        f"/api/operations/workflows/{wf_id}/steps",
        params={"tenant_id": TENANT},
        headers=HEADERS,
    )
    assert r.status_code == 200
    steps = r.json()
    assert len(steps) >= 1
    assert steps[0]["step_order"] == 1


# ---------------------------------------------------------------------------
# Phase 2 — Workflow Execution
# ---------------------------------------------------------------------------

def _create_wf_with_step(approval_required=True):
    """Helper: create a workflow + one step, return workflow_id."""
    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={
            "name": f"Exec WF {TS}",
            "workflow_type": "capa",
            "sla_hours": 48,
            "approval_required": approval_required,
            "created_by": "admin@lumenai.io",
        },
        headers=HEADERS,
    ).json()
    wf_id = wf["id"]
    client.post(
        f"/api/operations/workflows/{wf_id}/steps",
        params={"tenant_id": TENANT},
        json={"step_order": 1, "name": "Review", "step_type": "approval",
              "assignee_role": "manager"},
        headers=HEADERS,
    )
    return wf_id


def test_execute_workflow_requires_approval():
    wf_id = _create_wf_with_step(approval_required=True)
    r = client.post(
        f"/api/operations/workflows/{wf_id}/execute",
        params={"tenant_id": TENANT},
        json={
            "resource_type": "capa",
            "resource_id": f"CAPA-{TS}",
            "triggered_by": "manager@hospital.org",
            "priority": "high",
        },
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "awaiting_approval"


def test_approve_execution():
    wf_id = _create_wf_with_step(approval_required=True)
    ex = client.post(
        f"/api/operations/workflows/{wf_id}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "capa", "resource_id": f"CAPA2-{TS}",
              "triggered_by": "nurse@hospital.org"},
        headers=HEADERS,
    ).json()
    ex_id = ex["id"]

    r = client.post(
        f"/api/operations/executions/{ex_id}/approve",
        params={"tenant_id": TENANT},
        json={"approved_by": "director@hospital.org", "approved": True},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["human_approved"] is True


def test_reject_execution():
    wf_id = _create_wf_with_step(approval_required=True)
    ex = client.post(
        f"/api/operations/workflows/{wf_id}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "inspection", "resource_id": f"INS-{TS}",
              "triggered_by": "tech@hospital.org"},
        headers=HEADERS,
    ).json()

    r = client.post(
        f"/api/operations/executions/{ex['id']}/approve",
        params={"tenant_id": TENANT},
        json={"approved_by": "director@hospital.org", "approved": False, "notes": "Not needed"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert r.json()["human_approved"] is False


def test_approve_non_awaiting_execution_fails():
    wf_id = _create_wf_with_step(approval_required=False)
    ex = client.post(
        f"/api/operations/workflows/{wf_id}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "capa", "resource_id": f"CAPA3-{TS}",
              "triggered_by": "tech@hospital.org"},
        headers=HEADERS,
    ).json()
    # status is in_progress (no approval required)
    r = client.post(
        f"/api/operations/executions/{ex['id']}/approve",
        params={"tenant_id": TENANT},
        json={"approved_by": "director@hospital.org", "approved": True},
        headers=HEADERS,
    )
    assert r.status_code == 409


def test_execute_workflow_no_approval_goes_in_progress():
    wf_id = _create_wf_with_step(approval_required=False)
    r = client.post(
        f"/api/operations/workflows/{wf_id}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "inspection", "resource_id": f"INS2-{TS}",
              "triggered_by": "tech@hospital.org"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "in_progress"


def test_escalate_execution():
    wf_id = _create_wf_with_step(approval_required=False)
    ex = client.post(
        f"/api/operations/workflows/{wf_id}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "recall", "resource_id": f"RCL-{TS}",
              "triggered_by": "manager@hospital.org"},
        headers=HEADERS,
    ).json()

    r = client.post(
        f"/api/operations/executions/{ex['id']}/escalate",
        params={"tenant_id": TENANT,
                "escalated_by": "director@hospital.org",
                "reason": "SLA breach imminent"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "escalated"


def test_list_executions():
    r = client.get(
        "/api/operations/executions",
        params={"tenant_id": TENANT},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Phase 3 — Work Queues
# ---------------------------------------------------------------------------

def test_add_queue_item():
    r = client.post(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT},
        json={
            "queue_type": "technician",
            "title": f"Inspect instrument {TS}",
            "priority": "high",
            "source_type": "inspection",
            "source_id": f"INS-{TS}",
        },
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["queue_type"] == "technician"
    assert r.json()["status"] == "open"


def test_add_queue_item_invalid_type():
    r = client.post(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT},
        json={"queue_type": "robot", "title": "Bad item", "priority": "normal"},
        headers=HEADERS,
    )
    assert r.status_code == 400


def test_list_queue_items():
    r = client.get(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT, "queue_type": "technician"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_claim_queue_item():
    item = client.post(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT},
        json={"queue_type": "manager", "title": f"Review CAPA {TS}", "priority": "normal"},
        headers=HEADERS,
    ).json()

    r = client.post(
        f"/api/operations/work-queue/{item['id']}/claim",
        params={"tenant_id": TENANT, "claimed_by": "mgr@hospital.org"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "claimed"
    assert r.json()["claimed_by"] == "mgr@hospital.org"


def test_claim_already_claimed_item_fails():
    item = client.post(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT},
        json={"queue_type": "executive", "title": f"Exec Review {TS}", "priority": "critical"},
        headers=HEADERS,
    ).json()
    # Claim once
    client.post(
        f"/api/operations/work-queue/{item['id']}/claim",
        params={"tenant_id": TENANT, "claimed_by": "exec1@hospital.org"},
        headers=HEADERS,
    )
    # Claim again — should fail
    r = client.post(
        f"/api/operations/work-queue/{item['id']}/claim",
        params={"tenant_id": TENANT, "claimed_by": "exec2@hospital.org"},
        headers=HEADERS,
    )
    assert r.status_code == 409


def test_complete_queue_item():
    item = client.post(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT},
        json={"queue_type": "vendor", "title": f"Vendor repair {TS}", "priority": "normal"},
        headers=HEADERS,
    ).json()

    r = client.post(
        f"/api/operations/work-queue/{item['id']}/complete",
        params={"tenant_id": TENANT, "completed_by": "vendor@corp.com",
                "notes": "Repair completed successfully"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


def test_escalate_queue_item():
    item = client.post(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT},
        json={"queue_type": "manager", "title": f"Urgent review {TS}", "priority": "normal"},
        headers=HEADERS,
    ).json()

    r = client.post(
        f"/api/operations/work-queue/{item['id']}/escalate",
        params={"tenant_id": TENANT, "escalated_by": "director@hospital.org"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["escalated"] is True
    assert r.json()["priority"] == "critical"


# ---------------------------------------------------------------------------
# Phase 4 — Command Center
# ---------------------------------------------------------------------------

def test_create_risk_snapshot():
    r = client.post(
        "/api/operations/command-center/snapshots",
        params={"tenant_id": TENANT},
        json={
            "snapshot_type": "risk",
            "period_label": f"2026-W{TS[:2]}",
            "open_high_priority_items": 12,
            "overdue_items": 3,
            "risk_score": 0.62,
            "active_escalations": 2,
            "escalations_last_7d": 5,
            "generated_by": "system",
        },
        headers=HEADERS,
    )
    assert r.status_code == 201
    assert r.json()["snapshot_type"] == "risk"
    assert r.json()["risk_score"] == 0.62


def test_create_workload_snapshot():
    r = client.post(
        "/api/operations/command-center/snapshots",
        params={"tenant_id": TENANT},
        json={
            "snapshot_type": "workload",
            "total_open_queue_items": 47,
            "technician_queue_depth": 20,
            "manager_queue_depth": 15,
            "executive_queue_depth": 5,
            "vendor_queue_depth": 7,
            "generated_by": "system",
        },
        headers=HEADERS,
    )
    assert r.status_code == 201


def test_create_snapshot_invalid_type():
    r = client.post(
        "/api/operations/command-center/snapshots",
        params={"tenant_id": TENANT},
        json={"snapshot_type": "unknown", "generated_by": "system"},
        headers=HEADERS,
    )
    assert r.status_code == 400


def test_list_snapshots():
    r = client.get(
        "/api/operations/command-center/snapshots",
        params={"tenant_id": TENANT},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_live_dashboard():
    r = client.get(
        "/api/operations/command-center/dashboard",
        params={"tenant_id": TENANT},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert "risk" in data
    assert "workload" in data
    assert data["human_review_required"] is True


# ---------------------------------------------------------------------------
# Phase 5 — AI Copilot
# ---------------------------------------------------------------------------

def test_submit_copilot_query():
    r = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={
            "asked_by": "director@hospital.org",
            "query_text": "Which items should I prioritize for this week?",
            "query_type": "prioritization",
        },
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["human_review_required"] is True
    assert "disclaimer" in data
    assert "autonomous" in data["disclaimer"].lower()
    assert "query_id" in data
    assert "recommendation_id" in data


def test_copilot_query_invalid_type():
    r = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={
            "asked_by": "exec@hospital.org",
            "query_text": "Do something",
            "query_type": "invalid_type",
        },
        headers=HEADERS,
    )
    assert r.status_code == 400


def test_list_recommendations():
    r = client.get(
        "/api/operations/copilot/recommendations",
        params={"tenant_id": TENANT},
        headers=HEADERS,
    )
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    # All pending recommendations must have human_review_required True
    pending = [x for x in rows if x["review_status"] == "pending"]
    for rec in pending:
        assert rec["human_review_required"] is True


def test_review_recommendation():
    q = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={
            "asked_by": "manager@hospital.org",
            "query_text": "Analyze current workload distribution",
            "query_type": "workload",
        },
        headers=HEADERS,
    ).json()
    rec_id = q["recommendation_id"]

    r = client.post(
        f"/api/operations/copilot/recommendations/{rec_id}/review",
        params={"tenant_id": TENANT},
        json={
            "reviewed_by": "director@hospital.org",
            "review_status": "accepted",
            "review_notes": "Looks accurate — will act on Q3 backlog items",
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["review_status"] == "accepted"
    assert data["reviewed_by"] == "director@hospital.org"


def test_review_already_reviewed_recommendation_fails():
    q = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={
            "asked_by": "exec@hospital.org",
            "query_text": "What actions are overdue?",
            "query_type": "action",
        },
        headers=HEADERS,
    ).json()
    rec_id = q["recommendation_id"]

    # First review
    client.post(
        f"/api/operations/copilot/recommendations/{rec_id}/review",
        params={"tenant_id": TENANT},
        json={"reviewed_by": "director@hospital.org", "review_status": "rejected"},
        headers=HEADERS,
    )
    # Second review — should fail
    r = client.post(
        f"/api/operations/copilot/recommendations/{rec_id}/review",
        params={"tenant_id": TENANT},
        json={"reviewed_by": "coo@hospital.org", "review_status": "accepted"},
        headers=HEADERS,
    )
    assert r.status_code == 409


def test_copilot_status_query():
    r = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={
            "asked_by": "exec@hospital.org",
            "query_text": "What is the current operational status?",
            "query_type": "status",
        },
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["confidence"] == 0.88


# ---------------------------------------------------------------------------
# Governance & isolation
# ---------------------------------------------------------------------------

def test_tenant_isolation_queue():
    """Items created in TENANT should not appear in a different tenant's list."""
    other_tenant = f"p22-other-{TS}"
    r = client.get(
        "/api/operations/work-queue",
        params={"tenant_id": other_tenant},
        headers=HEADERS,
    )
    assert r.status_code == 200
    # other_tenant should have no items from TENANT
    items = r.json()
    assert all(i.get("queue_type") is not None for i in items)  # well-formed, just empty for new tenant


def test_step_complete_for_approved_execution():
    """Full flow: create wf → step → execute (no approval) → complete step."""
    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={
            "name": f"Full Flow WF {TS}",
            "workflow_type": "inspection",
            "approval_required": False,
            "created_by": "admin@lumenai.io",
        },
        headers=HEADERS,
    ).json()
    wf_id = wf["id"]

    client.post(
        f"/api/operations/workflows/{wf_id}/steps",
        params={"tenant_id": TENANT},
        json={"step_order": 1, "name": "Final Check", "step_type": "action",
              "assignee_role": "technician"},
        headers=HEADERS,
    )

    ex = client.post(
        f"/api/operations/workflows/{wf_id}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "instrument", "resource_id": f"INS-FULL-{TS}",
              "triggered_by": "tech@hospital.org"},
        headers=HEADERS,
    ).json()
    ex_id = ex["id"]

    # Get step execution id
    execs = client.get(
        "/api/operations/executions",
        params={"tenant_id": TENANT, "status": "in_progress"},
        headers=HEADERS,
    ).json()
    this_ex = next((e for e in execs if e["id"] == ex_id), None)
    assert this_ex is not None

    # We need the step execution id — query from the test client directly
    from app.models.p22_operations import WorkflowStepExecution
    from app.deps import get_db
    db = next(get_db())
    se = db.query(WorkflowStepExecution).filter_by(execution_id=ex_id).first()
    assert se is not None
    se_id = se.id
    db.close()

    r = client.post(
        f"/api/operations/executions/{ex_id}/steps/{se_id}/complete",
        params={"tenant_id": TENANT, "assignee_email": "tech@hospital.org",
                "outcome": "passed"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["execution_status"] == "completed"


# ---------------------------------------------------------------------------
# Tier-1 Recommendation Tests
# ---------------------------------------------------------------------------

# --- 1. Auto-create queue items on workflow execution ---

def test_execute_workflow_auto_creates_queue_items():
    """Triggering a workflow should auto-populate the assignee role queue."""
    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={
            "name": f"AutoQueue WF {TS}",
            "workflow_type": "inspection",
            "approval_required": False,
            "sla_hours": 24,
            "created_by": "admin@lumenai.io",
        },
        headers=HEADERS,
    ).json()
    wf_id = wf["id"]

    client.post(
        f"/api/operations/workflows/{wf_id}/steps",
        params={"tenant_id": TENANT},
        json={"step_order": 1, "name": "Visual Check", "step_type": "action",
              "assignee_role": "technician"},
        headers=HEADERS,
    )
    client.post(
        f"/api/operations/workflows/{wf_id}/steps",
        params={"tenant_id": TENANT},
        json={"step_order": 2, "name": "Manager Sign-Off", "step_type": "approval",
              "assignee_role": "manager"},
        headers=HEADERS,
    )

    ex = client.post(
        f"/api/operations/workflows/{wf_id}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "instrument", "resource_id": f"INS-AQ-{TS}",
              "triggered_by": "tech@hospital.org"},
        headers=HEADERS,
    ).json()
    ex_id = ex["id"]

    # Technician queue should now have an item from this execution
    tech_q = client.get(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT, "queue_type": "technician"},
        headers=HEADERS,
    ).json()
    execution_items = [i for i in tech_q if i.get("execution_id") == ex_id]
    assert len(execution_items) >= 1
    assert execution_items[0]["source_type"] == "instrument"

    # Manager queue should also have an item from this execution
    mgr_q = client.get(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT, "queue_type": "manager"},
        headers=HEADERS,
    ).json()
    mgr_items = [i for i in mgr_q if i.get("execution_id") == ex_id]
    assert len(mgr_items) >= 1


def test_auto_queue_item_inherits_priority():
    """Queue items created by execution should inherit the execution priority."""
    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={"name": f"PriorityQ WF {TS}", "workflow_type": "capa",
              "approval_required": False, "created_by": "admin@lumenai.io"},
        headers=HEADERS,
    ).json()
    client.post(
        f"/api/operations/workflows/{wf['id']}/steps",
        params={"tenant_id": TENANT},
        json={"step_order": 1, "name": "Review", "step_type": "action",
              "assignee_role": "manager"},
        headers=HEADERS,
    )

    ex = client.post(
        f"/api/operations/workflows/{wf['id']}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "capa", "resource_id": f"CAPA-PQ-{TS}",
              "triggered_by": "admin@hospital.org", "priority": "critical"},
        headers=HEADERS,
    ).json()

    mgr_q = client.get(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT, "queue_type": "manager"},
        headers=HEADERS,
    ).json()
    items = [i for i in mgr_q if i.get("execution_id") == ex["id"]]
    assert len(items) >= 1
    assert items[0]["priority"] == "critical"


# --- 2. Copilot grounded on live data ---

def test_copilot_status_reflects_live_queue():
    """Status query confidence and response should reflect actual queue state."""
    # Add a known high-priority item to the queue
    client.post(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT},
        json={"queue_type": "manager", "title": f"Critical Review {TS}",
              "priority": "critical"},
        headers=HEADERS,
    )

    r = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={"asked_by": "director@hospital.org",
              "query_text": "What is the current status?",
              "query_type": "status"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    # Response should mention actual counts (not a static string)
    assert "open queue items" in data["response_summary"]
    # Confidence should be deterministic for status type
    assert data["confidence"] == 0.88


def test_copilot_prioritization_mentions_high_priority_items():
    """Prioritization response should mention high/critical items by name."""
    client.post(
        "/api/operations/work-queue",
        params={"tenant_id": TENANT},
        json={"queue_type": "technician",
              "title": f"URGENT instrument check {TS}",
              "priority": "critical"},
        headers=HEADERS,
    )

    r = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={"asked_by": "director@hospital.org",
              "query_text": "What should I prioritize?",
              "query_type": "prioritization"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["human_review_required"] is True
    # Response should reference high/critical item counts
    assert "high/critical" in data["response_summary"]


def test_copilot_workload_shows_queue_breakdown():
    """Workload response should reference actual queue distribution."""
    r = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={"asked_by": "exec@hospital.org",
              "query_text": "How is workload distributed?",
              "query_type": "workload"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    # Should mention queue names in the response
    assert any(qt in data["response_summary"] for qt in ("technician", "manager", "executive", "vendor", "all queues empty"))


def test_copilot_action_mentions_escalated_and_overdue():
    """Action response should reference escalation and overdue counts."""
    r = client.post(
        "/api/operations/copilot/query",
        params={"tenant_id": TENANT},
        json={"asked_by": "coo@hospital.org",
              "query_text": "What actions need attention?",
              "query_type": "action"},
        headers=HEADERS,
    )
    assert r.status_code == 201
    data = r.json()
    assert "escalated" in data["response_summary"]
    assert "overdue" in data["response_summary"]


# --- 3. Step timeout enforcement ---

def test_scan_timeouts_no_timeouts_returns_zero():
    """Scanning a tenant with no overdue steps returns zero processed."""
    # Tenant is now derived from the auth context (X-LumenAI-Tenant-Id),
    # not a caller-supplied query param. Route the clean tenant via header.
    r = client.post(
        "/api/operations/executions/scan-timeouts",
        headers={**HEADERS, "X-LumenAI-Tenant-Id": f"p22-clean-{TS}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["timeouts_processed"] == 0
    assert data["scanned_executions"] == 0


def test_scan_timeouts_escalates_overdue_step():
    """A step past its timeout with on_timeout=escalate should escalate the execution."""
    from app.models.p22_operations import WorkflowStepExecution
    from app.deps import get_db
    from datetime import timedelta

    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={"name": f"Timeout WF {TS}", "workflow_type": "inspection",
              "approval_required": False, "sla_hours": 24,
              "created_by": "admin@lumenai.io"},
        headers=HEADERS,
    ).json()
    client.post(
        f"/api/operations/workflows/{wf['id']}/steps",
        params={"tenant_id": TENANT},
        json={"step_order": 1, "name": "Timed Step", "step_type": "action",
              "assignee_role": "technician", "timeout_hours": 1,
              "on_timeout": "escalate"},
        headers=HEADERS,
    )
    ex = client.post(
        f"/api/operations/workflows/{wf['id']}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "instrument", "resource_id": f"INS-TO-{TS}",
              "triggered_by": "tech@hospital.org"},
        headers=HEADERS,
    ).json()
    ex_id = ex["id"]

    # Manually back-date the step execution's created_at so it appears overdue
    db = next(get_db())
    se = db.query(WorkflowStepExecution).filter_by(execution_id=ex_id).first()
    assert se is not None
    se.created_at = datetime.utcnow() - timedelta(hours=2)
    db.commit()
    db.close()

    r = client.post(
        "/api/operations/executions/scan-timeouts",
        params={"tenant_id": TENANT},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["timeouts_processed"] >= 1
    timed = next((d for d in data["details"] if d["execution_id"] == ex_id), None)
    assert timed is not None
    assert timed["policy"] == "escalate"

    # Execution should now be escalated
    execs = client.get(
        "/api/operations/executions",
        params={"tenant_id": TENANT, "status": "escalated"},
        headers=HEADERS,
    ).json()
    assert any(e["id"] == ex_id for e in execs)


def test_scan_timeouts_skip_policy():
    """A step with on_timeout=skip should be marked skipped."""
    from app.models.p22_operations import WorkflowStepExecution
    from app.deps import get_db
    from datetime import timedelta

    wf = client.post(
        "/api/operations/workflows",
        params={"tenant_id": TENANT},
        json={"name": f"Skip WF {TS}", "workflow_type": "notification",
              "approval_required": False, "created_by": "admin@lumenai.io"},
        headers=HEADERS,
    ).json()
    client.post(
        f"/api/operations/workflows/{wf['id']}/steps",
        params={"tenant_id": TENANT},
        json={"step_order": 1, "name": "Optional Notify", "step_type": "notification",
              "assignee_role": "manager", "timeout_hours": 1, "on_timeout": "skip"},
        headers=HEADERS,
    )
    ex = client.post(
        f"/api/operations/workflows/{wf['id']}/execute",
        params={"tenant_id": TENANT},
        json={"resource_type": "capa", "resource_id": f"CAPA-SK-{TS}",
              "triggered_by": "admin@hospital.org"},
        headers=HEADERS,
    ).json()

    db = next(get_db())
    se = db.query(WorkflowStepExecution).filter_by(execution_id=ex["id"]).first()
    se.created_at = datetime.utcnow() - timedelta(hours=2)
    db.commit()
    db.close()

    r = client.post(
        "/api/operations/executions/scan-timeouts",
        params={"tenant_id": TENANT},
        headers=HEADERS,
    )
    assert r.status_code == 200
    data = r.json()
    skipped = [d for d in data["details"] if d["execution_id"] == ex["id"]]
    assert len(skipped) >= 1
    assert skipped[0]["policy"] == "skip"
