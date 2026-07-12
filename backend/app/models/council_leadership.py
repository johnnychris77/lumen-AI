"""LumenAI AI Leadership Platform — Project Council: Multi-Agent Leadership
Teams & Governed Consensus Intelligence.

## Naming disambiguation

**"Council" already exists** in one unrelated context: Olympus's Network
Governance Council (`olympus_governance_council_service.py`,
`NetworkGovernanceCase` in `app/models/olympus_network.py`) -- a
cross-hospital, network-level governance body for intelligence-sharing
disputes between member sites. Project Council is a different,
single-tenant concept: structured AI leadership *teams* composed of
already-built LumenAI specialists, convened to review one operational or
clinical issue and produce a transparent, dissent-preserving
recommendation for human leadership. This file uses a distinct
`council_` prefix throughout and never touches `NetworkGovernanceCase` or
any Olympus table. `/council` and `/api/council` were unclaimed before
this sprint.

## What Council composes rather than duplicates

Council does not run its own clinical/operational analysis. Each
specialist's Council assessment is derived from that specialist's own,
already-built real service:

  * **Veritas** — `veritas_evidence_agent_service.run_evidence_assessment`
  * **Aegis** — `vulcan_aegis_integration_service.
    compute_process_variation_signal`
  * **Vulcan** — `vulcan_reliability_agent_service.
    run_reliability_assessment`
  * **Sage** — `sage_knowledge_gap_service.list_gaps`
  * **Sentinel-X** — `sentinelx_risk_agent_service.run_risk_assessment`
  * **Apollo** — `apollo_capa_engine_service.capa_engine_summary`
  * **Athena** — `athena_search_service.organizational_search`
  * **Pulse** — `pulse_command_center_service.pulse_command_center`
  * **Phoenix** — `phoenix_maturity_index_service.
    compute_platform_maturity_index`
  * **Maestro** — `maestro_priority_engine_service.latest_priorities`
  * **Research Agent** — `horizon_research_portal_service.
    research_portal_summary` (network-wide research/dataset activity;
    read-only reference for the Research and Innovation Council)

Reports reuse Veritas's already-generic `veritas_reports_service.
build_report_pdf_bytes` / `build_report_csv_bytes` / `build_report_xlsx_bytes`
rather than a new export library. Decision Journal integration reuses
Maestro's `maestro_decision_journal_service.record_decision` directly.

## What is genuinely new in this file

Eight tables: `CouncilTeamConfig` (Sections 2, 15), `CouncilCase`
(Section 3), `CouncilSpecialistAssessment` (Section 4),
`CouncilDissentRecord` (Section 6), `CouncilDecisionOption` (Section 7),
`CouncilHumanDecision` (Section 8), `CouncilMeetingNotes` (Section 12),
`CouncilOutcomeReview` (Section 14). Specialist performance (Section 17)
is computed on the fly from these tables -- never a separate,
independently-drifting scoreboard.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2 & 15: Leadership Team Registry ─────────────────────────────────
TEAM_CLINICAL_QUALITY = "clinical_quality"
TEAM_OPERATIONS = "operations"
TEAM_EDUCATION = "education"
TEAM_RELIABILITY = "reliability"
TEAM_EXECUTIVE = "executive"
TEAM_RESEARCH_INNOVATION = "research_innovation"
COUNCIL_TEAM_KEYS = [
    TEAM_CLINICAL_QUALITY, TEAM_OPERATIONS, TEAM_EDUCATION,
    TEAM_RELIABILITY, TEAM_EXECUTIVE, TEAM_RESEARCH_INNOVATION,
]

# Specialist keys used throughout Council (map onto real specialist services).
SPECIALIST_VERITAS = "veritas"
SPECIALIST_AEGIS = "aegis"
SPECIALIST_VULCAN = "vulcan"
SPECIALIST_SAGE = "sage"
SPECIALIST_SENTINELX = "sentinelx"
SPECIALIST_APOLLO = "apollo"
SPECIALIST_ATHENA = "athena"
SPECIALIST_PULSE = "pulse"
SPECIALIST_PHOENIX = "phoenix"
SPECIALIST_MAESTRO = "maestro"
SPECIALIST_RESEARCH_AGENT = "research_agent"

# Specialists whose unresolved dissent can never be majority-overridden
# (Section 5, 16) -- the safety- and evidence-integrity specialists.
SAFETY_VETO_SPECIALISTS = {SPECIALIST_SENTINELX, SPECIALIST_VERITAS}

DEFAULT_TEAM_DEFINITIONS = {
    TEAM_CLINICAL_QUALITY: {
        "team_name": "Clinical Quality Council",
        "required_specialists": [SPECIALIST_SENTINELX, SPECIALIST_VERITAS, SPECIALIST_APOLLO, SPECIALIST_ATHENA, SPECIALIST_VULCAN],
        "optional_specialists": [],
        "decision_scope": "High-risk findings, evidence quality, clinical significance, quality implications, institutional guidance.",
    },
    TEAM_OPERATIONS: {
        "team_name": "Operations Council",
        "required_specialists": [SPECIALIST_MAESTRO, SPECIALIST_AEGIS, SPECIALIST_PULSE, SPECIALIST_VULCAN, SPECIALIST_SENTINELX],
        "optional_specialists": [],
        "decision_scope": "Workload prioritization, workflow risk, repair impact, staffing pressure, immediate operational response.",
    },
    TEAM_EDUCATION: {
        "team_name": "Education Council",
        "required_specialists": [SPECIALIST_SAGE, SPECIALIST_AEGIS, SPECIALIST_ATHENA, SPECIALIST_APOLLO, SPECIALIST_VERITAS],
        "optional_specialists": [],
        "decision_scope": "Knowledge gaps, competency needs, approved educational content, effectiveness measurement.",
    },
    TEAM_RELIABILITY: {
        "team_name": "Reliability Council",
        "required_specialists": [SPECIALIST_VULCAN, SPECIALIST_VERITAS, SPECIALIST_SENTINELX, SPECIALIST_AEGIS, SPECIALIST_MAESTRO],
        "optional_specialists": [],
        "decision_scope": "Recurring instrument failure, repair recurrence, process exposure, clinical risk, disposition options.",
    },
    TEAM_EXECUTIVE: {
        "team_name": "Executive Council",
        "required_specialists": [SPECIALIST_MAESTRO, SPECIALIST_SENTINELX, SPECIALIST_PULSE, SPECIALIST_PHOENIX, SPECIALIST_APOLLO, SPECIALIST_AEGIS],
        "optional_specialists": [],
        "decision_scope": "Enterprise priorities, executive risks, resource options, quality priorities, strategic recommendations.",
    },
    TEAM_RESEARCH_INNOVATION: {
        "team_name": "Research and Innovation Council",
        "required_specialists": [SPECIALIST_PHOENIX, SPECIALIST_ATHENA, SPECIALIST_VERITAS, SPECIALIST_SENTINELX, SPECIALIST_RESEARCH_AGENT],
        "optional_specialists": [],
        "decision_scope": "New hypotheses, model improvements, evidence needs, pilots, research proposals, innovation opportunities.",
    },
}

# ── Section 3: Council Case types ────────────────────────────────────────────
CASE_HIGH_RISK_INSPECTION = "high_risk_inspection"
CASE_RECURRING_CONTAMINATION = "recurring_contamination"
CASE_RECURRING_INSTRUMENT_FAILURE = "recurring_instrument_failure"
CASE_REPAIR_RECURRENCE = "repair_recurrence"
CASE_PROCESS_VARIATION = "process_variation"
CASE_EDUCATION_NEED = "education_need"
CASE_CAPA_ESCALATION = "capa_escalation"
CASE_WORKFLOW_BOTTLENECK = "workflow_bottleneck"
CASE_ENTERPRISE_TREND = "enterprise_trend"
CASE_MODEL_PERFORMANCE_ISSUE = "model_performance_issue"
CASE_EVIDENCE_CONFLICT = "evidence_conflict"
CASE_INNOVATION_PROPOSAL = "innovation_proposal"
CASE_TYPES = [
    CASE_HIGH_RISK_INSPECTION, CASE_RECURRING_CONTAMINATION, CASE_RECURRING_INSTRUMENT_FAILURE,
    CASE_REPAIR_RECURRENCE, CASE_PROCESS_VARIATION, CASE_EDUCATION_NEED, CASE_CAPA_ESCALATION,
    CASE_WORKFLOW_BOTTLENECK, CASE_ENTERPRISE_TREND, CASE_MODEL_PERFORMANCE_ISSUE,
    CASE_EVIDENCE_CONFLICT, CASE_INNOVATION_PROPOSAL,
]

# Default team routed to for each case type -- organizations may override
# per-tenant via CouncilTeamConfig, but this is the out-of-the-box mapping.
CASE_TYPE_DEFAULT_TEAM = {
    CASE_HIGH_RISK_INSPECTION: TEAM_CLINICAL_QUALITY,
    CASE_RECURRING_CONTAMINATION: TEAM_CLINICAL_QUALITY,
    CASE_RECURRING_INSTRUMENT_FAILURE: TEAM_RELIABILITY,
    CASE_REPAIR_RECURRENCE: TEAM_RELIABILITY,
    CASE_PROCESS_VARIATION: TEAM_OPERATIONS,
    CASE_EDUCATION_NEED: TEAM_EDUCATION,
    CASE_CAPA_ESCALATION: TEAM_CLINICAL_QUALITY,
    CASE_WORKFLOW_BOTTLENECK: TEAM_OPERATIONS,
    CASE_ENTERPRISE_TREND: TEAM_EXECUTIVE,
    CASE_MODEL_PERFORMANCE_ISSUE: TEAM_RESEARCH_INNOVATION,
    CASE_EVIDENCE_CONFLICT: TEAM_CLINICAL_QUALITY,
    CASE_INNOVATION_PROPOSAL: TEAM_RESEARCH_INNOVATION,
}

CASE_STATUS_OPEN = "open"
CASE_STATUS_AWAITING_EVIDENCE = "awaiting_evidence"
CASE_STATUS_AWAITING_DECISION = "awaiting_decision"
CASE_STATUS_RESOLVED = "resolved"
CASE_STATUS_CLOSED = "closed"
CASE_STATUSES = [
    CASE_STATUS_OPEN, CASE_STATUS_AWAITING_EVIDENCE, CASE_STATUS_AWAITING_DECISION,
    CASE_STATUS_RESOLVED, CASE_STATUS_CLOSED,
]

# ── Section 5: Consensus Engine outcomes ─────────────────────────────────────
CONSENSUS_UNANIMOUS = "UNANIMOUS"
CONSENSUS_STRONG = "STRONG_CONSENSUS"
CONSENSUS_CONDITIONAL = "CONDITIONAL_CONSENSUS"
CONSENSUS_SPLIT = "SPLIT_DECISION"
CONSENSUS_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
CONSENSUS_SAFETY_DISSENT = "SAFETY_DISSENT"
CONSENSUS_STATUSES = [
    CONSENSUS_UNANIMOUS, CONSENSUS_STRONG, CONSENSUS_CONDITIONAL,
    CONSENSUS_SPLIT, CONSENSUS_INSUFFICIENT_EVIDENCE, CONSENSUS_SAFETY_DISSENT,
]

# ── Section 8: Human decision authority ──────────────────────────────────────
# LumenAI's actual RBAC has four roles (admin/spd_manager/operator/viewer).
# Council layers the brief's five-tier authority scale on top of them: a
# case's `required_approval_tier` is checked against the deciding user's
# tenant role, mapped through ROLE_AUTHORITY_TIER below.
APPROVER_TECHNICIAN = "technician"
APPROVER_SUPERVISOR = "supervisor"
APPROVER_SPD_MANAGER = "spd_manager"
APPROVER_DIRECTOR = "director"
APPROVER_CLINICAL_QUALITY_GOVERNANCE = "clinical_quality_governance"
APPROVAL_TIER_BY_ROLE_NAME = {
    APPROVER_TECHNICIAN: 0,
    APPROVER_SUPERVISOR: 1,
    APPROVER_SPD_MANAGER: 2,
    APPROVER_DIRECTOR: 3,
    APPROVER_CLINICAL_QUALITY_GOVERNANCE: 4,
}
# Tenant role (`current_user["role"]`) -> maximum authority tier it holds.
# viewer/operator are technician-equivalent (view only, tier 0); spd_manager
# covers supervisor+manager scope (tier 2); admin covers director +
# clinical/quality governance (tier 4, the ceiling).
ROLE_AUTHORITY_TIER = {"viewer": 0, "operator": 0, "spd_manager": 2, "admin": 4}

# ── Section 14: Outcome Effectiveness classifications ────────────────────────
OUTCOME_EFFECTIVE = "effective"
OUTCOME_PARTIALLY_EFFECTIVE = "partially_effective"
OUTCOME_INEFFECTIVE = "ineffective"
OUTCOME_UNINTENDED_CONSEQUENCE = "unintended_consequence"
OUTCOME_INSUFFICIENT_FOLLOW_UP = "insufficient_follow_up_data"
OUTCOME_CLASSIFICATIONS = [
    OUTCOME_EFFECTIVE, OUTCOME_PARTIALLY_EFFECTIVE, OUTCOME_INEFFECTIVE,
    OUTCOME_UNINTENDED_CONSEQUENCE, OUTCOME_INSUFFICIENT_FOLLOW_UP,
]

COUNCIL_AGENT_VERSION = "1.0.0"

DISCLAIMER = (
    "Council convenes LumenAI's specialist agents as a structured leadership team to synthesize evidence, "
    "surface agreement and disagreement, and evaluate tradeoffs. Council does not replace leadership -- "
    "no recommendation may hide specialist disagreement, and every final decision requires human approval "
    "at the appropriate authority level."
)


class CouncilTeamConfig(Base):
    """A configurable AI leadership team (Sections 2, 15) -- append-only
    versioned: updating a team's configuration inserts a new row with an
    incremented `version` rather than mutating history, the same
    append-only audit pattern used by Veritas's baseline governance
    actions."""

    __tablename__ = "council_team_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    team_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    team_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    required_specialists_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    optional_specialists_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    decision_scope: Mapped[str] = mapped_column(Text, default="", nullable=False)
    escalation_rules: Mapped[str] = mapped_column(Text, default="", nullable=False)
    quorum_requirement: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    safety_veto_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evidence_requirements: Mapped[str] = mapped_column(Text, default="", nullable=False)
    review_frequency: Mapped[str] = mapped_column(String(50), default="quarterly", nullable=False)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(30), default="approved", nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class CouncilCase(Base):
    """The typed Council Case (Section 3) -- the durable record a
    leadership team convenes around."""

    __tablename__ = "council_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    case_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_event: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    inspection_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    instrument_ids_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    digital_twin_refs_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    evidence_package_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    risk_level: Mapped[str] = mapped_column(String(20), default="", nullable=False, index=True)
    urgency: Mapped[str] = mapped_column(String(20), default="routine", nullable=False)
    requested_decision: Mapped[str] = mapped_column(Text, default="", nullable=False)

    team_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    participating_specialists_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    consensus_status: Mapped[str] = mapped_column(String(30), default="", nullable=False, index=True)
    recommended_action: Mapped[str] = mapped_column(Text, default="", nullable=False)

    required_human_approver: Mapped[str] = mapped_column(String(50), default=APPROVER_SUPERVISOR, nullable=False)
    required_approval_tier: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    status: Mapped[str] = mapped_column(String(30), default=CASE_STATUS_OPEN, nullable=False, index=True)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=COUNCIL_AGENT_VERSION, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class CouncilSpecialistAssessment(Base):
    """One specialist's independent assessment of a Council Case (Section
    4) -- immutable once submitted. If a specialist revises its
    conclusion after seeing other assessments, the original row is never
    edited; a new row is inserted with `is_revision=True` and
    `supersedes_assessment_id` pointing back to it."""

    __tablename__ = "council_specialist_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    council_case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    specialist_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    evidence_used_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    evidence_limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    significance: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    alternative_explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), default="routine", nullable=False)
    human_role_required: Mapped[str] = mapped_column(String(50), default=APPROVER_SUPERVISOR, nullable=False)

    is_revision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supersedes_assessment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class CouncilDissentRecord(Base):
    """A dissent record (Section 6) -- always displayed prominently, never
    hidden from the final report."""

    __tablename__ = "council_dissent_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    council_case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dissenting_specialist: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    disputed_conclusion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_supporting_dissent: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risk_if_ignored: Mapped[str] = mapped_column(Text, default="", nullable=False)
    additional_evidence_required: Mapped[str] = mapped_column(Text, default="", nullable=False)
    proposed_alternative_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    escalation_level: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)


class CouncilDecisionOption(Base):
    """One decision option with tradeoffs (Section 7). `financial_impact`
    is left empty unless a real, supportable estimate exists -- Council
    never fabricates a financial figure."""

    __tablename__ = "council_decision_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    council_case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    option_label: Mapped[str] = mapped_column(String(20), nullable=False)
    option_title: Mapped[str] = mapped_column(String(300), nullable=False)
    benefits: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risks: Mapped[str] = mapped_column(Text, default="", nullable=False)

    clinical_risk: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    operational_impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    financial_impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence_strength: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    reversibility: Mapped[str] = mapped_column(String(20), default="reversible", nullable=False)
    required_authority: Mapped[str] = mapped_column(String(50), default=APPROVER_SUPERVISOR, nullable=False)
    expected_time_to_resolution: Mapped[str] = mapped_column(String(100), default="", nullable=False)


class CouncilHumanDecision(Base):
    """The final human decision on a Council Case (Section 8) --
    Council's own output is only ever a recommendation until this row
    exists."""

    __tablename__ = "council_human_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    council_case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    approver: Mapped[str] = mapped_column(String(255), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(50), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    conditions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )


class CouncilMeetingNotes(Base):
    """Structured Council Meeting Mode record (Section 12).
    `discussion_notes` is human-authored only -- Council never presents
    AI-generated discussion as human meeting content, enforced by
    requiring a non-empty `recorded_by` for any notes to be saved."""

    __tablename__ = "council_meeting_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    council_case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    agenda_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    discussion_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    action_items_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recorded_by: Mapped[str] = mapped_column(String(255), nullable=False)


class CouncilOutcomeReview(Base):
    """Outcome Effectiveness Review (Section 14) -- links back to the
    original Council Case and recommendation to close the learning
    loop."""

    __tablename__ = "council_outcome_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    council_case_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    issue_resolved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    recurred: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    risk_decreased: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    operational_performance_improved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    recommendation_followed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dissent_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    additional_evidence_changed_decision: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    knowledge_update_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    classification: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
