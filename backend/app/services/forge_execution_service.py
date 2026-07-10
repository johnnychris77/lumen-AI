"""v4.1 — Project Forge, Section 1 (execution) & Section 11 (/workflow-execution).

Walks a published `WorkflowDefinition`'s node graph from its `start` node
to an `end` node, dispatching each node to the correct existing engine:
`forge_rule_engine` for Conditional Branch, `forge_ai_node_service` for
every AI Decision Node, `forge_action_service` for Notification/
Knowledge Capture/Export Report, `forge_approval_service` for Approval
nodes, and `or_connect.RepairRequest` directly for Repair Referral (the
same model OR Connect's own repair workflow already uses). Every step
taken and every millisecond elapsed is real — this module records what
actually happened, it never fabricates a decision path.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import REPAIR_PENDING, RepairRequest
from app.models.workflow_forge import (
    EXECUTION_COMPLETED,
    EXECUTION_FAILED,
    NODE_AI_ANALYSIS,
    NODE_ANATOMY_CHECK,
    NODE_APPROVAL,
    NODE_CLINICAL_REASONING,
    NODE_CONDITIONAL_BRANCH,
    NODE_COVERAGE_CHECK,
    NODE_DIGITAL_TWIN_UPDATE,
    NODE_END,
    NODE_EXPORT_REPORT,
    NODE_KNOWLEDGE_CAPTURE,
    NODE_KNOWLEDGE_LOOKUP,
    NODE_NOTIFICATION,
    NODE_REPAIR_REFERRAL,
    NODE_START,
    NODE_SUPERVISOR_REVIEW,
    WorkflowExecution,
)
from app.services import forge_action_service, forge_ai_node_service, forge_approval_service, forge_rule_engine
from app.services.forge_workflow_service import get_workflow

_NODE_TO_AI_RUN_TYPE = {
    NODE_AI_ANALYSIS: "run_recommendation_engine",
    NODE_ANATOMY_CHECK: "run_anatomy_model",
    NODE_KNOWLEDGE_LOOKUP: "run_knowledge_graph",
    NODE_CLINICAL_REASONING: "run_risk_model",
    NODE_DIGITAL_TWIN_UPDATE: "run_digital_twin_update",
}

_MAX_STEPS = 64


class UnknownWorkflowForExecutionError(Exception):
    pass


def _execution_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    result["decision_path"] = json.loads(result.pop("decision_path_json") or "[]")
    result["execution_log"] = json.loads(result.pop("execution_log_json") or "[]")
    return result


def build_context(db: Session, tenant_id: str, inspection_id: int | None) -> dict:
    """Builds the rule-evaluation context from a real Inspection row (and
    its findings) — every field is read from the actual row; a field with
    no real source simply doesn't appear in the context (and so never
    matches a rule condition referencing it), rather than being guessed."""
    context: dict = {"facility": "", "department": "", "shift": "", "time": datetime.now(timezone.utc).isoformat()}
    if inspection_id is None:
        return context

    inspection = db.query(Inspection).filter(Inspection.id == inspection_id, Inspection.tenant_id == tenant_id).first()
    if inspection is None:
        return context

    context["instrument_family"] = inspection.instrument_type
    context["manufacturer"] = inspection.vendor_name
    context["coverage_pct"] = inspection.coverage_pct
    context["confidence"] = inspection.confidence
    context["facility"] = inspection.facility_name or ""

    finding = db.query(InspectionFinding).filter(InspectionFinding.inspection_id == inspection_id).order_by(InspectionFinding.severity_index.desc()).first()
    if finding is not None:
        context["finding"] = finding.finding_type
        context["inspection_zone"] = finding.zone
        context["severity"] = finding.severity_index

    return context


def _find_node(nodes: list[dict], key: str) -> dict | None:
    return next((n for n in nodes if n.get("key") == key), None)


def _next_edge(edges: list[dict], from_key: str, *, branch: str | None = None) -> dict | None:
    candidates = [e for e in edges if e.get("from") == from_key]
    if branch is not None:
        matching = [e for e in candidates if e.get("condition") == branch]
        if matching:
            return matching[0]
    return candidates[0] if candidates else None


def execute_workflow(
    db: Session, tenant_id: str, workflow_id: int, *, inspection_id: int | None = None,
    triggered_by: str = "system", is_simulation: bool = False,
) -> dict:
    workflow = get_workflow(db, workflow_id)
    if workflow is None:
        raise UnknownWorkflowForExecutionError(f"Workflow {workflow_id} not found.")

    nodes = workflow["nodes"]
    edges = workflow["edges"]
    start_node = next((n for n in nodes if n.get("type") == NODE_START), None)
    if start_node is None:
        raise UnknownWorkflowForExecutionError(f"Workflow {workflow_id} has no start node.")

    execution = WorkflowExecution(
        tenant_id=tenant_id, workflow_id=workflow_id, inspection_id=inspection_id,
        is_simulation=is_simulation, triggered_by=triggered_by,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    context = build_context(db, tenant_id, inspection_id)
    decision_path: list[str] = []
    execution_log: list[dict] = []
    wall_start = time.monotonic()
    current_key = start_node["key"]
    status = EXECUTION_COMPLETED
    steps = 0

    try:
        while current_key and steps < _MAX_STEPS:
            steps += 1
            node = _find_node(nodes, current_key)
            if node is None:
                break
            decision_path.append(current_key)
            node_type = node.get("type")
            detail: dict = {"node_key": current_key, "node_type": node_type}
            branch: str | None = None

            if node_type == NODE_START:
                pass
            elif node_type == NODE_END:
                execution_log.append(detail)
                break
            elif node_type in _NODE_TO_AI_RUN_TYPE:
                ai_run_type = node.get("config", {}).get("ai_run_type", _NODE_TO_AI_RUN_TYPE[node_type])
                result = forge_ai_node_service.run_ai_node(db, tenant_id, ai_run_type, node.get("config", {}))
                detail["result"] = result
            elif node_type == NODE_COVERAGE_CHECK:
                threshold = node.get("config", {}).get("min_coverage_pct", 80)
                coverage = context.get("coverage_pct") or 0
                passed = coverage >= threshold
                detail["passed"] = passed
                branch = "true" if passed else "false"
            elif node_type == NODE_CONDITIONAL_BRANCH:
                rule_id = node.get("config", {}).get("rule_id")
                if rule_id:
                    rule_result = forge_rule_engine.evaluate_rule(db, rule_id, context)
                    detail["rule_result"] = rule_result
                    branch = "true" if rule_result["matched"] else "false"
                    for action in rule_result.get("actions", []):
                        action_result = forge_action_service.execute_action(db, tenant_id, action["type"], action.get("params", {}), actor=triggered_by)
                        detail.setdefault("actions", []).append(action_result)
                else:
                    branch = "true"
            elif node_type == NODE_SUPERVISOR_REVIEW:
                detail["awaiting_review"] = True
            elif node_type == NODE_APPROVAL:
                chain_id = node.get("config", {}).get("chain_id")
                if chain_id:
                    instance = forge_approval_service.start_instance(db, tenant_id, chain_id, execution_id=execution.id)
                    detail["approval_instance_id"] = instance["id"]
            elif node_type == NODE_NOTIFICATION:
                result = forge_action_service.execute_action(db, tenant_id, "notify_supervisor", node.get("config", {}), actor=triggered_by)
                detail["result"] = result
            elif node_type == NODE_KNOWLEDGE_CAPTURE:
                result = forge_action_service.execute_action(db, tenant_id, "create_knowledge_draft", {**node.get("config", {}), "inspection_id": inspection_id}, actor=triggered_by)
                detail["result"] = result
            elif node_type == NODE_EXPORT_REPORT:
                result = forge_action_service.execute_action(db, tenant_id, "generate_report", node.get("config", {}), actor=triggered_by)
                detail["result"] = result
            elif node_type == NODE_REPAIR_REFERRAL:
                repair = RepairRequest(
                    tenant_id=tenant_id, inspection_id=inspection_id or 0,
                    instrument_identity=node.get("config", {}).get("instrument_identity", ""),
                    vendor_name=node.get("config", {}).get("vendor_name", ""), status=REPAIR_PENDING,
                )
                db.add(repair)
                db.commit()
                db.refresh(repair)
                detail["repair_request_id"] = repair.id

            execution_log.append(detail)
            next_edge = _next_edge(edges, current_key, branch=branch)
            current_key = next_edge["to"] if next_edge else None
    except Exception as exc:
        # A failed node must still persist what happened up to the failure.
        status = EXECUTION_FAILED
        execution_log.append({"error": str(exc)})

    elapsed_ms = (time.monotonic() - wall_start) * 1000
    execution.status = status
    execution.completed_at = datetime.now(timezone.utc)
    execution.execution_time_ms = elapsed_ms
    execution.decision_path_json = json.dumps(decision_path)
    execution.execution_log_json = json.dumps(execution_log, default=str)
    execution.actual_outcome = status
    db.commit()
    db.refresh(execution)

    if not is_simulation:
        # Best-effort: publish to Nexus's event bus so Pulse's Live Event
        # Stream (v4.2) can surface it — a publish failure must never roll
        # back an already-persisted execution.
        try:
            from app.models.nexus_integration import EVENT_WORKFLOW_EXECUTED
            from app.services import nexus_event_bus_service
            nexus_event_bus_service.publish(
                db, tenant_id=tenant_id, event_type=EVENT_WORKFLOW_EXECUTED,
                payload={"workflow_id": workflow_id, "execution_id": execution.id, "status": status, "inspection_id": inspection_id},
                actor=triggered_by,
            )
        except Exception:
            pass

    return _execution_to_dict(execution)


def get_execution(db: Session, execution_id: int) -> dict | None:
    row = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
    return _execution_to_dict(row) if row else None


def list_executions(db: Session, tenant_id: str, *, workflow_id: int | None = None, is_simulation: bool | None = None) -> list[dict]:
    q = db.query(WorkflowExecution).filter(WorkflowExecution.tenant_id == tenant_id)
    if workflow_id is not None:
        q = q.filter(WorkflowExecution.workflow_id == workflow_id)
    if is_simulation is not None:
        q = q.filter(WorkflowExecution.is_simulation.is_(is_simulation))
    return [_execution_to_dict(r) for r in q.order_by(WorkflowExecution.id.desc()).all()]
