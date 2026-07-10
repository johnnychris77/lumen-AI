"""v4.4 — LumenAI OS: Project Catalyst — AI Copilot & Natural Language
Operations.

## Naming disambiguation (confirmed before writing a single line)

A pre-existing **P9 "Autonomous Inspection Copilot"** system already owns
the name "copilot" in this codebase: `app/models/copilot.py`
(`InspectionSession`, `InspectionStep`, `CopilotRecommendation`,
`InspectionProtocol`, `EscalationEvent`), `app/services/copilot_engine.py`,
`app/routes/copilot.py` mounted at `/api/copilot`. P9 is a guided,
step-by-step inspection checklist / escalation wizard driven by
keyword-matched protocol templates — it is not a conversational,
natural-language system and shares no code with this sprint.

To avoid any collision, Project Catalyst:
  * uses the API prefix `/api/catalyst` (never `/api/copilot`);
  * names every new model `Catalyst*` (never `Copilot*`, and never
    `InspectionSession`/`InspectionStep`/`InspectionProtocol`/
    `EscalationEvent`, all already taken by P9);
  * mounts its frontend workspace at `/copilot-workspace` (confirmed
    unused — no route named `/copilot` or `/copilot-workspace` exists
    anywhere in `frontend/src/main.tsx` today; P9 has no frontend page
    at all).

## Reuse map (confirmed before adding a single new table)

This codebase has **zero real LLM/completion-API integration** anywhere
(no `openai`/`anthropic` package dependency, no network call to a
completion endpoint) — every "AI" feature here is a deterministic,
seeded, or rule/threshold-based computation. Consistent with that,
Catalyst's natural-language engine is a deterministic keyword/intent
classifier that dispatches to the real services below; it never
simulates or fabricates a live LLM.

  * Query dispatch reuses `pulse_kpi_service.live_kpis`,
    `pulse_executive_service.executive_command_dashboard`,
    `atlas_report_service.generate_executive_report`,
    `digital_twin_engine.compute_twin_dashboard`,
    `anatomy_risk_service.anatomy_risk_dashboard`,
    `finding_trend_service.finding_trends`, and direct
    `Inspection`/`InspectionFinding` queries for ad hoc combinations —
    no query result is ever computed twice by two different systems.
  * Action dispatch reuses `forge_action_service.execute_action`,
    `forge_workflow_service.publish_workflow`, `capa_service.create_capa`,
    `pulse_notification_center_service.send_via_channel`/
    `route_notification` — Catalyst adds no parallel action-execution
    path, it only adds natural-language *front doors* to these.
  * Explainability reuses `knowledge_graph_service.reasoning_chain`/
    `explain_inspection` as evidence sources and imitates (does not
    reuse code from, since it's inspection-pipeline-scoped) the
    trace-panel idiom already established by `app/agents/` +
    `AgentTraceViewer.tsx`.
  * Multi-modal upload reuses `app/routes/capture.py`'s existing
    multipart image pattern (`image_retention_service.retain_image`,
    EXIF-stripped, audit-logged) — no second upload pipeline is built.

## What's genuinely new in this file

Nothing before Catalyst modeled a multi-turn conversation with memory,
a skills catalog, or a lightweight single-action confirmation step
(Forge's `WorkflowApprovalInstance` is a multi-step role-chain approval,
not a fit for "confirm this one natural-language action") — these are
real gaps:

  * `CatalystConversation` — a chat session, scoped by
    `(tenant_id, user_email)`, with an honest retention cutoff.
  * `CatalystMessage` — one turn (user or assistant) in a conversation,
    carrying the assistant's explainability trace inline.
  * `CatalystSkill` — the AI Skills Framework registry/catalog.
  * `CatalystPendingAction` — a short-lived confirm-token row gating any
    critical natural-language action before it executes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Message roles / types ───────────────────────────────────────────────────
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"
MESSAGE_ROLES = [MESSAGE_ROLE_USER, MESSAGE_ROLE_ASSISTANT]

MESSAGE_TYPE_TEXT = "text"
MESSAGE_TYPE_IMAGE = "image"
MESSAGE_TYPE_DOCUMENT = "document"
MESSAGE_TYPE_CHART = "chart"
MESSAGE_TYPE_VOICE = "voice"  # accepted as an input type only — see docs/catalyst/multi-modal note
MESSAGE_TYPES = [MESSAGE_TYPE_TEXT, MESSAGE_TYPE_IMAGE, MESSAGE_TYPE_DOCUMENT, MESSAGE_TYPE_CHART, MESSAGE_TYPE_VOICE]

# ── Conversation lifecycle ───────────────────────────────────────────────────
CONVERSATION_ACTIVE = "active"
CONVERSATION_ARCHIVED = "archived"
CONVERSATION_STATUSES = [CONVERSATION_ACTIVE, CONVERSATION_ARCHIVED]

# Real, honest retention limit — conversations are not fabricated as
# "forgotten" silently; anything past this window is excluded from recall
# and the conversation is marked archived rather than deleted.
CONVERSATION_RETENTION_DAYS = 90

# ── AI Skills Framework categories (Section 10) ─────────────────────────────
SKILL_INSPECTION = "inspection"
SKILL_DIGITAL_TWIN = "digital_twin"
SKILL_KNOWLEDGE_SEARCH = "knowledge_search"
SKILL_ANALYTICS = "analytics"
SKILL_FORECAST = "forecast"
SKILL_WORKFLOW = "workflow"
SKILL_RESEARCH = "research"
SKILL_REPORTING = "reporting"
SKILL_CATEGORIES = [
    SKILL_INSPECTION, SKILL_DIGITAL_TWIN, SKILL_KNOWLEDGE_SEARCH, SKILL_ANALYTICS,
    SKILL_FORECAST, SKILL_WORKFLOW, SKILL_RESEARCH, SKILL_REPORTING,
]

# ── Natural Language Actions (Section 3) ────────────────────────────────────
ACTION_ASSIGN_INSPECTION = "assign_inspection"
ACTION_GENERATE_REPORT = "generate_report"
ACTION_EXPORT_DASHBOARD = "export_dashboard"
ACTION_CREATE_CAPA_DRAFT = "create_capa_draft"
ACTION_NOTIFY_SUPERVISOR = "notify_supervisor"
ACTION_SCHEDULE_COMPETENCY_REVIEW = "schedule_competency_review"
ACTION_OPEN_DIGITAL_TWIN = "open_digital_twin"
ACTION_OPEN_KNOWLEDGE_ARTICLE = "open_knowledge_article"
ACTION_PUBLISH_WORKFLOW = "publish_workflow"
CATALYST_ACTION_TYPES = [
    ACTION_ASSIGN_INSPECTION, ACTION_GENERATE_REPORT, ACTION_EXPORT_DASHBOARD,
    ACTION_CREATE_CAPA_DRAFT, ACTION_NOTIFY_SUPERVISOR, ACTION_SCHEDULE_COMPETENCY_REVIEW,
    ACTION_OPEN_DIGITAL_TWIN, ACTION_OPEN_KNOWLEDGE_ARTICLE, ACTION_PUBLISH_WORKFLOW,
]
# Read-only "open X" navigation actions never need a confirmation step;
# everything that creates, publishes, or notifies does (Section 3: "Every
# critical action requires explicit confirmation").
CRITICAL_ACTION_TYPES = [
    ACTION_ASSIGN_INSPECTION, ACTION_CREATE_CAPA_DRAFT, ACTION_NOTIFY_SUPERVISOR,
    ACTION_SCHEDULE_COMPETENCY_REVIEW, ACTION_PUBLISH_WORKFLOW,
]

PENDING_ACTION_PENDING = "pending"
PENDING_ACTION_CONFIRMED = "confirmed"
PENDING_ACTION_CANCELLED = "cancelled"
PENDING_ACTION_EXPIRED = "expired"
PENDING_ACTION_STATUSES = [
    PENDING_ACTION_PENDING, PENDING_ACTION_CONFIRMED, PENDING_ACTION_CANCELLED, PENDING_ACTION_EXPIRED,
]
PENDING_ACTION_TTL_MINUTES = 15

DISCLAIMER = (
    "LumenAI Catalyst answers questions and drafts actions using only this tenant's real "
    "operational data and existing LumenAI services — it does not run a general-purpose "
    "language model, never claims causation, and never executes a critical action without "
    "explicit human confirmation. Every response is decision support only and requires "
    "human review before any clinical or operational action is taken."
)


class CatalystConversation(Base):
    """A copilot chat session, scoped by (tenant_id, user_email) — the same
    user-identity pairing `app/enterprise_auth.py` already resolves per
    request."""

    __tablename__ = "catalyst_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    persona: Mapped[str] = mapped_column(String(30), default="technician", nullable=False)  # executive|supervisor|technician
    title: Mapped[str] = mapped_column(String(255), default="New conversation", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=CONVERSATION_ACTIVE, nullable=False, index=True)


class CatalystMessage(Base):
    """One turn in a `CatalystConversation`, carrying the assistant's
    explainability trace inline so the Evidence Panel never has to be
    reconstructed after the fact."""

    __tablename__ = "catalyst_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    conversation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user|assistant
    message_type: Mapped[str] = mapped_column(String(20), default=MESSAGE_TYPE_TEXT, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    intent: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    skill_used: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class CatalystSkill(Base):
    """The AI Skills Framework registry (Section 10) — one row per
    independently-callable, independently-testable skill."""

    __tablename__ = "catalyst_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    skill_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CatalystPendingAction(Base):
    """A short-lived confirm-token row gating a critical natural-language
    action (Section 3) — deliberately lightweight, unlike Forge's
    multi-step `WorkflowApprovalInstance` chain, since this only ever
    gates one action behind one explicit "yes"."""

    __tablename__ = "catalyst_pending_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    conversation_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    params_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)

    confirm_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=PENDING_ACTION_PENDING, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(minutes=PENDING_ACTION_TTL_MINUTES),
        nullable=False,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
