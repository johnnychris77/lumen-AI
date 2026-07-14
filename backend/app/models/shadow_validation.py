"""Shadow — Phase 6: Prospective Shadow-Mode Clinical Validation.

Three new, additive tables that Phase 6 introduces (distinct from the
pre-existing `ShadowPrediction` silent-prediction store, `SupervisorReview`
AI-agreement feedback, and `PilotStatus` pilot-conversion row, all of which
this sprint extends rather than duplicates — see docs/shadow-validation/):

* ``ShadowGroundTruth`` — §3's ground-truth registry: the full
  technician -> supervisor -> adjudicated finding chain for one inspection,
  with reviewer identities and per-stage timestamps. Distinct from
  ``SupervisorReview`` (a single reviewer's AI-agreement feedback) because
  no existing table captures the *original technician finding* alongside
  the supervisor's and a possible adjudicator's, in one place, with a
  reason for correction and supporting evidence.
* ``ShadowErrorReviewItem`` — §6's error review queue: a stateful review
  record (reviewer comments, resolution) auto-routed whenever the
  comparison engine finds anything other than agreement. Distinct from
  ``pilot_validation.safety_review_queue()`` (a computed, safety-specific
  view with no persisted reviewer workflow) because this covers *every*
  disagreement, not just safety-flagged ones, and tracks its own
  resolution state.
* ``ClinicalReviewBoardSession`` — §8's periodic review record: who
  reviewed, what they found, and their readiness recommendation for one
  candidate model. Feeds the Validated Candidate promotion gate
  (`app.services.ml.candidate_promotion`).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ShadowGroundTruth(Base):
    __tablename__ = "shadow_ground_truth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    # §3 — the original technician finding, captured before any review.
    technician_finding: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    technician_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    technician_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # §3 — the supervisor's finding.
    supervisor_finding: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    supervisor_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    supervisor_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # §3 — the final adjudicated finding. Blank until an adjudicator records
    # one; ground truth is the supervisor finding until then (see
    # shadow_ground_truth.final_finding()).
    final_adjudicated_finding: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    adjudicator_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    adjudicated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reason_for_correction: Mapped[str] = mapped_column(Text, default="", nullable=False)
    supporting_evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ShadowErrorReviewItem(Base):
    __tablename__ = "shadow_error_review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    shadow_prediction_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    model_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    human_decision: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    ai_prediction: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    comparison_category: Mapped[str] = mapped_column(String(30), default="", nullable=False, index=True)

    # §7 root cause, filled in by shadow_failure_analysis.
    failure_classification: Mapped[str] = mapped_column(String(40), default="", nullable=False, index=True)
    reviewer_comments: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # open | in_review | resolved
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    resolved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClinicalReviewBoardSession(Base):
    __tablename__ = "clinical_review_board_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    model_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    review_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # JSON list of {"name": ..., "role": ...} — SPD leadership, quality,
    # clinical advisors, AI engineering, product management (§8).
    reviewers_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    performance_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    failure_modes_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    operational_impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    readiness_assessment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommendations: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # None until the board records an explicit decision — never defaulted true.
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
