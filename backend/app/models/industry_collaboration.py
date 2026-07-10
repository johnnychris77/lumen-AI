"""v3.5 — Project Beacon: Collaborative Quality Ecosystem & Industry
Intelligence Platform.

## Reuse map (researched before writing any of this file)

Project Beacon is the 9th cross-tenant/collaboration sprint in this
codebase. Before adding a single new table, the following pre-existing
infrastructure was identified and is reused directly rather than
duplicated:

  * **Participant roster + Advisory Board membership** —
    `app/models/p24_standards.py::AdvisoryConsortiumMember` already has
    everything Sections 1 and 10 need (`organization_type`,
    `membership_tier`, `membership_status`, `governance_roles`,
    `voting_rights`). Its `organization_type` vocabulary was extended
    with `"repair_vendor"` and `"research_partner"` (in
    `app/routes/p24_standards.py::enroll_consortium`) rather than
    building a second membership model here.
  * **Versioned standards/guidance publications** (Section 4) — reuses
    `p24_standards.py::StandardsPublication` directly, which gained a
    nullable `supersedes_id` column for real version chaining.
  * **Clinical evidence** (Section 5) — reuses Horizon's
    `federated_horizon.py::ClinicalEvidenceReference` /
    `RecommendationEvidenceLink`, whose `EVIDENCE_TYPES` vocabulary was
    extended with `case_report` / `quality_improvement_initiative` /
    `best_practice`.
  * **Industry benchmarking** (Section 8) — reuses
    `horizon_benchmark_service.py` / `federated_horizon.py::
    BENCHMARK_METRICS`, extended with `repair_category_rate` and
    `digital_twin_health_score` rather than a sixth percentile engine.
  * **Manufacturer feedback loop / knowledge sharing** (Section 6) —
    reuses `horizon_contribution_service.py::KnowledgeContribution`
    (already true cross-organization, de-identified, approval-gated).
  * **Repair Partner Portal / Digital Twin sync** (Section 3) — reuses
    `or_connect_vendor_service.py`'s real-identity-filtered query pattern
    and `digital_twin_engine.log_instrument_flow` directly for the
    "repair outcomes update Digital Twins" hook; `RepairRequest` gained a
    nullable `failure_category` column (`app/models/or_connect.py`).
  * **Governance / audit trail** (Section 9) — reuses this platform's
    single `AuditLog` table (`app/audit.py::log_audit_event`), the same
    mechanism every prior sprint's governance center uses. No second
    audit store.

## What is genuinely new in this file

Nothing pre-existing covered aggregate repair-cause intelligence
snapshots, or a real Advisory Board meeting/action-item/recommendation
tracking structure (P24's `AdvisoryConsortiumMember` is a membership
roster, not a meeting tracker) — those are the four additive tables
below.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Repair Intelligence snapshot cadence (Section 7) ────────────────────────
SNAPSHOT_MONTHLY = "monthly"
SNAPSHOT_QUARTERLY = "quarterly"
SNAPSHOT_PERIODS = [SNAPSHOT_MONTHLY, SNAPSHOT_QUARTERLY]

# ── Advisory Board meeting lifecycle (Section 10) ───────────────────────────
MEETING_SCHEDULED = "scheduled"
MEETING_COMPLETED = "completed"
MEETING_CANCELLED = "cancelled"
MEETING_STATUSES = [MEETING_SCHEDULED, MEETING_COMPLETED, MEETING_CANCELLED]

ACTION_OPEN = "open"
ACTION_IN_PROGRESS = "in_progress"
ACTION_DONE = "done"
ACTION_STATUSES = [ACTION_OPEN, ACTION_IN_PROGRESS, ACTION_DONE]

RECOMMENDATION_PROPOSED = "proposed"
RECOMMENDATION_UNDER_REVIEW = "under_review"
RECOMMENDATION_ADOPTED = "adopted"
RECOMMENDATION_DECLINED = "declined"
RECOMMENDATION_STATUSES = [
    RECOMMENDATION_PROPOSED, RECOMMENDATION_UNDER_REVIEW, RECOMMENDATION_ADOPTED, RECOMMENDATION_DECLINED,
]

DISCLAIMER = (
    "LumenAI Industry Collaboration Hub shares only governance-approved, de-identified, "
    "aggregate quality intelligence across organizations. It never exposes another "
    "organization's raw data, patient information, or identity. Outputs describe potential "
    "associations only, never causation, and require human review before any action is taken."
)


class RepairIntelligenceSnapshot(Base):
    """A persisted aggregate repair-cause/outcome snapshot (Section 7).

    Distinct from any single tenant's or vendor's own repair history —
    this row is a network-wide, k-anonymity-gated rollup produced by
    `beacon_repair_intelligence_service.py`, never a raw per-organization
    repair count.
    """

    __tablename__ = "beacon_repair_intelligence_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    period: Mapped[str] = mapped_column(String(20), default=SNAPSHOT_MONTHLY, nullable=False, index=True)

    failure_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    facility_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_repairs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repeat_repair_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_turnaround_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_improvement_recommendation: Mapped[str] = mapped_column(Text, default="", nullable=False)

    suppressed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AdvisoryBoardMeeting(Base):
    """An Industry Advisory Board meeting (Section 10)."""

    __tablename__ = "beacon_advisory_board_meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=MEETING_SCHEDULED, nullable=False, index=True)
    attendee_organizations: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON list
    meeting_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    roadmap_feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class AdvisoryBoardActionItem(Base):
    """An action item arising from an Advisory Board meeting (Section 10)."""

    __tablename__ = "beacon_advisory_board_action_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    meeting_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ACTION_OPEN, nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdvisoryBoardRecommendation(Base):
    """A recommendation the Advisory Board has proposed for review cycles /
    product roadmap (Section 10). Advisory only — never auto-applied."""

    __tablename__ = "beacon_advisory_board_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    meeting_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    target_area: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RECOMMENDATION_PROPOSED, nullable=False, index=True)
    review_cycle: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    decided_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
