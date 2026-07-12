"""LumenAI AI Leadership Platform — Project Steward: Governed Action
Execution, Change Management & Benefits Realization.

## Naming disambiguation

**"Steward"** appears nowhere else in this codebase except as a human-role
label on two unrelated columns (`escalated_to_steward_at`,
`steward_decision`) on Olympus's P20 Network Intelligence recall-signal
model (`app/models/p20_network_intelligence.py`) — a cross-hospital
recall-escalation reviewer, not an agent. This file's `steward_`-free,
`GovernedAction`-prefixed tables never touch that model.

**"Pilot"** is a heavily-loaded, pre-existing namespace in this codebase
(`app/models/pilot.py`, `pilot_config.py`, `pilot_error_log.py`,
`app/routes/pilot*.py`) meaning a *customer/product* deployment pilot --
an entirely different concept from the brief's "pilot rollout" of one
governed action. To avoid a permanent, confusing namespace collision,
this file uses **`GovernedActionRollout`** / `rollout_scope` throughout
instead of any `pilot_*` symbol. The brief's own vocabulary ("single-
instrument pilot", "facility pilot", etc.) is preserved as data values in
`ROLLOUT_SCOPES`, never as a Python/table identifier.

## What Steward composes rather than duplicates

Steward is the governed execution layer for decisions *already* approved
elsewhere -- it never re-decides anything. A `GovernedAction` always
carries a `source_type` + `source_id` pointing back to the record that
was actually approved:

  * **Council** — `council_human_decision_service.decisions_for_case`
    (a `CouncilHumanDecision` row is the approval-of-record for
    `source_type="council_case"`)
  * **CAPA** — the existing `capa_service`/`capa_lifecycle_service`
    single `capas` table and its `open -> assigned -> in_progress ->
    verified -> closed` lifecycle are *not* duplicated here. A
    `GovernedAction` with `source_type="capa"` just links to that CAPA's
    id via `source_id`; Steward's own 15-status lifecycle (Section 3)
    tracks the *implementation* of the CAPA's corrective/preventive
    action, which is a materially richer, longer-running process
    (dependencies, rollout, benefits realization) than the CAPA record
    itself tracks.
  * **Sentinel-X** — `sentinelx_risk_scoring_service.compute_risk_score`
    is called twice (before/after) for `GovernedActionResidualRiskReview`
    rather than Steward inventing its own risk model.
  * **Veritas** — `veritas_evidence_agent_service` / `to_dict` supplies
    the evidence-sufficiency judgment gating high-risk closure.
  * **Sage** — `sage_knowledge_gap_service` / competency-completion
    services satisfy training dependencies; Steward never independently
    determines competency.
  * **Vulcan** — `vulcan_reliability_agent_service.run_reliability_assessment`
    supplies reliability-outcome measurement for reliability actions.
  * **Aegis** — `vulcan_aegis_integration_service.compute_process_variation_signal`
    supplies process-outcome measurement, kept separately traceable
    (never merged into Steward's own outcome record).
  * Escalation/notification follows the same "compute-and-return a list
    of notification dicts" pattern as `council_notification_service.
    combined_notifications` -- no new delivery channel.
  * Authority tiers reuse Council's exact `ROLE_AUTHORITY_TIER` mapping
    (`council_leadership.ROLE_AUTHORITY_TIER`) since the underlying RBAC
    is still only four real roles (viewer/operator/spd_manager/admin).

## What is genuinely new in this file

Seven tables: `GovernedAction` (Section 2), `GovernedActionAuditEvent`
(Sections 3, 24 -- append-only status/audit trail), `GovernedActionRollout`
(Section 8), `GovernedActionVerification` (Section 9),
`GovernedActionOutcomeReview` (Section 10), `GovernedActionUnintendedConsequence`
(Section 11), `GovernedActionResidualRiskReview` (Section 20). Dependency/
impact analysis (Section 6) and the decision-to-outcome timeline (Section
25) are computed live from these tables, never separately persisted.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2: Governed Action source types ──────────────────────────────────
SOURCE_COUNCIL_CASE = "council_case"
SOURCE_CAPA = "capa"
SOURCE_SENTINELX_RISK_ALERT = "sentinelx_risk_alert"
SOURCE_MAESTRO_RECOMMENDATION = "maestro_recommendation"
SOURCE_AEGIS_PROCESS_RECOMMENDATION = "aegis_process_recommendation"
SOURCE_VULCAN_RELIABILITY_RECOMMENDATION = "vulcan_reliability_recommendation"
SOURCE_SAGE_EDUCATION_RECOMMENDATION = "sage_education_recommendation"
SOURCE_VERITAS_EVIDENCE_REMEDIATION = "veritas_evidence_remediation"
SOURCE_PHOENIX_IMPROVEMENT_RECOMMENDATION = "phoenix_improvement_recommendation"
SOURCE_AUDIT_FINDING = "audit_finding"
SOURCE_POLICY_CHANGE = "policy_change"
SOURCE_LEADERSHIP_DIRECTIVE = "leadership_directive"
SOURCE_TYPES = [
    SOURCE_COUNCIL_CASE, SOURCE_CAPA, SOURCE_SENTINELX_RISK_ALERT, SOURCE_MAESTRO_RECOMMENDATION,
    SOURCE_AEGIS_PROCESS_RECOMMENDATION, SOURCE_VULCAN_RELIABILITY_RECOMMENDATION,
    SOURCE_SAGE_EDUCATION_RECOMMENDATION, SOURCE_VERITAS_EVIDENCE_REMEDIATION,
    SOURCE_PHOENIX_IMPROVEMENT_RECOMMENDATION, SOURCE_AUDIT_FINDING, SOURCE_POLICY_CHANGE,
    SOURCE_LEADERSHIP_DIRECTIVE,
]

# ── Section 3: Action lifecycle ───────────────────────────────────────────────
STATUS_DRAFT = "DRAFT"
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
STATUS_APPROVED = "APPROVED"
STATUS_READY_TO_START = "READY_TO_START"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_BLOCKED = "BLOCKED"
STATUS_AT_RISK = "AT_RISK"
STATUS_AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
STATUS_AWAITING_VERIFICATION = "AWAITING_VERIFICATION"
STATUS_COMPLETED_PENDING_REVIEW = "COMPLETED_PENDING_REVIEW"
STATUS_SUSTAIN = "SUSTAIN"
STATUS_REVISE = "REVISE"
STATUS_ESCALATE = "ESCALATE"
STATUS_CLOSED = "CLOSED"
STATUS_CANCELLED = "CANCELLED"
ACTION_STATUSES = [
    STATUS_DRAFT, STATUS_PENDING_APPROVAL, STATUS_APPROVED, STATUS_READY_TO_START, STATUS_IN_PROGRESS,
    STATUS_BLOCKED, STATUS_AT_RISK, STATUS_AWAITING_EVIDENCE, STATUS_AWAITING_VERIFICATION,
    STATUS_COMPLETED_PENDING_REVIEW, STATUS_SUSTAIN, STATUS_REVISE, STATUS_ESCALATE, STATUS_CLOSED,
    STATUS_CANCELLED,
]
# Terminal statuses that can never legally transition again (Section 24: a
# CLOSED/CANCELLED action can only be reopened by creating a new action that
# references it, never by mutating the closed row -- mirrors Council's
# CASE_STATUS_RESOLVED "reconvene rejected" invariant).
TERMINAL_STATUSES = {STATUS_CLOSED, STATUS_CANCELLED}

# ── Section 5: Action categories & types ──────────────────────────────────────
CATEGORY_CLINICAL_QUALITY = "clinical_quality"
CATEGORY_OPERATIONAL = "operational"
CATEGORY_EDUCATION = "education"
CATEGORY_RELIABILITY = "reliability"
CATEGORY_GOVERNANCE = "governance"
ACTION_CATEGORIES = [
    CATEGORY_CLINICAL_QUALITY, CATEGORY_OPERATIONAL, CATEGORY_EDUCATION, CATEGORY_RELIABILITY,
    CATEGORY_GOVERNANCE,
]

ACTION_TYPES_BY_CATEGORY = {
    CATEGORY_CLINICAL_QUALITY: [
        "recleaning_workflow_revision", "enhanced_inspection_requirement",
        "supervisor_review_threshold_change", "baseline_remediation", "anatomy_profile_update",
    ],
    CATEGORY_OPERATIONAL: [
        "workload_reassignment", "queue_priority_change", "staffing_adjustment_recommendation",
        "workflow_redesign", "equipment_use_change",
    ],
    CATEGORY_EDUCATION: [
        "targeted_microlearning", "competency_reassessment", "supervised_return_demonstration",
        "shift_based_education", "instrument_family_training",
    ],
    CATEGORY_RELIABILITY: [
        "repair_evaluation", "manufacturer_review", "increased_inspection_frequency", "quarantine",
        "retirement_review",
    ],
    CATEGORY_GOVERNANCE: [
        "policy_revision", "rule_revision", "workflow_approval", "knowledge_update", "model_review",
        "evidence_remediation",
    ],
}
ALL_ACTION_TYPES = [t for types in ACTION_TYPES_BY_CATEGORY.values() for t in types]

# ── Section 7: Change readiness ───────────────────────────────────────────────
READINESS_READY = "ready"
READINESS_PARTIALLY_READY = "partially_ready"
READINESS_NOT_READY = "not_ready"
READINESS_BLOCKED = "blocked"
READINESS_UNKNOWN = "unknown"
CHANGE_READINESS_STATES = [
    READINESS_READY, READINESS_PARTIALLY_READY, READINESS_NOT_READY, READINESS_BLOCKED, READINESS_UNKNOWN,
]

# ── Section 8: Rollout scope (see naming disambiguation above re: "pilot") ────
ROLLOUT_SINGLE_INSTRUMENT = "single_instrument"
ROLLOUT_SINGLE_WORKFLOW = "single_workflow"
ROLLOUT_SHIFT = "shift"
ROLLOUT_DEPARTMENT = "department"
ROLLOUT_FACILITY = "facility"
ROLLOUT_MARKET = "market"
ROLLOUT_ENTERPRISE = "enterprise"
ROLLOUT_SCOPES = [
    ROLLOUT_SINGLE_INSTRUMENT, ROLLOUT_SINGLE_WORKFLOW, ROLLOUT_SHIFT, ROLLOUT_DEPARTMENT,
    ROLLOUT_FACILITY, ROLLOUT_MARKET, ROLLOUT_ENTERPRISE,
]

# ── Section 10: Benefits realization classifications ──────────────────────────
BENEFITS_EXCEEDED = "exceeded_expectations"
BENEFITS_ACHIEVED = "achieved"
BENEFITS_PARTIALLY_ACHIEVED = "partially_achieved"
BENEFITS_NOT_ACHIEVED = "not_achieved"
BENEFITS_WORSENED = "worsened"
BENEFITS_INCONCLUSIVE = "inconclusive"
BENEFITS_CLASSIFICATIONS = [
    BENEFITS_EXCEEDED, BENEFITS_ACHIEVED, BENEFITS_PARTIALLY_ACHIEVED, BENEFITS_NOT_ACHIEVED,
    BENEFITS_WORSENED, BENEFITS_INCONCLUSIVE,
]

# ── Section 24: Closure outcomes ───────────────────────────────────────────────
CLOSURE_CLOSE_AND_SUSTAIN = "close_and_sustain"
CLOSURE_CLOSE_WITH_MONITORING = "close_with_monitoring"
CLOSURE_REVISE_AND_CONTINUE = "revise_and_continue"
CLOSURE_ESCALATE = "escalate"
CLOSURE_REOPEN_SOURCE_CASE = "reopen_source_case"
CLOSURE_ROLLBACK = "rollback"
CLOSURE_OUTCOMES = [
    CLOSURE_CLOSE_AND_SUSTAIN, CLOSURE_CLOSE_WITH_MONITORING, CLOSURE_REVISE_AND_CONTINUE,
    CLOSURE_ESCALATE, CLOSURE_REOPEN_SOURCE_CASE, CLOSURE_ROLLBACK,
]

RISK_LEVELS = ["low", "medium", "high", "critical"]
PRIORITIES = ["low", "medium", "high", "critical"]
HIGH_RISK_LEVELS = {"high", "critical"}

# ── Section 27: Authority -- reuse Council's exact role-to-tier mapping.
# Steward's own required-tier constants for specific gated operations
# (Section 23/24): approving a standard-risk action requires supervisor+
# (tier 1); approving/closing a high-risk action requires manager+ (tier 2).
from app.models.council_leadership import ROLE_AUTHORITY_TIER  # noqa: E402, F401

TIER_APPROVE_STANDARD = 1
TIER_APPROVE_HIGH_RISK = 2
TIER_CLOSE_STANDARD = 1
TIER_CLOSE_HIGH_RISK = 2
# Only a director/executive-tier ("admin") actor may approve or close an
# action outside their own configured facility (Section 23: "supervisor
# can approve only within configured scope"). This is deliberately the
# RBAC ceiling, not TIER_APPROVE_HIGH_RISK -- a manager-tier (spd_manager)
# actor satisfies the high-risk approval tier but is still facility-scoped.
TIER_CROSS_FACILITY_AUTHORITY = 4

STEWARD_AGENT_VERSION = "1.0.0"

DISCLAIMER = (
    "Steward converts approved decisions into governed implementation plans and tracks their execution, "
    "verification, and measured outcomes. Steward does not approve clinical or operational decisions -- it "
    "executes and monitors only actions authorized by the appropriate human role, and every action remains "
    "reversible and human-governed."
)


class GovernedAction(Base):
    """The typed Governed Action (Section 2) -- the durable record
    tracking an approved decision from implementation plan through
    closure. `source_type`/`source_id` point back to the record that was
    actually approved (a `CouncilHumanDecision`, a CAPA row, etc.);
    Steward never re-derives or overrides that approval."""

    __tablename__ = "governed_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    source_decision: Mapped[str] = mapped_column(Text, default="", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approval_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    action_title: Mapped[str] = mapped_column(String(300), nullable=False)
    action_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)

    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    accountable_leader: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    stakeholders_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)

    dependencies_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    milestones_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(30), default=STATUS_DRAFT, nullable=False, index=True)

    evidence_requirements_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    expected_outcomes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    success_metrics_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    actual_outcomes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    benefits_realization: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    unintended_consequences_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    change_readiness: Mapped[str] = mapped_column(String(30), default=READINESS_UNKNOWN, nullable=False)

    closure_decision: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    closure_approver: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=STEWARD_AGENT_VERSION, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class GovernedActionAuditEvent(Base):
    """Append-only status-transition/audit trail (Sections 3, 24, 27) --
    never mutated or deleted, including across a rollback, so a
    rollback's full history remains reconstructable."""

    __tablename__ = "governed_action_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    governed_action_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    from_status: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    changed_by_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)


class GovernedActionRollout(Base):
    """A phased-rollout stage of one Governed Action (Section 8). See the
    naming disambiguation at the top of this file for why this is
    `GovernedActionRollout`, never `Pilot*`."""

    __tablename__ = "governed_action_rollouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    governed_action_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rollout_scope: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_value: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    baseline_metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    expected_result: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actual_result: Mapped[str] = mapped_column(Text, default="", nullable=False)
    adverse_effects: Mapped[str] = mapped_column(Text, default="", nullable=False)
    user_feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)

    go_no_go_decision: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class GovernedActionVerification(Base):
    """One piece of completion evidence (Section 9). A checkbox alone is
    not sufficient for a high-risk action -- `sufficient` is set by
    Veritas's evidence-sufficiency judgment, never self-declared."""

    __tablename__ = "governed_action_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    governed_action_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verified_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sufficient: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    insufficiency_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)


class GovernedActionOutcomeReview(Base):
    """One benefits-realization measurement (Section 10). Compares one
    expected metric against its actual measured value; `classification`
    is only ever derived from a real actual-vs-expected comparison, never
    guessed when data is missing (that case is `inconclusive`)."""

    __tablename__ = "governed_action_outcome_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    governed_action_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification: Mapped[str] = mapped_column(String(30), default=BENEFITS_INCONCLUSIVE, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class GovernedActionUnintendedConsequence(Base):
    """A flagged unintended consequence (Section 11) -- flagging one
    never edits or removes the original implementation history it
    references."""

    __tablename__ = "governed_action_unintended_consequences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    governed_action_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    consequence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    supporting_evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class GovernedActionResidualRiskReview(Base):
    """Residual-risk review (Section 20) -- Sentinel-X's risk score is
    captured before, during, and after implementation. Closure of a
    high-risk action requires this row to exist and be reviewed."""

    __tablename__ = "governed_action_residual_risk_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    governed_action_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    risk_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_during: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
