"""v1.4 — Technician competency tracking.

A lightweight event log the SPD Mentor Engine's competency service reads to
build per-technician summaries: findings reviewed, supervisor corrections,
repeated errors, and education completed. Deliberately separate from
SupervisorReview (the ML ground-truth label store) — this table tracks
technician learning/competency, not model performance.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompetencyEvent(Base):
    __tablename__ = "competency_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )
    technician: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # finding_reviewed | supervisor_correction | repeated_error | education_completed
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    finding_type: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
