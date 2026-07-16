"""Lumen Decision Engine & Observation Doctrine — foundational models.

Implements the persistence layer for the 19-section "LumenAI Clinical
Reasoning & Inspection Workflow" doctrine:

  - `BaselineDecisionPolicy` — governed, org-configurable Baseline Decision
    Policy (Sections 5, 6, 8). Resolution hierarchy and simulation read this
    table; only rows with status="active" may influence a live
    recommendation.
  - `LumenDecisionRecord` — the immutable, persisted Result Contract
    (Section 14) produced for a single inspection by the Lumen Decision
    Engine (Section 10). The original AI observation fields are never
    overwritten by a later human decision (Section 16/18) — human
    corrections are recorded in separate `human_*` columns alongside the
    untouched original.
  - `UnknownFindingReview` — the Unknown-Finding Learning Loop (Section 13).
    A supervisor classification here never itself modifies production code,
    taxonomy, or model behavior; it is only a candidate for a future,
    independently-validated retraining cycle.

This module composes with, rather than replaces, the existing
`baseline_comparison_scoring_service.analyze_inspection()` pipeline and the
existing `readiness_engine`/`disposition_engine` chain — those remain the
source of the underlying finding/severity/disposition computation. This
file adds the governed-policy and doctrine-compliant recommendation layer
on top of them.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 8 — Policy Governance vocabulary ────────────────────────────────
POLICY_STATUSES = [
    "draft", "pending_approval", "approved", "active",
    "superseded", "archived", "rejected",
]

# ── Section 5 — Baseline Decision Policy configurable scopes ────────────────
POLICY_SCOPES = [
    "health_system", "market", "facility", "department",
    "instrument_family", "manufacturer", "model", "anatomy_zone",
    "finding_category", "lumenai_default",
]

# ── Section 6 — Policy Resolution Hierarchy (most specific first) ──────────
POLICY_RESOLUTION_ORDER = [
    "model", "instrument_family", "anatomy_zone", "department",
    "facility", "health_system", "lumenai_default",
]

ROLES_MAY_PUBLISH_POLICY = {"admin", "spd_manager"}


class BaselineDecisionPolicy(Base):
    """Section 5/6/8 — a single governed Baseline Decision Policy."""

    __tablename__ = "baseline_decision_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    policy_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    organization_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    scope: Mapped[str] = mapped_column(String(30), nullable=False)
    # The specific value the scope applies to (facility name, instrument
    # family key, anatomy zone key, model name, ...). Blank for org-wide
    # (health_system) or the LumenAI default policy.
    scope_value: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    policy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")

    baseline_source_requirement: Mapped[str] = mapped_column(String(100), default="any_approved", nullable=False)

    # Baseline-similarity thresholds (0.0-1.0). See Section 5's worked
    # default: 90-100 continue, 70-89 technician review, <70 supervisor.
    pass_threshold: Mapped[float] = mapped_column(Float, default=0.90, nullable=False)
    technician_review_threshold: Mapped[float] = mapped_column(Float, default=0.70, nullable=False)
    supervisor_attention_threshold: Mapped[float] = mapped_column(Float, default=0.70, nullable=False)
    supervisor_approval_threshold: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Section 4 — this text is stored for governance visibility only; the
    # contamination override itself is always enforced in code
    # (lumen_decision_engine.py) and can never be weakened by policy data.
    contamination_override_rule: Mapped[str] = mapped_column(
        Text, default="Probable contamination always requires reclean and reinspect, "
        "regardless of baseline similarity.", nullable=False,
    )
    structural_damage_rule: Mapped[str] = mapped_column(
        Text, default="Probable structural damage always requires supervisor attention.", nullable=False,
    )
    unknown_finding_rule: Mapped[str] = mapped_column(
        Text, default="Any finding outside the validated taxonomy always requires supervisor review.",
        nullable=False,
    )

    author: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approving_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    supporting_reference: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    previous_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class LumenDecisionRecord(Base):
    """Section 14/16 — the immutable Result Contract for one inspection.

    `observation_*`, `assessment_*`, and `policy_*` fields are the original
    AI-produced values and are set exactly once, at creation. A later human
    decision is captured in the `human_*` columns without ever mutating the
    original fields — this is what Section 16/18 mean by "the original AI
    observation remains immutable after human correction."
    """

    __tablename__ = "lumen_decision_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # -- Observation layer (Section 1-2-3A) --
    observation_category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    observation_display_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    observation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    observation_status: Mapped[str] = mapped_column(String(40), default="model_observation", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    # -- Assessment layer (Section 3B) --
    image_quality: Mapped[str] = mapped_column(String(30), default="not_assessed", nullable=False)
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    anatomy_zone: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    anatomy_zone_risk: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    baseline_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_deviation: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    baseline_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    digital_twin_trend: Mapped[str] = mapped_column(String(30), default="not_available", nullable=False)

    # -- Policy layer (Section 3C policy resolution, Section 6/16) --
    policy_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    policy_version: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    policy_scope: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    threshold_used: Mapped[float | None] = mapped_column(Float, nullable=True)

    # -- Recommendation layer (Section 3C / 14) --
    recommended_action: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    supervisor_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    escalation_condition: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # -- Auditability (Section 16) --
    limitations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # -- Human follow-through (never overwrites the original fields above) --
    technician_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    technician_actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    technician_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supervisor_action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    supervisor_actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supervisor_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_human_decision: Mapped[str | None] = mapped_column(String(60), nullable=True)


class UnknownFindingReview(Base):
    """Section 13 — Unknown-Finding Learning Loop.

    Created whenever the Decision Engine observes a signal for a category
    the deployed model is not validated on (`UNKNOWN_REVIEW_REQUIRED`).
    Supervisor classification here is a candidate-dataset annotation only;
    it never itself changes production taxonomy or model behavior.
    """

    __tablename__ = "unknown_finding_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    anatomy_zone: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    model_output: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    model_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_limitations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    # Review workflow: pending_supervisor -> classified -> second_review -> adjudicated
    status: Mapped[str] = mapped_column(String(30), default="pending_supervisor", nullable=False, index=True)
    supervisor_classification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supervisor_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    supervisor_actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    second_review_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    adjudicated_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dataset_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usage_rights: Mapped[str] = mapped_column(String(255), default="", nullable=False)
