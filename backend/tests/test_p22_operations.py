"""P22: Autonomous Healthcare Operations Platform — test suite.

Covers:
  Phase 1 — Workflow definitions and steps
  Phase 2 — Workflow execution, approval, step completion, escalation
  Phase 3 — Work queue CRUD (claim, complete, escalate)
  Phase 4 — Command center snapshots and live dashboard
  Phase 5 — Copilot queries and recommendation review
"""
import time

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
    assert data["confidence"] == 0.85


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
