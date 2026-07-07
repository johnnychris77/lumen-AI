"""v1.4 — Supervisor Coaching Dashboard review store.

Captures a supervisor's review of the SPD Mentor Engine's coaching output for
an inspection — approve as-is, edit the recommendation, and/or add an
educational comment. Deliberately separate from SupervisorReview (which
captures AI-agreement for ML ground truth) — this table tracks coaching
quality/effectiveness, not model performance.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MentorCoachingReview(Base):
    __tablename__ = "mentor_coaching_reviews"

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

    approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    edited_recommendation: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    educational_comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
