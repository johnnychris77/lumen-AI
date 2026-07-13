"""LumenAI AI Specialist — Project Oracle: Clinical Intelligence Scientist &
Discovery Engine.

## Naming disambiguation

**"Oracle"** appears nowhere else in this codebase as a system/table name.
The only pre-existing near-collision is `app/services/oracle_*` -- there is
none; a grep across `app/` turns up zero prior `Oracle`-prefixed symbols, so
this file introduces the namespace cleanly.

**"Pilot"** is reused here only as the data value `"PILOT_STUDY"` inside
`VALIDATION_STAGES` (the brief's own vocabulary for one stage of the 8-stage
scientific validation pipeline -- a *hypothesis's* pilot study, not a
customer/product deployment pilot). Exactly like Project Steward's
`ROLLOUT_SCOPES` decision, this never becomes a table or class name --
there is no `Pilot*` class in this file -- so it does not collide with the
pre-existing `app/models/pilot.py` / `pilot_config.py` customer-pilot
namespace.

**"Trend"** -- Horizon already owns network-wide, cross-tenant emerging-
trend detection (`app/models/federated_horizon.py::EmergingTrendAlert`,
`horizon_trend_detection_service.detect_emerging_trends`), which requires
`horizon_participation_service.list_enrolled_tenant_ids` to have at least
`EARLY_WARNING_K` peer tenants enrolled. `OracleTrendObservation` in this
file is deliberately **tenant-scoped**, working directly off one tenant's
own data with no network-enrollment precondition, so a single-tenant
deployment still gets trend discovery. The two are complementary, never
merged: Oracle may *cite* a Horizon `EmergingTrendAlert` by id as supporting
evidence on a hypothesis, but never recomputes or duplicates Horizon's
algorithm.

## What Oracle composes rather than duplicates

Oracle is a **discovery and research** specialist -- it observes, proposes,
and tracks hypotheses through a mandatory human-gated validation pipeline;
it never changes a production rule, policy, or model automatically.

  * **Sentinel-X** — `sentinel_ai_health_service.compute_ai_health` is the
    single source of AI drift/confidence/calibration truth. Oracle's
    `OracleModelObservation.ai_health_snapshot_json` stores that function's
    own returned dict verbatim; it never recomputes drift detection.
  * **Apollo** — `apollo_quality_twin_service.twin_history` supplies the
    governance-health digital-twin trajectory behind
    `OracleDigitalTwinInsight` rows with `source_service="apollo_quality_twin"`.
  * **Vulcan** — `vulcan_progression_service.compute_progression` /
    `findings_timeline` supplies the per-instrument finding-progression
    trajectory behind `OracleDigitalTwinInsight` rows with
    `source_service="vulcan_progression"`. Both twin sources are stored by
    reference/snapshot, never re-derived.
  * **Knowledge** — a promoted `OracleKnowledgeSuggestion` does not write
    `app/models/knowledge.py::KnowledgeArticle` directly. It creates a
    `GovernanceApproval` row (the same generic governance-approval table
    Steward and pre-existing routes use), using the modern 4-role RBAC
    (never the legacy `"tenant_admin"`/`"site_admin"` roles seen in one
    pre-existing route) -- only once that approval is granted does
    `knowledge_article_id` get populated by the existing
    `knowledge_governance_service` workflow.
  * **Authority tiers** reuse Council's exact `ROLE_AUTHORITY_TIER` mapping,
    the same convention Steward already established.

## Non-negotiable framing constraints (see repository CLAUDE.md)

Oracle never claims causation. `hypothesis_statement`, `outcome`, and every
generated summary field must be phrased as a *potential association* or
*possible contributing factor* requiring quality review -- enforced at the
service layer, not just documented here. Every hypothesis and trend/twin/
model observation carries `human_review_required=True` by default and an
explicit `disclaimer`. **Oracle may not bypass any validation-pipeline
stage** -- `OracleStageTransition` is the append-only audit trail the
service layer uses to enforce forward-one-stage-at-a-time (or a jump to the
terminal `REJECTED` stage from any non-terminal stage).

## What is genuinely new in this file

Six tables: `OracleHypothesis` (Sections 5, 11 -- the Research Registry
record), `OracleStageTransition` (Sections 10, 17 -- append-only validation-
pipeline audit trail), `OracleTrendObservation` (Section 4), `OracleDigitalTwinInsight`
(Section 5), `OracleModelObservation` (Section 7), `OracleKnowledgeSuggestion`
(Section 6). The 8-stage validation pipeline (Section 10) is enforced by the
service layer against `VALIDATION_STAGES`, never separately persisted as a
table.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 3: Discovery categories ───────────────────────────────────────────
CATEGORY_PROCESS_PATTERN = "process_pattern"
CATEGORY_INSTRUMENT_RELIABILITY_TREND = "instrument_reliability_trend"
CATEGORY_EDUCATION_EFFECTIVENESS = "education_effectiveness"
CATEGORY_EQUIPMENT_UTILIZATION = "equipment_utilization"
CATEGORY_STAFFING_WORKLOAD_CORRELATION = "staffing_workload_correlation"
CATEGORY_POLICY_EFFECTIVENESS = "policy_effectiveness"
CATEGORY_CROSS_DEPARTMENT_VARIATION = "cross_department_variation"
CATEGORY_SEASONAL_TEMPORAL_PATTERN = "seasonal_temporal_pattern"
CATEGORY_EMERGING_RISK_SIGNAL = "emerging_risk_signal"
CATEGORY_AI_MODEL_PERFORMANCE_DRIFT = "ai_model_performance_drift"
CATEGORY_DIGITAL_TWIN_DIVERGENCE = "digital_twin_divergence"
CATEGORY_KNOWLEDGE_GAP = "knowledge_gap"
DISCOVERY_CATEGORIES = [
    CATEGORY_PROCESS_PATTERN, CATEGORY_INSTRUMENT_RELIABILITY_TREND, CATEGORY_EDUCATION_EFFECTIVENESS,
    CATEGORY_EQUIPMENT_UTILIZATION, CATEGORY_STAFFING_WORKLOAD_CORRELATION, CATEGORY_POLICY_EFFECTIVENESS,
    CATEGORY_CROSS_DEPARTMENT_VARIATION, CATEGORY_SEASONAL_TEMPORAL_PATTERN, CATEGORY_EMERGING_RISK_SIGNAL,
    CATEGORY_AI_MODEL_PERFORMANCE_DRIFT, CATEGORY_DIGITAL_TWIN_DIVERGENCE, CATEGORY_KNOWLEDGE_GAP,
]

# ── Section 5: Confidence levels (never "proven" -- Oracle never claims
# causation, only an evidence-graded degree of association) ──────────────────
CONFIDENCE_EXPLORATORY = "exploratory"
CONFIDENCE_EMERGING = "emerging"
CONFIDENCE_MODERATE = "moderate"
CONFIDENCE_STRONG = "strong"
CONFIDENCE_LEVELS = [CONFIDENCE_EXPLORATORY, CONFIDENCE_EMERGING, CONFIDENCE_MODERATE, CONFIDENCE_STRONG]

# ── Section 10: 8-stage validation pipeline. Oracle may not bypass any
# stage -- the service layer only allows a forward move to the next entry in
# this list, or a move to the terminal STAGE_REJECTED from any non-terminal
# stage. ───────────────────────────────────────────────────────────────────────
STAGE_OBSERVATION = "OBSERVATION"
STAGE_HYPOTHESIS = "HYPOTHESIS"
STAGE_EVIDENCE_REVIEW = "EVIDENCE_REVIEW"
STAGE_SCIENTIFIC_VALIDATION = "SCIENTIFIC_VALIDATION"
STAGE_PILOT_STUDY = "PILOT_STUDY"
STAGE_CLINICAL_REVIEW = "CLINICAL_REVIEW"
STAGE_GOVERNANCE_APPROVAL = "GOVERNANCE_APPROVAL"
STAGE_PRODUCTION_KNOWLEDGE = "PRODUCTION_KNOWLEDGE"
STAGE_REJECTED = "REJECTED"
VALIDATION_STAGES = [
    STAGE_OBSERVATION, STAGE_HYPOTHESIS, STAGE_EVIDENCE_REVIEW, STAGE_SCIENTIFIC_VALIDATION,
    STAGE_PILOT_STUDY, STAGE_CLINICAL_REVIEW, STAGE_GOVERNANCE_APPROVAL, STAGE_PRODUCTION_KNOWLEDGE,
]
TERMINAL_STAGES = {STAGE_PRODUCTION_KNOWLEDGE, STAGE_REJECTED}

# ── Hypothesis outcome classification ─────────────────────────────────────────
OUTCOME_PENDING = ""
OUTCOME_PROMOTED = "promoted_to_knowledge"
OUTCOME_REJECTED = "rejected"
OUTCOME_WITHDRAWN = "withdrawn"
OUTCOME_INCONCLUSIVE = "inconclusive"
HYPOTHESIS_OUTCOMES = [OUTCOME_PENDING, OUTCOME_PROMOTED, OUTCOME_REJECTED, OUTCOME_WITHDRAWN, OUTCOME_INCONCLUSIVE]

# ── Section 6: Knowledge-suggestion status ────────────────────────────────────
SUGGESTION_PENDING = "pending"
SUGGESTION_APPROVED = "approved"
SUGGESTION_REJECTED = "rejected"
SUGGESTION_PUBLISHED = "published"
KNOWLEDGE_SUGGESTION_STATUSES = [SUGGESTION_PENDING, SUGGESTION_APPROVED, SUGGESTION_REJECTED, SUGGESTION_PUBLISHED]

TREND_DIRECTIONS = ["increasing", "decreasing", "stable", "volatile"]

# ── Authority -- reuse Council's exact role-to-tier mapping (same convention
# Steward established). Approving a knowledge-evolution governance request or
# promoting a hypothesis to PRODUCTION_KNOWLEDGE requires manager+ (tier 2).
from app.models.council_leadership import ROLE_AUTHORITY_TIER  # noqa: E402, F401

TIER_APPROVE_KNOWLEDGE_SUGGESTION = 2
TIER_PROMOTE_TO_PRODUCTION_KNOWLEDGE = 2

ORACLE_AGENT_VERSION = "1.0.0"

DISCLAIMER = (
    "Oracle surfaces explainable research hypotheses and discovery signals from governed enterprise data for "
    "scientific review. Oracle never changes a production rule, policy, or model automatically, and it never "
    "claims causation -- every output describes a potential association or possible contributing factor, "
    "graded by confidence level, and requires human scientific and clinical review before any production use. "
    "human_review_required is always true."
)


class OracleHypothesis(Base):
    """The Research Registry record (Sections 5, 11) -- a research
    hypothesis and its full life through the 8-stage validation pipeline.
    `hypothesis_statement` and `outcome` must always be phrased as a
    potential association, never a causal claim -- enforced by the
    service layer that writes these fields."""

    __tablename__ = "oracle_hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    hypothesis_code: Mapped[str] = mapped_column(String(50), default="", nullable=False, index=True)
    discovery_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)

    observation_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hypothesis_statement: Mapped[str] = mapped_column(Text, default="", nullable=False)
    supporting_literature_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    related_instruments_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    related_anatomy_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    digital_twin_refs_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    knowledge_links_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    statistical_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    confidence_level: Mapped[str] = mapped_column(String(20), default=CONFIDENCE_EXPLORATORY, nullable=False)
    current_stage: Mapped[str] = mapped_column(String(30), default=STAGE_OBSERVATION, nullable=False, index=True)
    research_owner: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)

    outcome: Mapped[str] = mapped_column(String(30), default=OUTCOME_PENDING, nullable=False)
    outcome_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rejected_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=ORACLE_AGENT_VERSION, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class OracleStageTransition(Base):
    """Append-only validation-pipeline audit trail (Sections 10, 17) --
    the mechanism by which the service layer proves 'Oracle may not
    bypass any stage': every row records exactly one forward-adjacent
    stage move, or a move to the terminal REJECTED stage."""

    __tablename__ = "oracle_stage_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    hypothesis_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    from_stage: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    to_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    changed_by_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    gate_check_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)


class OracleTrendObservation(Base):
    """A tenant-scoped emerging-trend observation (Section 4). See the
    naming disambiguation at the top of this file for why this is
    deliberately independent of Horizon's network-wide
    `EmergingTrendAlert` rather than a duplicate of it."""

    __tablename__ = "oracle_trend_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    trend_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    observation_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observation_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_points_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    direction: Mapped[str] = mapped_column(String(20), default="stable", nullable=False)
    magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    statistical_confidence: Mapped[str] = mapped_column(String(20), default="low", nullable=False)

    promoted_to_hypothesis_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class OracleDigitalTwinInsight(Base):
    """An insight derived from an existing digital-twin trajectory
    (Section 5) -- `underlying_snapshot_json` stores a reference/copy of
    Apollo's or Vulcan's own already-computed output, never a
    re-derivation of it."""

    __tablename__ = "oracle_digital_twin_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    source_service: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_reference: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    insight_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    underlying_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), default=CONFIDENCE_EXPLORATORY, nullable=False)

    promoted_to_hypothesis_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class OracleModelObservation(Base):
    """An AI Model Observatory observation (Section 7) --
    `ai_health_snapshot_json` stores Sentinel-X's own
    `compute_ai_health` return dict verbatim; Oracle never recomputes
    drift or calibration."""

    __tablename__ = "oracle_model_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    model_scope: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    observation_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ai_health_snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)

    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    promoted_to_hypothesis_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class OracleKnowledgeSuggestion(Base):
    """A suggested Knowledge Article (Section 6) awaiting governance
    approval -- `knowledge_article_id` is only ever populated after a
    linked `GovernanceApproval` row is granted and the existing
    `knowledge_governance_service` workflow creates the real article;
    Oracle never writes `KnowledgeArticle` directly."""

    __tablename__ = "oracle_knowledge_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    hypothesis_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    suggested_article_title: Mapped[str] = mapped_column(String(300), nullable=False)
    suggested_article_body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    governance_approval_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    knowledge_article_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=SUGGESTION_PENDING, nullable=False, index=True)
    submitted_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
