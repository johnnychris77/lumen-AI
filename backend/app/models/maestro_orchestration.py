"""LumenAI AI Specialist — Project Maestro: Operational Orchestration &
Decision Intelligence.

## Naming disambiguation (read this first)

"Orchestrator"/"orchestration" is already used by two unrelated, existing
systems: Phase 22's `app/agents/orchestrator.py` (`run_pipeline`, the
hardcoded 10-step per-inspection agent pipeline) and Nova's
`nova_orchestration_service.py` (`AgentTaskRun`, a configurable ordered
pipeline of `agent_key`s for Nova's own task platform). Maestro is a
**different, higher-level concept** -- an executive layer that reads the
*outputs* of every specialist (including both of those) to rank operational
priorities for SPD leadership. `maestro_orchestration_service.py` never
touches or extends either existing orchestration system.

## What Maestro composes rather than duplicates

Maestro is a pure read-and-synthesize layer over already-built specialists:

  * **Vision/Anatomy/Clinical Reasoning** — `app.agents.orchestrator.
    run_pipeline(db, inspection, tenant_id)` (Phase 22), computed live,
    never cached or re-derived.
  * **Knowledge** — `knowledge_graph_service.learning_confidence`.
  * **Digital Twin** — `instrument_condition_service.
    instrument_condition_history` (condition_trend).
  * **Veritas** — `veritas_evidence_agent_service.run_evidence_assessment`.
  * **Aegis** — `vulcan_aegis_integration_service.
    compute_process_variation_signal`.
  * **Vulcan** — `vulcan_reliability_agent_service.
    run_reliability_assessment`.
  * **Sage** — `sage_knowledge_gap_service.list_gaps` /
    `sage_learning_plan_service.list_plans`.
  * **Sentinel-X** — `sentinelx_risk_agent_service.run_risk_assessment` /
    `sentinelx_dashboard_service.risk_dashboard_summary` /
    `sentinelx_supervisor_workspace_service.supervisor_workspace_summary`.
  * **Pulse** — `pulse_command_center_service.pulse_command_center`.
  * **Phoenix** — `phoenix_maturity_index_service.
    compute_platform_maturity_index`.
  * **Forge** — `forge_approval_service` (the generic ordered-role approval
    chain, reused for executive-decision approval rather than a new gate)
    and `capa_suggestion_service.generate_capa_suggestions`/
    `create_capa_from_suggestion` for the "Generate CAPA draft"
    recommendation.
  * **Catalyst** — read-only reference; Maestro does not call Catalyst's
    conversational query engine, it produces its own structured
    recommendations.

## What is genuinely new in this file

Five tables: `MaestroPriorityItem` (Section 2), `MaestroRecommendation`
(Sections 3, 5), `MaestroDailyBrief` (Section 4), `MaestroOperationalHealthSnapshot`
(Section 7), `MaestroDecisionJournalEntry` (Section 8). The Strategy
Timeline (Section 6) is a query over `MaestroRecommendation`, not a
separate table.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2: Priority Engine categories ────────────────────────────────────
PRIORITY_HIGHEST_RISK_INSTRUMENT = "highest_risk_instrument"
PRIORITY_HIGHEST_RISK_WORKFLOW = "highest_risk_workflow"
PRIORITY_HIGHEST_RISK_FACILITY = "highest_risk_facility"
PRIORITY_HIGHEST_RISK_TECHNICIAN_EDUCATION_NEED = "highest_risk_technician_education_need"
PRIORITY_HIGHEST_RISK_EQUIPMENT = "highest_risk_equipment"
PRIORITY_HIGHEST_PRIORITY_CAPA = "highest_priority_capa"
PRIORITY_HIGHEST_PRIORITY_INSPECTION = "highest_priority_inspection"
PRIORITY_HIGHEST_PRIORITY_REPAIR = "highest_priority_repair"
PRIORITY_HIGHEST_PRIORITY_EXECUTIVE_ISSUE = "highest_priority_executive_issue"
PRIORITY_CATEGORIES = [
    PRIORITY_HIGHEST_RISK_INSTRUMENT, PRIORITY_HIGHEST_RISK_WORKFLOW, PRIORITY_HIGHEST_RISK_FACILITY,
    PRIORITY_HIGHEST_RISK_TECHNICIAN_EDUCATION_NEED, PRIORITY_HIGHEST_RISK_EQUIPMENT,
    PRIORITY_HIGHEST_PRIORITY_CAPA, PRIORITY_HIGHEST_PRIORITY_INSPECTION, PRIORITY_HIGHEST_PRIORITY_REPAIR,
    PRIORITY_HIGHEST_PRIORITY_EXECUTIVE_ISSUE,
]

# ── Section 3 & 5: Recommendation types ──────────────────────────────────────
RECOMMENDATION_MOVE_SUPERVISOR = "move_supervisor"
RECOMMENDATION_SCHEDULE_COMPETENCY = "schedule_competency"
RECOMMENDATION_REVIEW_CORROSION_TREND = "review_corrosion_trend"
RECOMMENDATION_ESCALATE_REPAIR_BACKLOG = "escalate_repair_backlog"
RECOMMENDATION_PUBLISH_BASELINE = "publish_baseline"
RECOMMENDATION_GENERATE_CAPA_DRAFT = "generate_capa_draft"
RECOMMENDATION_RESOURCE_ALLOCATION = "resource_allocation"
RECOMMENDATION_STAFFING_CHANGES = "staffing_changes"
RECOMMENDATION_INSPECTION_PRIORITIES = "inspection_priorities"
RECOMMENDATION_EQUIPMENT_UTILIZATION = "equipment_utilization"
RECOMMENDATION_EDUCATION_PRIORITIES = "education_priorities"
RECOMMENDATION_QUALITY_INITIATIVES = "quality_initiatives"
RECOMMENDATION_TYPES = [
    RECOMMENDATION_MOVE_SUPERVISOR, RECOMMENDATION_SCHEDULE_COMPETENCY, RECOMMENDATION_REVIEW_CORROSION_TREND,
    RECOMMENDATION_ESCALATE_REPAIR_BACKLOG, RECOMMENDATION_PUBLISH_BASELINE, RECOMMENDATION_GENERATE_CAPA_DRAFT,
    RECOMMENDATION_RESOURCE_ALLOCATION, RECOMMENDATION_STAFFING_CHANGES, RECOMMENDATION_INSPECTION_PRIORITIES,
    RECOMMENDATION_EQUIPMENT_UTILIZATION, RECOMMENDATION_EDUCATION_PRIORITIES, RECOMMENDATION_QUALITY_INITIATIVES,
]

# Section 6: Strategy Timeline tracking states.
DECISION_STATUS_PENDING = "pending"
DECISION_STATUS_COMPLETED = "completed"
DECISION_STATUS_BLOCKED = "blocked"
DECISION_STATUS_ESCALATED = "escalated"
DECISION_STATUS_DISMISSED = "dismissed"
DECISION_STATUSES = [
    DECISION_STATUS_PENDING, DECISION_STATUS_COMPLETED, DECISION_STATUS_BLOCKED,
    DECISION_STATUS_ESCALATED, DECISION_STATUS_DISMISSED,
]

# Section 6 timeline horizons.
TIMELINE_TODAY = "today"
TIMELINE_THIS_WEEK = "this_week"
TIMELINE_THIS_MONTH = "this_month"
TIMELINE_QUARTER = "quarter"
TIMELINE_YEAR = "year"
TIMELINE_HORIZONS = [TIMELINE_TODAY, TIMELINE_THIS_WEEK, TIMELINE_THIS_MONTH, TIMELINE_QUARTER, TIMELINE_YEAR]

# ── Section 4: Daily Operational Brief types ─────────────────────────────────
BRIEF_MORNING = "morning_brief"
BRIEF_AFTERNOON = "afternoon_update"
BRIEF_END_OF_DAY = "end_of_day_summary"
BRIEF_WEEKEND_READINESS = "weekend_readiness"
BRIEF_SHIFT_HANDOFF = "shift_handoff"
BRIEF_TYPES = [BRIEF_MORNING, BRIEF_AFTERNOON, BRIEF_END_OF_DAY, BRIEF_WEEKEND_READINESS, BRIEF_SHIFT_HANDOFF]

MAESTRO_AGENT_VERSION = "1.0.0"

DISCLAIMER = (
    "Maestro continuously coordinates all LumenAI specialists to recommend operational priorities for "
    "SPD leaders. It never replaces human leadership -- every recommendation is explainable, "
    "evidence-based, auditable, role-aware, and subject to human approval."
)


class MaestroPriorityItem(Base):
    """One ranked priority (Section 2) -- a persisted snapshot each time the
    Priority Engine runs, citing the real specialist output it was ranked
    from."""

    __tablename__ = "maestro_priority_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(300), default="", nullable=False, index=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_specialist: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class MaestroRecommendation(Base):
    """A leadership recommendation (Sections 3, 5) -- always advisory;
    `status` starts `pending` and only a human decision (recorded via the
    Decision Journal) moves it forward."""

    __tablename__ = "maestro_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    priority_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    recommendation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(300), default="", nullable=False, index=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    specialists_consulted_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    timeline_horizon: Mapped[str] = mapped_column(String(20), default=TIMELINE_TODAY, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=DECISION_STATUS_PENDING, nullable=False, index=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=MAESTRO_AGENT_VERSION, nullable=False)


class MaestroDailyBrief(Base):
    """A generated operational brief (Section 4)."""

    __tablename__ = "maestro_daily_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    brief_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    content_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MaestroOperationalHealthSnapshot(Base):
    """Operational Health Index (Section 7) -- composite across every named
    dimension, each a real, already-computed signal."""

    __tablename__ = "maestro_operational_health_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    workflow_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    education_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    equipment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    digital_twin_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    knowledge_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    enterprise_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    breakdown_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MaestroDecisionJournalEntry(Base):
    """Decision Journal (Section 8) -- every recommendation's evidence,
    consulted specialists, confidence, the leader's actual decision, the
    outcome, and lessons learned. This is the leadership knowledge base."""

    __tablename__ = "maestro_decision_journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    recommendation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    specialists_consulted_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)

    leader_decision: Mapped[str] = mapped_column(Text, default="", nullable=False)
    outcome: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lessons_learned: Mapped[str] = mapped_column(Text, default="", nullable=False)

    decided_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    decided_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
