"""v5.4 — LumenAI Network: Project Nova — Autonomous AI Agent Platform.

## Naming disambiguation (read this first)

**A real, working multi-agent pipeline already exists** —
`app/agents/*.py` ("Phase 22 — Multi-Agent Clinical Intelligence
Platform", pre-dating this sprint series), with 10 deterministic,
in-process agent classes (Instrument, Anatomy, Coverage, Contamination,
Damage, Clinical Reasoning, Recommendation, Supervisor, Learning,
Enterprise), a static `app.agents.registry.get_registry()` function, and
`app.agents.orchestrator.run_pipeline` — already exposed at
`/api/agents/registry`, `/api/agents/run/{id}`, `/api/agents/trace/{id}`.
Nova does not rewrite, replace, or duplicate any of this. Its
`_health()` self-check philosophy ("these agents are deterministic
in-process Python wrapping existing services, not external calls... not
a fabricated uptime/latency metric") is the same one this file follows.

Nova is the 23rd additive sprint. It adds the *governed platform layer*
around agents in general — a persisted registry, a logged communication
bus, configurable task orchestration, governed per-agent memory, human-
agent collaboration requests, and an agent marketplace — composing the
existing pipeline rather than reimplementing it:

  * **Agent Registry (Section 2)** — `AgentDefinition` is genuinely new
    (the existing registry is static/in-memory, not queryable or
    extensible at runtime). Every one of the 14 named Core Agents
    (Section 4) gets one row; for names that already correspond to a
    real Phase 22 agent class (Anatomy, Clinical Reasoning, Enterprise),
    the row's `wrapped_module` field points at that *same* existing
    module — never a second implementation. Nova's registry endpoint
    also merges in the 10 Phase 22 pipeline agents' live entries from
    `app.agents.registry.get_registry()`, so `/api/nova/agents` is the
    complete picture, not a partial one.
  * **Agent Communication Bus (Section 3)** — `AgentMessage` is
    genuinely new; the existing orchestrator builds an in-memory
    `trace` list per run but never persists it. Nova can persist Phase
    22's own trace entries as `AgentMessage` rows via
    `nova_communication_bus_service.log_pipeline_trace` (a thin
    adapter over the real trace, never a re-derivation of it), as well
    as log messages for its own new agent compositions.
  * **Task Orchestration (Section 5)** — `AgentTaskRun` is a new,
    configurable pipeline-run record distinct from Phase 22's
    hardcoded 10-step inspection pipeline (which keeps its own
    `run_pipeline` entry point unchanged) — for compositions across the
    newer named agents (Vision, Digital Twin, Knowledge, Workflow,
    Simulation, Quality, CAPA, Audit, Executive, Research).
  * **Agent Memory (Section 6)** — `AgentMemoryEntry` is genuinely new;
    nothing in this codebase persists a per-agent memory record.
  * **Human-Agent Collaboration (Section 7)** — `AgentCollaborationRequest`
    is genuinely new. "Request explanations" reuses GuardianX's
    `AIExplainabilityRecord`/`guardianx_explainability_service.py`
    directly rather than a second explanation store.
  * **Agent Marketplace (Section 8)** — zero new tables. Infinity's
    `MarketplaceListing`/`infinity_marketplace_service.py` (v5.0) is
    already a generic, developer-owned, review-gated listing pipeline;
    `LISTING_TYPES` gains 6 new agent-category values.
  * **Observability (Section 9)** — zero new tables. Computed live from
    `AgentDefinition.status`/health self-check, `AgentMessage` counts,
    and `AgentTaskRun` outcomes — never a fabricated latency/resource
    metric, the same discipline Phase 22's own registry established.

## What is genuinely new in this file

Five tables: `AgentDefinition`, `AgentMessage`, `AgentTaskRun`,
`AgentMemoryEntry`, `AgentCollaborationRequest`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Agent Framework / Registry (Sections 1, 2, 4) ────────────────────────────
AGENT_CATEGORY_CORE = "core"
AGENT_CATEGORY_MARKETPLACE = "marketplace"
AGENT_CATEGORIES = [AGENT_CATEGORY_CORE, AGENT_CATEGORY_MARKETPLACE]

AGENT_STATUS_ACTIVE = "active"
AGENT_STATUS_DISABLED = "disabled"
AGENT_STATUS_DEPRECATED = "deprecated"
AGENT_STATUSES = [AGENT_STATUS_ACTIVE, AGENT_STATUS_DISABLED, AGENT_STATUS_DEPRECATED]

AGENT_HEALTH_OK = "ok"
AGENT_HEALTH_DEGRADED = "degraded"
AGENT_HEALTH_UNKNOWN = "unknown"
AGENT_HEALTH_STATUSES = [AGENT_HEALTH_OK, AGENT_HEALTH_DEGRADED, AGENT_HEALTH_UNKNOWN]

# The 14 named Core Agents (Section 4), by agent_key.
CORE_AGENT_KEYS = [
    "inspection_agent", "vision_agent", "anatomy_agent", "digital_twin_agent", "knowledge_agent",
    "clinical_reasoning_agent", "workflow_agent", "simulation_agent", "quality_agent", "capa_agent",
    "audit_agent", "executive_agent", "research_agent", "enterprise_agent",
]

# ── Task Orchestration (Section 5) ───────────────────────────────────────────
TASK_RUN_RUNNING = "running"
TASK_RUN_COMPLETED = "completed"
TASK_RUN_FAILED = "failed"
TASK_RUN_STATUSES = [TASK_RUN_RUNNING, TASK_RUN_COMPLETED, TASK_RUN_FAILED]

# ── Agent Memory (Section 6) ─────────────────────────────────────────────────
MEMORY_WORKING = "working"
MEMORY_CONVERSATION_CONTEXT = "conversation_context"
MEMORY_HISTORICAL_LEARNING = "historical_learning"
MEMORY_TASK_HISTORY = "task_history"
MEMORY_EVIDENCE = "evidence"
MEMORY_TYPES = [
    MEMORY_WORKING, MEMORY_CONVERSATION_CONTEXT, MEMORY_HISTORICAL_LEARNING, MEMORY_TASK_HISTORY, MEMORY_EVIDENCE,
]

# ── Human-Agent Collaboration (Section 7) ────────────────────────────────────
COLLAB_ASSIGN_TASK = "assign_task"
COLLAB_APPROVE_WORK = "approve_work"
COLLAB_REJECT_RECOMMENDATION = "reject_recommendation"
COLLAB_REQUEST_EXPLANATION = "request_explanation"
COLLAB_ESCALATE_TO_SUPERVISOR = "escalate_to_supervisor"
COLLABORATION_REQUEST_TYPES = [
    COLLAB_ASSIGN_TASK, COLLAB_APPROVE_WORK, COLLAB_REJECT_RECOMMENDATION,
    COLLAB_REQUEST_EXPLANATION, COLLAB_ESCALATE_TO_SUPERVISOR,
]

COLLAB_PENDING = "pending"
COLLAB_APPROVED = "approved"
COLLAB_REJECTED = "rejected"
COLLAB_ESCALATED = "escalated"
COLLAB_COMPLETED = "completed"
COLLABORATION_STATUSES = [COLLAB_PENDING, COLLAB_APPROVED, COLLAB_REJECTED, COLLAB_ESCALATED, COLLAB_COMPLETED]

DISCLAIMER = (
    "LumenAI Nova coordinates specialized software agents that wrap this platform's existing "
    "deterministic services -- no agent runs an autonomous large language model or takes an "
    "irreversible clinical or operational action without explicit human authorization and "
    "governance. Every agent output is advisory, requires human review, and is fully auditable."
)


class AgentDefinition(Base):
    """One agent's registry entry (Sections 1, 2, 4) -- identity, role,
    capabilities, permissions, goals, dependencies, version, and health.
    `wrapped_module` names the real, pre-existing service/module this
    agent composes -- never a second implementation of that logic.
    `developer_account_id` is set only for marketplace-installed agents
    (Infinity's `DeveloperAccount`, reused rather than a new identity).
    """

    __tablename__ = "nova_agent_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    agent_key: Mapped[str] = mapped_column(String(60), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    agent_category: Mapped[str] = mapped_column(String(20), default=AGENT_CATEGORY_CORE, nullable=False, index=True)

    capabilities_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    permissions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    goals_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    dependencies_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    wrapped_module: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AGENT_STATUS_ACTIVE, nullable=False, index=True)
    health: Mapped[str] = mapped_column(String(20), default=AGENT_HEALTH_UNKNOWN, nullable=False)

    developer_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registered_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class AgentMessage(Base):
    """One logged communication-bus message (Section 3) -- "every
    interaction is logged." Tenant-aware; `task_run_id` optionally links
    a message to the `AgentTaskRun` it was produced during."""

    __tablename__ = "nova_agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_agent_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    target_agent_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    task_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class AgentTaskRun(Base):
    """One orchestrated multi-agent task run (Section 5) -- a
    configurable ordered pipeline of `agent_key`s, distinct from Phase
    22's hardcoded 10-step inspection pipeline."""

    __tablename__ = "nova_agent_task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pipeline_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_sequence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=TASK_RUN_RUNNING, nullable=False, index=True)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    step_log_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    triggered_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AgentMemoryEntry(Base):
    """One governed, tenant-aware memory record for an agent (Section 6)."""

    __tablename__ = "nova_agent_memory_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    agent_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    content_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class AgentCollaborationRequest(Base):
    """A human-agent collaboration action (Section 7): assign a task,
    approve or reject an agent's work, request an explanation, or
    escalate to a supervisor."""

    __tablename__ = "nova_agent_collaboration_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    agent_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default=COLLAB_PENDING, nullable=False, index=True)
    resolution: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resolved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
