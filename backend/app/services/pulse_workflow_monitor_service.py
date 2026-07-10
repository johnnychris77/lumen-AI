"""v4.2 — Project Pulse, Section 7: Live Workflow Monitoring.

Composes Forge's existing `WorkflowExecution`/`WorkflowApprovalInstance`
(`app/models/workflow_forge.py`, `forge_execution_service.py`,
`forge_approval_service.py`) rather than a parallel execution-tracking
table. "Current stage"/"waiting state"/"blocking rule"/"responsible
user"/"next step" are all *derived* from an execution's real
`decision_path`/`execution_log` and any linked approval instance — none
of these are stored as new columns on `WorkflowExecution` itself.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import forge_approval_service, forge_execution_service, forge_workflow_service


def _next_step(workflow: dict, current_node_key: str | None) -> str | None:
    if current_node_key is None:
        return None
    edge = next((e for e in workflow["edges"] if e.get("from") == current_node_key), None)
    return edge["to"] if edge else None


def monitor_execution(db: Session, execution_id: int) -> dict | None:
    execution = forge_execution_service.get_execution(db, execution_id)
    if execution is None:
        return None
    workflow = forge_workflow_service.get_workflow(db, execution["workflow_id"])

    decision_path = execution["decision_path"]
    current_stage = decision_path[-1] if decision_path else None
    is_running = execution["status"] == "running"
    next_step = _next_step(workflow, current_stage) if is_running and workflow else None

    waiting_state = None
    blocking_rule = None
    responsible_user = None
    last_log = execution["execution_log"][-1] if execution["execution_log"] else None
    if last_log:
        if last_log.get("node_type") == "supervisor_review" and last_log.get("awaiting_review"):
            waiting_state = "awaiting_supervisor_review"
            responsible_user = "supervisor"
        elif last_log.get("node_type") == "approval" and last_log.get("approval_instance_id"):
            instance = forge_approval_service.get_instance(db, last_log["approval_instance_id"])
            if instance and instance["status"] == "pending":
                waiting_state = "awaiting_approval"
                chain = next(
                    (c for c in forge_approval_service.list_chains(db, execution["tenant_id"]) if c["id"] == instance["chain_id"]), None,
                )
                if chain and instance["current_step_index"] < len(chain["steps"]):
                    responsible_user = chain["steps"][instance["current_step_index"]]
        elif last_log.get("rule_result") and not last_log["rule_result"].get("matched"):
            blocking_rule = last_log["rule_result"].get("rule_ref")

    return {
        "execution_id": execution["id"], "workflow_id": execution["workflow_id"], "workflow_name": workflow["name"] if workflow else None,
        "status": execution["status"], "current_stage": current_stage, "next_step": next_step,
        "waiting_state": waiting_state, "blocking_rule": blocking_rule, "responsible_user": responsible_user,
        "execution_time_ms": execution["execution_time_ms"], "started_at": execution["started_at"],
        "completed_at": execution["completed_at"], "decision_path": decision_path,
    }


def active_workflows(db: Session, tenant_id: str) -> list[dict]:
    executions = forge_execution_service.list_executions(db, tenant_id, is_simulation=False)
    running = [e for e in executions if e["status"] == "running"]
    return [monitor_execution(db, e["id"]) for e in running]
