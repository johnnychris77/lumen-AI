"""Supervisor AI-agreement feedback — the human-in-the-loop label store.

Captures whether a supervisor agrees with the AI's clinical review, their
rationale, and any override. This is deliberately a separate table from the
inspection's qa_* fields so the agreement signal can be exported as labeled
training data and aggregated for model-performance monitoring.

Governance: only admin/spd_manager submit reviews; comments are required for
partial-agreement, disagreement, and override; every review is audit-logged.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SupervisorReview(Base):
    __tablename__ = "supervisor_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    reviewer_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    # agree | partially_agree | disagree
    agreement: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Optional disposition override the supervisor applied.
    override_action: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    # Snapshot of what the AI said, for training-data provenance.
    ai_recommendation: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    ai_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Zone-aware feedback (instrument high-risk zone detection) — labeled data.
    finding_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    zone_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    corrected_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    corrected_severity: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    final_disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)
