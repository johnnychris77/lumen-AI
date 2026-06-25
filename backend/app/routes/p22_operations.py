"""P22: Autonomous Healthcare Operations Platform.

Phases covered:
  1 – Operations Orchestration (workflow definitions + steps)
  2 – Workflow Automation (CAPA, inspection, escalation, notification)
  3 – Intelligent Work Queues (technician/manager/executive/vendor)
  4 – Enterprise Command Center (risk / workload / backlog / escalation snapshots)
  5 – AI Operations Copilot (NL queries + recommendations)

Governance:
  - Every mutation is audit-logged with compliance_flag=True
  - Human-in-the-loop: approval_required workflows block at awaiting_approval
  - Copilot recommendations always carry human_review_required=True
  - No autonomous external action; escalation notifies humans only
  - Tenant isolation: every query is scoped to tenant_id
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.p22_operations import (
    OperationsWorkflow,
    WorkflowStep,
    WorkflowExecution,
    WorkflowStepExecution,
    WorkQueueItem,
    OperationalRiskSnapshot,
    CopilotQuery,
    CopilotRecommendation,
)

router = APIRouter(prefix="/api/operations", tags=["operations"])

# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------

def _audit(db, action_type: str, tenant_id: str, details: dict | None = None):
    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name="Operations",
        actor_email="system",
        actor_role="admin",
        action_type=action_type,
        resource_type="operations",
        resource_id="",
        details=details or {},
        compliance_flag=True,
    )


# ---------------------------------------------------------------------------
# Validation sets
# ---------------------------------------------------------------------------

_WORKFLOW_TYPES = {"capa", "inspection", "escalation", "notification"}
_PRIORITIES = {"low", "normal", "high", "critical"}
_STEP_TYPES = {"action", "approval", "notification", "gate"}
_ASSIGNEE_ROLES = {"technician", "manager", "executive", "vendor"}
_QUEUE_TYPES = {"technician", "manager", "executive", "vendor"}
_EXEC_STATUSES = {
    "pending", "in_progress", "awaiting_approval", "escalated", "completed", "cancelled",
}
_SNAPSHOT_TYPES = {"risk", "workload", "backlog", "escalation"}
_QUERY_TYPES = {"prioritization", "workload", "action", "status"}
_REC_TYPES = {"prioritization", "workload", "action", "risk"}
_REVIEW_STATUSES = {"pending", "accepted", "rejected", "modified"}


# ---------------------------------------------------------------------------
# Phase 1 — Workflow Definitions
# ---------------------------------------------------------------------------

class WorkflowIn(BaseModel):
    name: str
    workflow_type: str
    description: Optional[str] = None
    priority: str = "normal"
    sla_hours: Optional[int] = None
    auto_assign: bool = False
    approval_required: bool = True
    created_by: str


class StepIn(BaseModel):
    step_order: int
    name: str
    step_type: str
    assignee_role: str
    instructions: Optional[str] = None
    required: bool = True
    timeout_hours: Optional[int] = None
    on_timeout: str = "escalate"


@router.post("/workflows", status_code=201,
             dependencies=[Depends(require_roles("admin", "manager"))])
def create_workflow(request: Request, body: WorkflowIn = ...,
                    db: Session = Depends(get_db)):
    if body.workflow_type not in _WORKFLOW_TYPES:
        raise HTTPException(400, f"workflow_type must be one of {_WORKFLOW_TYPES}")
    if body.priority not in _PRIORITIES:
        raise HTTPException(400, f"priority must be one of {_PRIORITIES}")
    wf = OperationsWorkflow(tenant_id=tenant_id, **body.model_dump())
    db.add(wf)
    db.commit()
    db.refresh(wf)
    _audit(db, "workflow_created", tenant_id, {"workflow_id": wf.id, "type": wf.workflow_type})
    return {"id": wf.id, "name": wf.name, "workflow_type": wf.workflow_type,
            "status": wf.status, "created_at": wf.created_at.isoformat()}


@router.get("/workflows", dependencies=[Depends(require_roles("admin", "manager", "executive"))])
def list_workflows(request: Request,
                   workflow_type: Optional[str] = Query(None),
                   db: Session = Depends(get_db)):
    q = db.query(OperationsWorkflow).filter_by(tenant_id=tenant_id, status="active")
    if workflow_type:
        q = q.filter_by(workflow_type=workflow_type)
    rows = q.order_by(OperationsWorkflow.created_at.desc()).all()
    return [{"id": r.id, "name": r.name, "workflow_type": r.workflow_type,
             "priority": r.priority, "sla_hours": r.sla_hours,
             "approval_required": r.approval_required,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/workflows/{workflow_id}/steps", status_code=201,
             dependencies=[Depends(require_roles("admin", "manager"))])
def add_step(workflow_id: int, request: Request, body: StepIn = ...,
             db: Session = Depends(get_db)):
    wf = db.query(OperationsWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(404, "Workflow not found")
    if body.step_type not in _STEP_TYPES:
        raise HTTPException(400, f"step_type must be one of {_STEP_TYPES}")
    if body.assignee_role not in _ASSIGNEE_ROLES:
        raise HTTPException(400, f"assignee_role must be one of {_ASSIGNEE_ROLES}")
    step = WorkflowStep(workflow_id=workflow_id, **body.model_dump())
    db.add(step)
    db.commit()
    db.refresh(step)
    _audit(db, "workflow_step_added", tenant_id,
           {"workflow_id": workflow_id, "step_id": step.id, "step_order": step.step_order})
    return {"id": step.id, "workflow_id": workflow_id, "step_order": step.step_order,
            "name": step.name, "assignee_role": step.assignee_role}


@router.get("/workflows/{workflow_id}/steps",
            dependencies=[Depends(require_roles("admin", "manager", "technician", "executive"))])
def list_steps(workflow_id: int, request: Request, db: Session = Depends(get_db)):
    wf = db.query(OperationsWorkflow).filter_by(id=workflow_id, tenant_id=tenant_id).first()
    if not wf:
        raise HTTPException(404, "Workflow not found")
    steps = (db.query(WorkflowStep).filter_by(workflow_id=workflow_id)
             .order_by(WorkflowStep.step_order).all())
    return [{"id": s.id, "step_order": s.step_order, "name": s.name,
             "step_type": s.step_type, "assignee_role": s.assignee_role,
             "required": s.required, "timeout_hours": s.timeout_hours} for s in steps]


# ---------------------------------------------------------------------------
# Phase 2 — Workflow Execution
# ---------------------------------------------------------------------------

class ExecutionIn(BaseModel):
    resource_type: str
    resource_id: str
    triggered_by: str
    trigger_reason: Optional[str] = None
    priority: str = "normal"


class ApprovalIn(BaseModel):
    approved_by: str
    approved: bool
    notes: Optional[str] = None


@router.post("/workflows/{workflow_id}/execute", status_code=201,
             dependencies=[Depends(require_roles("admin", "manager", "technician"))])
def execute_workflow(workflow_id: int, request: Request,
                     body: ExecutionIn = ..., db: Session = Depends(get_db)):
    wf = db.query(OperationsWorkflow).filter_by(
        id=workflow_id, tenant_id=tenant_id, status="active").first()
    if not wf:
        raise HTTPException(404, "Workflow not found or inactive")
    if body.priority not in _PRIORITIES:
        raise HTTPException(400, f"priority must be one of {_PRIORITIES}")

    sla_due = None
    if wf.sla_hours:
        sla_due = datetime.now(timezone.utc) + timedelta(hours=wf.sla_hours)

    initial_status = "awaiting_approval" if wf.approval_required else "in_progress"
    ex = WorkflowExecution(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        triggered_by=body.triggered_by,
        trigger_reason=body.trigger_reason,
        priority=body.priority,
        status=initial_status,
        sla_due_at=sla_due,
    )
    db.add(ex)
    db.flush()

    # Create step execution records + a work queue item per step
    steps = (db.query(WorkflowStep).filter_by(workflow_id=workflow_id)
             .order_by(WorkflowStep.step_order).all())
    for s in steps:
        se = WorkflowStepExecution(
            execution_id=ex.id,
            step_id=s.id,
            step_order=s.step_order,
            assignee_role=s.assignee_role,
            status="pending",
        )
        db.add(se)
        # Compute per-step due date if the workflow has an SLA
        step_due = None
        if wf.sla_hours and len(steps) > 0:
            step_due = datetime.now(timezone.utc) + timedelta(
                hours=wf.sla_hours * s.step_order / len(steps)
            )
        qi = WorkQueueItem(
            tenant_id=tenant_id,
            queue_type=s.assignee_role,           # route item to the correct role queue
            title=f"{wf.name} — {s.name}",
            description=s.instructions,
            priority=body.priority,
            source_type=body.resource_type,
            source_id=body.resource_id,
            execution_id=ex.id,
            due_at=step_due,
        )
        db.add(qi)

    db.commit()
    db.refresh(ex)
    _audit(db, "workflow_execution_started", tenant_id,
           {"execution_id": ex.id, "workflow_id": workflow_id,
            "resource_type": body.resource_type, "resource_id": body.resource_id,
            "status": initial_status})
    return {"id": ex.id, "workflow_id": workflow_id, "status": ex.status,
            "sla_due_at": sla_due.isoformat() if sla_due else None,
            "created_at": ex.created_at.isoformat()}


@router.get("/executions", dependencies=[Depends(require_roles("admin", "manager", "executive"))])
def list_executions(request: Request,
                    status: Optional[str] = Query(None),
                    db: Session = Depends(get_db)):
    q = db.query(WorkflowExecution).filter_by(tenant_id=tenant_id)
    if status:
        q = q.filter_by(status=status)
    rows = q.order_by(WorkflowExecution.created_at.desc()).limit(200).all()
    return [{"id": r.id, "workflow_id": r.workflow_id, "resource_type": r.resource_type,
             "resource_id": r.resource_id, "status": r.status, "priority": r.priority,
             "current_step": r.current_step, "sla_due_at": r.sla_due_at.isoformat() if r.sla_due_at else None,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/executions/{execution_id}/approve",
             dependencies=[Depends(require_roles("admin", "manager", "executive"))])
def approve_execution(execution_id: int, request: Request,
                      body: ApprovalIn = ..., db: Session = Depends(get_db)):
    ex = db.query(WorkflowExecution).filter_by(id=execution_id, tenant_id=tenant_id).first()
    if not ex:
        raise HTTPException(404, "Execution not found")
    if ex.status != "awaiting_approval":
        raise HTTPException(409, f"Execution is not awaiting approval (status={ex.status})")
    ex.human_approved = body.approved
    ex.approved_by = body.approved_by
    ex.approved_at = datetime.now(timezone.utc)
    ex.status = "in_progress" if body.approved else "cancelled"
    ex.outcome_notes = body.notes
    if not body.approved:
        ex.outcome = "cancelled"
        ex.completed_at = datetime.now(timezone.utc)
    db.commit()
    _audit(db, "workflow_execution_approved" if body.approved else "workflow_execution_rejected",
           tenant_id, {"execution_id": execution_id, "approved_by": body.approved_by})
    return {"id": ex.id, "status": ex.status, "human_approved": ex.human_approved}


@router.post("/executions/{execution_id}/steps/{step_id}/complete",
             dependencies=[Depends(require_roles("admin", "manager", "technician"))])
def complete_step(execution_id: int, step_id: int, request: Request,
                  assignee_email: str = Query(...), outcome: str = Query(...),
                  notes: Optional[str] = Query(None), db: Session = Depends(get_db)):
    ex = db.query(WorkflowExecution).filter_by(id=execution_id, tenant_id=tenant_id).first()
    if not ex:
        raise HTTPException(404, "Execution not found")
    if ex.status not in ("in_progress", "escalated"):
        raise HTTPException(409, f"Execution cannot accept step completions (status={ex.status})")
    se = db.query(WorkflowStepExecution).filter_by(
        execution_id=execution_id, id=step_id).first()
    if not se:
        raise HTTPException(404, "Step execution not found")
    se.assignee_email = assignee_email
    se.status = "completed"
    se.outcome = outcome
    se.notes = notes
    se.completed_at = datetime.now(timezone.utc)
    ex.current_step = se.step_order + 1

    # Check if all required steps are done
    all_steps = db.query(WorkflowStepExecution).filter_by(execution_id=execution_id).all()
    remaining = [s for s in all_steps if s.status == "pending"]
    if not remaining:
        ex.status = "completed"
        ex.outcome = "completed"
        ex.completed_at = datetime.now(timezone.utc)

    db.commit()
    _audit(db, "workflow_step_completed", tenant_id,
           {"execution_id": execution_id, "step_id": step_id, "outcome": outcome})
    return {"execution_id": execution_id, "step_id": step_id, "status": se.status,
            "execution_status": ex.status}


@router.post("/executions/{execution_id}/escalate",
             dependencies=[Depends(require_roles("admin", "manager"))])
def escalate_execution(execution_id: int, request: Request,
                        escalated_by: str = Query(...), reason: str = Query(...),
                        db: Session = Depends(get_db)):
    ex = db.query(WorkflowExecution).filter_by(id=execution_id, tenant_id=tenant_id).first()
    if not ex:
        raise HTTPException(404, "Execution not found")
    if ex.status in ("completed", "cancelled"):
        raise HTTPException(409, f"Cannot escalate a {ex.status} execution")
    ex.status = "escalated"
    ex.outcome_notes = f"Escalated by {escalated_by}: {reason}"
    db.commit()
    _audit(db, "workflow_execution_escalated", tenant_id,
           {"execution_id": execution_id, "escalated_by": escalated_by, "reason": reason})
    return {"id": ex.id, "status": ex.status}


# ---------------------------------------------------------------------------
# Phase 3 — Intelligent Work Queues
# ---------------------------------------------------------------------------

class QueueItemIn(BaseModel):
    queue_type: str
    title: str
    description: Optional[str] = None
    priority: str = "normal"
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    execution_id: Optional[int] = None
    assigned_to: Optional[str] = None
    due_at: Optional[datetime] = None


@router.post("/work-queue", status_code=201,
             dependencies=[Depends(require_roles("admin", "manager", "technician"))])
def add_queue_item(request: Request, body: QueueItemIn = ...,
                   db: Session = Depends(get_db)):
    if body.queue_type not in _QUEUE_TYPES:
        raise HTTPException(400, f"queue_type must be one of {_QUEUE_TYPES}")
    if body.priority not in _PRIORITIES:
        raise HTTPException(400, f"priority must be one of {_PRIORITIES}")
    item = WorkQueueItem(tenant_id=tenant_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    _audit(db, "queue_item_created", tenant_id,
           {"item_id": item.id, "queue_type": item.queue_type, "priority": item.priority})
    return {"id": item.id, "queue_type": item.queue_type, "status": item.status,
            "priority": item.priority, "created_at": item.created_at.isoformat()}


@router.get("/work-queue",
            dependencies=[Depends(require_roles("admin", "manager", "technician", "executive"))])
def list_queue_items(request: Request,
                     queue_type: Optional[str] = Query(None),
                     status: Optional[str] = Query(None),
                     priority: Optional[str] = Query(None),
                     db: Session = Depends(get_db)):
    q = db.query(WorkQueueItem).filter_by(tenant_id=tenant_id)
    if queue_type:
        q = q.filter_by(queue_type=queue_type)
    if status:
        q = q.filter_by(status=status)
    if priority:
        q = q.filter_by(priority=priority)
    rows = q.order_by(WorkQueueItem.created_at.desc()).limit(500).all()
    return [{"id": r.id, "queue_type": r.queue_type, "title": r.title,
             "priority": r.priority, "status": r.status,
             "source_type": r.source_type, "assigned_to": r.assigned_to,
             "execution_id": r.execution_id,
             "due_at": r.due_at.isoformat() if r.due_at else None,
             "escalated": r.escalated,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/work-queue/{item_id}/claim",
             dependencies=[Depends(require_roles("admin", "manager", "technician"))])
def claim_queue_item(item_id: int, request: Request,
                     claimed_by: str = Query(...), db: Session = Depends(get_db)):
    item = db.query(WorkQueueItem).filter_by(id=item_id, tenant_id=tenant_id).first()
    if not item:
        raise HTTPException(404, "Queue item not found")
    if item.status not in ("open",):
        raise HTTPException(409, f"Item cannot be claimed (status={item.status})")
    item.status = "claimed"
    item.claimed_by = claimed_by
    item.claimed_at = datetime.now(timezone.utc)
    item.assigned_to = claimed_by
    db.commit()
    _audit(db, "queue_item_claimed", tenant_id, {"item_id": item_id, "claimed_by": claimed_by})
    return {"id": item.id, "status": item.status, "claimed_by": item.claimed_by}


@router.post("/work-queue/{item_id}/complete",
             dependencies=[Depends(require_roles("admin", "manager", "technician"))])
def complete_queue_item(item_id: int, request: Request,
                         completed_by: str = Query(...),
                         notes: Optional[str] = Query(None),
                         db: Session = Depends(get_db)):
    item = db.query(WorkQueueItem).filter_by(id=item_id, tenant_id=tenant_id).first()
    if not item:
        raise HTTPException(404, "Queue item not found")
    if item.status not in ("open", "claimed", "in_progress"):
        raise HTTPException(409, f"Item cannot be completed (status={item.status})")
    item.status = "completed"
    item.completed_by = completed_by
    item.completed_at = datetime.now(timezone.utc)
    item.completion_notes = notes
    db.commit()
    _audit(db, "queue_item_completed", tenant_id,
           {"item_id": item_id, "completed_by": completed_by})
    return {"id": item.id, "status": item.status}


@router.post("/work-queue/{item_id}/escalate",
             dependencies=[Depends(require_roles("admin", "manager"))])
def escalate_queue_item(item_id: int, request: Request,
                         escalated_by: str = Query(...), db: Session = Depends(get_db)):
    item = db.query(WorkQueueItem).filter_by(id=item_id, tenant_id=tenant_id).first()
    if not item:
        raise HTTPException(404, "Queue item not found")
    if item.status in ("completed", "cancelled"):
        raise HTTPException(409, f"Cannot escalate a {item.status} item")
    item.escalated = True
    item.priority = "critical"
    db.commit()
    _audit(db, "queue_item_escalated", tenant_id,
           {"item_id": item_id, "escalated_by": escalated_by})
    return {"id": item.id, "escalated": item.escalated, "priority": item.priority}


# ---------------------------------------------------------------------------
# Phase 4 — Enterprise Command Center
# ---------------------------------------------------------------------------

class RiskSnapshotIn(BaseModel):
    snapshot_type: str
    period_label: Optional[str] = None
    open_high_priority_items: int = 0
    overdue_items: int = 0
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    total_open_queue_items: int = 0
    technician_queue_depth: int = 0
    manager_queue_depth: int = 0
    executive_queue_depth: int = 0
    vendor_queue_depth: int = 0
    backlog_items_gt_sla: int = 0
    avg_completion_hours: Optional[float] = None
    active_escalations: int = 0
    escalations_last_7d: int = 0
    notes: Optional[str] = None
    generated_by: str


@router.post("/command-center/snapshots", status_code=201,
             dependencies=[Depends(require_roles("admin", "executive"))])
def create_snapshot(request: Request, body: RiskSnapshotIn = ...,
                    db: Session = Depends(get_db)):
    if body.snapshot_type not in _SNAPSHOT_TYPES:
        raise HTTPException(400, f"snapshot_type must be one of {_SNAPSHOT_TYPES}")
    snap = OperationalRiskSnapshot(tenant_id=tenant_id, **body.model_dump())
    db.add(snap)
    db.commit()
    db.refresh(snap)
    _audit(db, "command_center_snapshot_created", tenant_id,
           {"snapshot_id": snap.id, "type": snap.snapshot_type})
    return {"id": snap.id, "snapshot_type": snap.snapshot_type,
            "risk_score": snap.risk_score, "created_at": snap.created_at.isoformat()}


@router.get("/command-center/snapshots",
            dependencies=[Depends(require_roles("admin", "executive", "manager"))])
def list_snapshots(request: Request,
                   snapshot_type: Optional[str] = Query(None),
                   db: Session = Depends(get_db)):
    q = db.query(OperationalRiskSnapshot).filter_by(tenant_id=tenant_id)
    if snapshot_type:
        q = q.filter_by(snapshot_type=snapshot_type)
    rows = q.order_by(OperationalRiskSnapshot.created_at.desc()).limit(100).all()
    return [{"id": r.id, "snapshot_type": r.snapshot_type, "period_label": r.period_label,
             "risk_score": r.risk_score, "open_high_priority_items": r.open_high_priority_items,
             "overdue_items": r.overdue_items, "active_escalations": r.active_escalations,
             "total_open_queue_items": r.total_open_queue_items,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/command-center/dashboard",
            dependencies=[Depends(require_roles("admin", "executive", "manager"))])
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """Live aggregate dashboard — derived from queue and execution state."""
    open_items = db.query(WorkQueueItem).filter(
        WorkQueueItem.tenant_id == tenant_id,
        WorkQueueItem.status.in_(("open", "claimed", "in_progress")),
    ).all()

    by_queue = {qt: 0 for qt in _QUEUE_TYPES}
    high_priority = 0
    escalated_count = 0
    for item in open_items:
        by_queue[item.queue_type] = by_queue.get(item.queue_type, 0) + 1
        if item.priority in ("high", "critical"):
            high_priority += 1
        if item.escalated:
            escalated_count += 1

    active_executions = db.query(WorkflowExecution).filter(
        WorkflowExecution.tenant_id == tenant_id,
        WorkflowExecution.status.in_(("in_progress", "awaiting_approval", "escalated")),
    ).count()

    overdue = db.query(WorkQueueItem).filter(
        WorkQueueItem.tenant_id == tenant_id,
        WorkQueueItem.due_at < datetime.now(timezone.utc),
        WorkQueueItem.status.notin_(("completed", "cancelled")),
    ).count()

    return {
        "tenant_id": tenant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "risk": {
            "open_high_priority_items": high_priority,
            "active_escalations": escalated_count,
            "overdue_items": overdue,
        },
        "workload": {
            "total_open": len(open_items),
            "by_queue": by_queue,
            "active_executions": active_executions,
        },
        "human_review_required": True,
    }


# ---------------------------------------------------------------------------
# Phase 5 — AI Operations Copilot
# ---------------------------------------------------------------------------

class CopilotQueryIn(BaseModel):
    asked_by: str
    query_text: str
    query_type: str


class RecommendationReviewIn(BaseModel):
    reviewed_by: str
    review_status: str
    review_notes: Optional[str] = None


def _build_copilot_response(query_type: str, tenant_id: str, db) -> tuple[str, float]:
    """Derive a candidate response from live queue + execution state."""
    # Use naive UTC — SQLite stores naive datetimes; avoids offset-naive comparison errors.
    now_naive = datetime.utcnow()

    open_items = db.query(WorkQueueItem).filter(
        WorkQueueItem.tenant_id == tenant_id,
        WorkQueueItem.status.in_(("open", "claimed", "in_progress")),
    ).all()

    total_open = len(open_items)
    high_priority = [i for i in open_items if i.priority in ("high", "critical")]
    escalated = [i for i in open_items if i.escalated]
    overdue = [i for i in open_items if i.due_at and i.due_at < now_naive]

    by_queue: dict[str, int] = {}
    for item in open_items:
        by_queue[item.queue_type] = by_queue.get(item.queue_type, 0) + 1

    active_executions = db.query(WorkflowExecution).filter(
        WorkflowExecution.tenant_id == tenant_id,
        WorkflowExecution.status.in_(("in_progress", "awaiting_approval", "escalated")),
    ).count()

    if query_type == "prioritization":
        top = sorted(high_priority, key=lambda i: (i.priority == "critical", i.due_at or now_naive), reverse=True)[:5]
        titles = ", ".join(f'"{i.title}"' for i in top) if top else "none found"
        response = (
            f"There are {len(high_priority)} high/critical priority items open across all queues "
            f"({total_open} total). Top candidates for immediate attention: {titles}. "
            f"{len(overdue)} items are past their due date. Human review required before action."
        )
        confidence = min(0.95, 0.55 + 0.05 * min(len(open_items), 8))

    elif query_type == "workload":
        queue_summary = "; ".join(f"{qt}: {cnt}" for qt, cnt in sorted(by_queue.items()))
        busiest = max(by_queue, key=by_queue.get) if by_queue else "none"
        response = (
            f"Current queue depth — {queue_summary or 'all queues empty'}. "
            f"The busiest queue is '{busiest}'. "
            f"{active_executions} workflow executions are active. "
            "Rebalancing candidates are surfaced here — human decision required."
        )
        confidence = 0.78 if total_open > 0 else 0.60

    elif query_type == "action":
        response = (
            f"There are {len(escalated)} escalated items and {len(overdue)} overdue items requiring attention. "
            f"{active_executions} executions are in flight. "
            "Suggested investigation candidates (not orders): review escalated items first, "
            "then overdue high-priority items. No autonomous action has been taken."
        )
        confidence = min(0.85, 0.50 + 0.05 * (len(escalated) + len(overdue)))

    else:  # status
        response = (
            f"Operational status — {total_open} open queue items, "
            f"{len(high_priority)} high/critical priority, "
            f"{len(escalated)} escalated, {len(overdue)} overdue, "
            f"{active_executions} active workflow executions. "
            "All figures are point-in-time snapshots requiring human interpretation."
        )
        confidence = 0.88

    return response, round(confidence, 2)


@router.post("/executions/scan-timeouts",
             dependencies=[Depends(require_roles("admin"))])
def scan_step_timeouts(request: Request, db: Session = Depends(get_db)):
    """Evaluate overdue WorkflowStepExecutions and enforce on_timeout policy.

    Policies:
      escalate — set step status to escalated; set execution status to escalated
      skip     — mark step completed with outcome=skipped
      block    — leave step pending; mark execution escalated for human review
    """
    now = datetime.now(timezone.utc)
    processed = []

    # Find all active executions for this tenant
    active_execs = db.query(WorkflowExecution).filter(
        WorkflowExecution.tenant_id == tenant_id,
        WorkflowExecution.status.in_(("in_progress", "awaiting_approval")),
    ).all()

    for ex in active_execs:
        pending_steps = db.query(WorkflowStepExecution).filter_by(
            execution_id=ex.id, status="pending"
        ).all()
        for se in pending_steps:
            step_def = db.query(WorkflowStep).filter_by(id=se.step_id).first()
            if not step_def or not step_def.timeout_hours:
                continue
            deadline = se.created_at.replace(tzinfo=timezone.utc) + timedelta(hours=step_def.timeout_hours)
            if now <= deadline:
                continue
            # Timeout reached — apply policy
            policy = step_def.on_timeout or "escalate"
            if policy == "skip":
                se.status = "skipped"
                se.outcome = "timeout_skipped"
                se.completed_at = now
                ex.current_step = se.step_order + 1
            elif policy == "escalate":
                se.status = "escalated"
                ex.status = "escalated"
                ex.outcome_notes = f"Step '{step_def.name}' timed out after {step_def.timeout_hours}h"
            else:  # block
                ex.status = "escalated"
                ex.outcome_notes = f"Step '{step_def.name}' timed out (blocking policy)"

            processed.append({
                "execution_id": ex.id,
                "step_id": se.id,
                "step_name": step_def.name,
                "policy": policy,
                "deadline": deadline.isoformat(),
            })
            _audit(db, "step_timeout_enforced", tenant_id,
                   {"execution_id": ex.id, "step_id": se.id, "policy": policy})

    db.commit()
    return {"scanned_executions": len(active_execs), "timeouts_processed": len(processed),
            "details": processed}


@router.post("/copilot/query", status_code=201,
             dependencies=[Depends(require_roles("admin", "manager", "executive"))])
def submit_copilot_query(request: Request, body: CopilotQueryIn = ...,
                          db: Session = Depends(get_db)):
    if body.query_type not in _QUERY_TYPES:
        raise HTTPException(400, f"query_type must be one of {_QUERY_TYPES}")

    response, confidence = _build_copilot_response(body.query_type, tenant_id, db)

    cq = CopilotQuery(
        tenant_id=tenant_id,
        asked_by=body.asked_by,
        query_text=body.query_text,
        query_type=body.query_type,
        response_summary=response,
        confidence=confidence,
        human_review_required=True,
    )
    db.add(cq)
    db.flush()

    rec = CopilotRecommendation(
        tenant_id=tenant_id,
        query_id=cq.id,
        recommendation_type=body.query_type,
        title=f"{body.query_type.title()} Recommendation",
        rationale=response,
        suggested_action="Review and validate findings before taking any operational action.",
        confidence=cq.confidence,
        human_review_required=True,
        review_status="pending",
    )
    db.add(rec)
    db.commit()
    db.refresh(cq)
    db.refresh(rec)
    _audit(db, "copilot_query_submitted", tenant_id,
           {"query_id": cq.id, "query_type": body.query_type, "asked_by": body.asked_by})
    return {
        "query_id": cq.id,
        "recommendation_id": rec.id,
        "response_summary": cq.response_summary,
        "confidence": cq.confidence,
        "human_review_required": True,
        "disclaimer": (
            "This is a candidate recommendation only. "
            "No autonomous action has been or will be taken. "
            "Human review is required before any operational decision."
        ),
    }


@router.get("/copilot/recommendations",
            dependencies=[Depends(require_roles("admin", "manager", "executive"))])
def list_recommendations(request: Request,
                          review_status: Optional[str] = Query(None),
                          db: Session = Depends(get_db)):
    q = db.query(CopilotRecommendation).filter_by(tenant_id=tenant_id)
    if review_status:
        q = q.filter_by(review_status=review_status)
    rows = q.order_by(CopilotRecommendation.created_at.desc()).limit(200).all()
    return [{"id": r.id, "recommendation_type": r.recommendation_type, "title": r.title,
             "confidence": r.confidence, "review_status": r.review_status,
             "human_review_required": r.human_review_required,
             "reviewed_by": r.reviewed_by,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/copilot/recommendations/{rec_id}/review",
             dependencies=[Depends(require_roles("admin", "manager", "executive"))])
def review_recommendation(rec_id: int, request: Request,
                            body: RecommendationReviewIn = ...,
                            db: Session = Depends(get_db)):
    if body.review_status not in _REVIEW_STATUSES:
        raise HTTPException(400, f"review_status must be one of {_REVIEW_STATUSES}")
    rec = db.query(CopilotRecommendation).filter_by(id=rec_id, tenant_id=tenant_id).first()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    if rec.review_status != "pending":
        raise HTTPException(409, f"Recommendation already reviewed (status={rec.review_status})")
    rec.review_status = body.review_status
    rec.reviewed_by = body.reviewed_by
    rec.reviewed_at = datetime.now(timezone.utc)
    rec.review_notes = body.review_notes
    rec.human_review_required = False  # satisfied
    db.commit()
    _audit(db, "copilot_recommendation_reviewed", tenant_id,
           {"rec_id": rec_id, "status": body.review_status, "reviewed_by": body.reviewed_by})
    return {"id": rec.id, "review_status": rec.review_status, "reviewed_by": rec.reviewed_by,
            "reviewed_at": rec.reviewed_at.isoformat()}
