"""Advisor — Phase 7: Supervised Advisory Pilot & Human-AI Collaboration.

Three new, additive tables:

* ``AdvisoryRecommendationInteraction`` — §1/§4: the technician-facing
  accept/modify/reject decision on an AI recommendation. Distinct from
  ``SupervisorReview`` (a supervisor/manager-only AI-agreement feedback
  store, role-gated to admin/spd_manager and used by pilot_validation.py,
  ground_truth.py, and competency scoring) because no existing table lets
  the *technician* who receives the recommendation act on it directly —
  their role previously ended at capture/submission.
* ``AdvisoryUserFeedback`` — §7: structured UX feedback from any pilot
  participant role, distinct from Sage's learning-plan feedback and
  Vulcan's instrument-reliability feedback (different domains).
* ``AdvisorySafetyEvent`` — §8: a persisted, reviewable safety concern
  log specific to the advisory pilot, distinct from the generic
  ``PilotErrorLog`` (operational failures — upload/AI-analysis/report-
  generation errors, no clinical-safety review workflow).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdvisoryRecommendationInteraction(Base):
    __tablename__ = "advisory_recommendation_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    predicted_label: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # accepted | modified | rejected
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    modified_to: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    reason_for_rejection: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewer_comments: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # 1-5, how confident the human felt in their own decision. Nullable —
    # never defaulted, since an unrated interaction is real, missing data.
    user_confidence_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # §4/§14 — the audit trail: who decided, in what role, and how long it
    # took from the AI's analysis being available to this decision.
    decided_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    decided_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    time_to_decision_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)


class AdvisoryUserFeedback(Base):
    __tablename__ = "advisory_user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    submitted_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    # technician | supervisor | manager | quality | biomedical_engineering
    submitted_role: Mapped[str] = mapped_column(String(50), default="", nullable=False, index=True)

    # §7 — each 1-5, nullable (a respondent may skip a dimension).
    ease_of_use: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trust: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clarity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explainability_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    perceived_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suggestions: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AdvisorySafetyEvent(Base):
    __tablename__ = "advisory_safety_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    model_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # unsafe_recommendation | near_miss | repeated_override |
    # unexpected_behavior | model_failure | workflow_failure |
    # critical_incident
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # low | medium | high | critical
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)
    reported_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # Every safety concern requires review (§8) — never auto-closed.
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
