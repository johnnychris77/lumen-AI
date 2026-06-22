"""P22: Autonomous Healthcare Operations Platform — data models.

Phases:
  1 – Operations Orchestration (workflow definitions + steps)
  2 – Workflow Automation (CAPA, inspection, escalation, notification executions)
  3 – Intelligent Work Queues (technician/manager/executive/vendor queues)
  4 – Enterprise Command Center (operational risk snapshots)
  5 – AI Operations Copilot (NL queries + recommendations)

Governance:
  - Every workflow mutation is audit-logged with compliance_flag=True
  - Human-in-the-loop: no automated external action without human approval
  - Tenant isolation enforced at the route layer — no cross-tenant reads
  - Copilot recommendations carry human_review_required=True; no autonomous action
  - Escalations require explicit human approval before external notification
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


# ---------------------------------------------------------------------------
# Phase 1 — Operations Orchestration
# ---------------------------------------------------------------------------

class OperationsWorkflow(Base):
    """Workflow definition template — CAPA, inspection, escalation, or notification."""
    __tablename__ = "p22_operations_workflows"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    workflow_type = Column(String, nullable=False)   # capa / inspection / escalation / notification
    description = Column(Text, nullable=True)
    priority = Column(String, default="normal")       # low / normal / high / critical
    sla_hours = Column(Integer, nullable=True)        # target completion window in hours
    auto_assign = Column(Boolean, default=False)      # queue auto-assignment allowed
    approval_required = Column(Boolean, default=True) # human approval gate
    status = Column(String, default="active")         # active / archived
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowStep(Base):
    """One step within a workflow definition (ordered)."""
    __tablename__ = "p22_workflow_steps"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    step_type = Column(String, nullable=False)        # action / approval / notification / gate
    assignee_role = Column(String, nullable=False)    # technician / manager / executive / vendor
    instructions = Column(Text, nullable=True)
    required = Column(Boolean, default=True)
    timeout_hours = Column(Integer, nullable=True)
    on_timeout = Column(String, default="escalate")   # escalate / skip / block
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 2 — Workflow Automation
# ---------------------------------------------------------------------------

class WorkflowExecution(Base):
    """Runtime instance of a workflow (triggered for a specific resource)."""
    __tablename__ = "p22_workflow_executions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    workflow_id = Column(Integer, nullable=False, index=True)
    resource_type = Column(String, nullable=False)    # capa / inspection / instrument / recall
    resource_id = Column(String, nullable=False)
    triggered_by = Column(String, nullable=False)     # user email or "system"
    trigger_reason = Column(Text, nullable=True)
    status = Column(String, default="pending")        # pending / in_progress / awaiting_approval / escalated / completed / cancelled
    current_step = Column(Integer, default=1)
    priority = Column(String, default="normal")
    sla_due_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    outcome = Column(String, nullable=True)           # completed / cancelled / escalated
    outcome_notes = Column(Text, nullable=True)
    human_approved = Column(Boolean, nullable=True)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowStepExecution(Base):
    """Execution record for one step of a workflow run."""
    __tablename__ = "p22_workflow_step_executions"

    id = Column(Integer, primary_key=True)
    execution_id = Column(Integer, nullable=False, index=True)
    step_id = Column(Integer, nullable=False)
    step_order = Column(Integer, nullable=False)
    assignee_email = Column(String, nullable=True)
    assignee_role = Column(String, nullable=False)
    status = Column(String, default="pending")        # pending / in_progress / completed / skipped / escalated
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    outcome = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 3 — Intelligent Work Queues
# ---------------------------------------------------------------------------

class WorkQueueItem(Base):
    """A work item in one of four role-scoped queues."""
    __tablename__ = "p22_work_queue_items"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    queue_type = Column(String, nullable=False)       # technician / manager / executive / vendor
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String, default="normal")       # low / normal / high / critical
    source_type = Column(String, nullable=True)       # workflow / inspection / capa / recall / manual
    source_id = Column(String, nullable=True)
    execution_id = Column(Integer, nullable=True)     # linked WorkflowExecution if any
    assigned_to = Column(String, nullable=True)       # user email (nullable = unassigned)
    status = Column(String, default="open")           # open / claimed / in_progress / completed / cancelled
    due_at = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    claimed_by = Column(String, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String, nullable=True)
    completion_notes = Column(Text, nullable=True)
    escalated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 4 — Enterprise Command Center
# ---------------------------------------------------------------------------

class OperationalRiskSnapshot(Base):
    """Point-in-time operational risk snapshot for command center dashboards."""
    __tablename__ = "p22_operational_risk_snapshots"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    snapshot_type = Column(String, nullable=False)    # risk / workload / backlog / escalation
    period_label = Column(String, nullable=True)      # e.g. "2026-W25"

    # Risk dashboard
    open_high_priority_items = Column(Integer, default=0)
    overdue_items = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)           # 0.0–1.0 composite

    # Workload dashboard
    total_open_queue_items = Column(Integer, default=0)
    technician_queue_depth = Column(Integer, default=0)
    manager_queue_depth = Column(Integer, default=0)
    executive_queue_depth = Column(Integer, default=0)
    vendor_queue_depth = Column(Integer, default=0)

    # Backlog dashboard
    backlog_items_gt_sla = Column(Integer, default=0)
    avg_completion_hours = Column(Float, nullable=True)

    # Escalation dashboard
    active_escalations = Column(Integer, default=0)
    escalations_last_7d = Column(Integer, default=0)

    notes = Column(Text, nullable=True)
    generated_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 5 — AI Operations Copilot
# ---------------------------------------------------------------------------

class CopilotQuery(Base):
    """Natural language operational query — logged for auditability."""
    __tablename__ = "p22_copilot_queries"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    asked_by = Column(String, nullable=False)         # user email
    query_text = Column(Text, nullable=False)
    query_type = Column(String, nullable=False)       # prioritization / workload / action / status
    response_summary = Column(Text, nullable=True)    # generated answer (candidate only)
    confidence = Column(Float, nullable=True)         # 0.0–1.0
    human_review_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CopilotRecommendation(Base):
    """AI-generated operational recommendation — always requires human review."""
    __tablename__ = "p22_copilot_recommendations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    query_id = Column(Integer, nullable=True)         # linked CopilotQuery
    recommendation_type = Column(String, nullable=False)  # prioritization / workload / action / risk
    title = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    human_review_required = Column(Boolean, default=True)  # ALWAYS True on creation
    review_status = Column(String, default="pending")      # pending / accepted / rejected / modified
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
