"""v4.1 — LumenAI OS: Project Forge — AI Workflow Builder & No-Code
Clinical Rules Engine.

## Reuse map (researched before writing any of this file)

Forge is the 11th cross-cutting sprint on this branch. Before adding a
single new table, the following pre-existing infrastructure was
identified and is reused directly rather than duplicated:

  * **Automation** — `app/automation_engine.py::AutomationRule`/
    `process_trigger` already exists, but its `_matches()` evaluator is a
    **flat AND-of-fields matcher only** — no OR/NOT/nesting anywhere in
    this codebase (confirmed by grepping every rule/escalation/
    validation/prioritization engine). Forge's Clinical Rule Engine
    genuinely needs a new nested boolean condition evaluator
    (`forge_rule_engine.py`) — this is real new capability, not a
    duplicate of `automation_engine.py`, which is left untouched.
  * **CAPA** — the "Create CAPA" automation action calls
    `app/services/capa_service.py::create_capa` directly.
  * **Knowledge capture** — the "Create Knowledge Article Draft" action
    calls `app/services/knowledge_repository_service.py::create_article`
    directly, with `approval_status=DRAFT` (from `app.models.knowledge`).
  * **Digital Twin** — the "Update Digital Twin" action and node reuse
    `digital_twin_engine.log_instrument_flow`/`complete_flow` directly
    (same functions Beacon's repair partner portal already reuses).
  * **Shared Intelligence Layer** — every AI Decision Node dispatches
    through Genesis's `platform_intelligence_gateway.py` registry
    (`get_shared_service`/`get_recommendation_engine`) rather than
    importing each engine ad hoc — this is the intended purpose of that
    gateway module.
  * **Watchlist / Enterprise Alert** — Atlas's `EnterpriseWatchlistEntry`/
    `EnterpriseAlert` and Sentinel's `ClinicalWatchlistEntry` already
    exist; their own `_upsert`/`generate_*` functions are private/batch-
    oriented (confirmed no public single-entry create function exists),
    so Forge's "Flag Instrument"/"Create Watchlist Entry"/"Create
    Enterprise Alert" actions construct a row on the existing
    `ClinicalWatchlistEntry`/`EnterpriseAlert` models directly, matching
    their exact existing field shape — no new watchlist/alert table.
  * **Versioning** — copies Beacon's exact pattern
    (`beacon_standards_service.py`: one nullable `supersedes_id` self-FK
    + a `status` field + a version-chain walker) rather than a second
    versioned-content model or a separate history table.
  * **Approval chains** — confirmed nothing in this codebase models a
    multi-step (Technician → Supervisor → Manager → Director) approval
    chain; `GovernanceApproval` is single-reviewer only. This is a
    genuine gap `WorkflowApprovalChain`/`WorkflowApprovalInstance` fills.

## The five new tables in this file

Nothing before Forge modeled a visual workflow definition, a nested-
condition clinical rule, a multi-step approval chain (and its running
instance), or a workflow execution/simulation run — these are real gaps:

  * `WorkflowDefinition` — a visual workflow (nodes/edges as JSON),
    versioned via the Beacon-style `supersedes_id` chain, with
    `is_template`/`marketplace_status` for Sections 4 and 10.
  * `WorkflowRule` — a clinical rule: nested AND/OR/NOT condition tree +
    an ordered action list, versioned the same way.
  * `WorkflowApprovalChain` — an ordered list of approval role-steps an
    organization defines once, reusable across workflows.
  * `WorkflowApprovalInstance` — one running instance of a chain against
    one workflow execution, tracking the current step and each step's
    decision.
  * `WorkflowExecution` — one real (or simulated) run of a
    `WorkflowDefinition`, recording the node path taken, timing, and
    outcome — this is what Section 8's Simulator replays and compares.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 1: Workflow node types ──────────────────────────────────────────
NODE_START = "start"
NODE_INSPECTION = "inspection"
NODE_AI_ANALYSIS = "ai_analysis"
NODE_ANATOMY_CHECK = "anatomy_check"
NODE_COVERAGE_CHECK = "coverage_check"
NODE_KNOWLEDGE_LOOKUP = "knowledge_lookup"
NODE_DIGITAL_TWIN_UPDATE = "digital_twin_update"
NODE_CLINICAL_REASONING = "clinical_reasoning"
NODE_SUPERVISOR_REVIEW = "supervisor_review"
NODE_CONDITIONAL_BRANCH = "conditional_branch"
NODE_NOTIFICATION = "notification"
NODE_APPROVAL = "approval"
NODE_REPAIR_REFERRAL = "repair_referral"
NODE_KNOWLEDGE_CAPTURE = "knowledge_capture"
NODE_EXPORT_REPORT = "export_report"
NODE_END = "end"
NODE_TYPES = [
    NODE_START, NODE_INSPECTION, NODE_AI_ANALYSIS, NODE_ANATOMY_CHECK, NODE_COVERAGE_CHECK,
    NODE_KNOWLEDGE_LOOKUP, NODE_DIGITAL_TWIN_UPDATE, NODE_CLINICAL_REASONING, NODE_SUPERVISOR_REVIEW,
    NODE_CONDITIONAL_BRANCH, NODE_NOTIFICATION, NODE_APPROVAL, NODE_REPAIR_REFERRAL,
    NODE_KNOWLEDGE_CAPTURE, NODE_EXPORT_REPORT, NODE_END,
]

# ── Section 3: Rule condition fields ────────────────────────────────────────
CONDITION_FIELDS = [
    "instrument_family", "manufacturer", "model", "inspection_zone", "finding", "severity",
    "coverage_pct", "confidence", "technician_role", "supervisor_decision", "digital_twin_health",
    "facility", "department", "procedure", "time", "shift",
]
RULE_OPERATORS = ["and", "or", "not"]
LEAF_OPERATORS = ["eq", "neq", "gt", "gte", "lt", "lte", "in", "contains"]

# ── Section 6: Automation action types ──────────────────────────────────────
ACTION_ASSIGN_TECHNICIAN = "assign_technician"
ACTION_NOTIFY_SUPERVISOR = "notify_supervisor"
ACTION_ESCALATE = "escalate"
ACTION_CREATE_CAPA = "create_capa"
ACTION_CREATE_KNOWLEDGE_DRAFT = "create_knowledge_draft"
ACTION_GENERATE_REPORT = "generate_report"
ACTION_FLAG_INSTRUMENT = "flag_instrument"
ACTION_CREATE_WATCHLIST_ENTRY = "create_watchlist_entry"
ACTION_UPDATE_DIGITAL_TWIN = "update_digital_twin"
ACTION_CREATE_ENTERPRISE_ALERT = "create_enterprise_alert"
# Rule-specific actions (Section 2's example: Require Supervisor Review /
# Recommend Reclean / Capture Knowledge Note / Update Digital Twin)
ACTION_REQUIRE_SUPERVISOR_REVIEW = "require_supervisor_review"
ACTION_RECOMMEND_RECLEAN = "recommend_reclean"
ACTION_TYPES = [
    ACTION_ASSIGN_TECHNICIAN, ACTION_NOTIFY_SUPERVISOR, ACTION_ESCALATE, ACTION_CREATE_CAPA,
    ACTION_CREATE_KNOWLEDGE_DRAFT, ACTION_GENERATE_REPORT, ACTION_FLAG_INSTRUMENT,
    ACTION_CREATE_WATCHLIST_ENTRY, ACTION_UPDATE_DIGITAL_TWIN, ACTION_CREATE_ENTERPRISE_ALERT,
    ACTION_REQUIRE_SUPERVISOR_REVIEW, ACTION_RECOMMEND_RECLEAN,
]

# ── Section 5: AI decision node run-types ───────────────────────────────────
AI_RUN_DETECTION = "run_detection"
AI_RUN_ANATOMY_MODEL = "run_anatomy_model"
AI_RUN_RISK_MODEL = "run_risk_model"
AI_RUN_KNOWLEDGE_GRAPH = "run_knowledge_graph"
AI_RUN_RECOMMENDATION_ENGINE = "run_recommendation_engine"
AI_RUN_PREDICTION_MODEL = "run_prediction_model"
AI_RUN_SENTINEL = "run_sentinel"
AI_RUN_DIGITAL_TWIN_UPDATE = "run_digital_twin_update"
AI_RUN_TYPES = [
    AI_RUN_DETECTION, AI_RUN_ANATOMY_MODEL, AI_RUN_RISK_MODEL, AI_RUN_KNOWLEDGE_GRAPH,
    AI_RUN_RECOMMENDATION_ENGINE, AI_RUN_PREDICTION_MODEL, AI_RUN_SENTINEL, AI_RUN_DIGITAL_TWIN_UPDATE,
]

# ── Section 9: Version control ───────────────────────────────────────────────
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_ARCHIVED = "archived"
WORKFLOW_STATUSES = [STATUS_DRAFT, STATUS_PUBLISHED, STATUS_ARCHIVED]

# ── Section 10: Marketplace ──────────────────────────────────────────────────
MARKETPLACE_PRIVATE = "private"
MARKETPLACE_PENDING_REVIEW = "pending_review"
MARKETPLACE_PUBLISHED = "published"
MARKETPLACE_STATUSES = [MARKETPLACE_PRIVATE, MARKETPLACE_PENDING_REVIEW, MARKETPLACE_PUBLISHED]

# ── Section 4: Named workflow templates ─────────────────────────────────────
TEMPLATE_CATEGORIES = [
    "general_instrument_inspection", "rigid_scope", "flexible_endoscope", "loaner_instrument",
    "vendor_tray", "robotic_instrument", "orthopedic", "neurosurgery", "custom_organization",
]

# ── Section 7: Default approval chain steps ─────────────────────────────────
DEFAULT_APPROVAL_STEPS = ["technician", "supervisor", "manager", "director"]

APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"
APPROVAL_INSTANCE_STATUSES = [APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED]

EXECUTION_RUNNING = "running"
EXECUTION_COMPLETED = "completed"
EXECUTION_FAILED = "failed"
EXECUTION_STATUSES = [EXECUTION_RUNNING, EXECUTION_COMPLETED, EXECUTION_FAILED]

DISCLAIMER = (
    "LumenAI Workflow Forge configures inspection routing, decision logic, and automation without "
    "modifying application code. Every workflow, rule, and automated action remains subject to the "
    "same RBAC, audit logging, and human-review requirements already enforced by the underlying "
    "LumenAI OS services it invokes. No workflow makes an unreviewable autonomous clinical decision."
)


class WorkflowDefinition(Base):
    """A visual workflow (Section 1), versioned (Section 9), optionally a
    template (Section 4) or marketplace listing (Section 10)."""

    __tablename__ = "forge_workflow_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)  # "" for global templates
    workflow_ref: Mapped[str] = mapped_column(String(40), nullable=False, index=True)  # shared across versions of "the same" workflow
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="", nullable=False, index=True)

    nodes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    edges_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_DRAFT, nullable=False, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supersedes_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    author: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    marketplace_status: Mapped[str] = mapped_column(String(20), default=MARKETPLACE_PRIVATE, nullable=False, index=True)
    approval_chain_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class WorkflowRule(Base):
    """A clinical rule (Section 2): nested condition tree + action list,
    versioned the same way as `WorkflowDefinition`."""

    __tablename__ = "forge_workflow_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    rule_ref: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    condition_json: Mapped[str] = mapped_column(Text, nullable=False)  # nested {"op": "and/or/not", "conditions": [...]} or leaf
    actions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_DRAFT, nullable=False, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supersedes_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    author: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)  # pending/approved/rejected
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowApprovalChain(Base):
    """An organization-defined ordered approval chain (Section 7)."""

    __tablename__ = "forge_approval_chains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    steps_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON ordered list of role strings


class WorkflowApprovalInstance(Base):
    """One running instance of a chain, tracking the current step and
    every step's decision (Section 7)."""

    __tablename__ = "forge_approval_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    execution_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=APPROVAL_PENDING, nullable=False, index=True)
    decisions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # [{step, role, decided_by, decision, decided_at}]
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowExecution(Base):
    """One real or simulated run of a `WorkflowDefinition` (Sections 1, 8)."""

    __tablename__ = "forge_workflow_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    workflow_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(20), default=EXECUTION_RUNNING, nullable=False, index=True)
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    triggered_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    decision_path_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # ordered list of node_keys visited
    execution_log_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # per-node detail entries
    expected_outcome: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actual_outcome: Mapped[str] = mapped_column(Text, default="", nullable=False)
