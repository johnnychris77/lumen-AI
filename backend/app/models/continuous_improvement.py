"""v1.5 — Continuous Improvement Tracker.

Tracks named quality initiatives (e.g. "retrain on Kerrison box-lock
brushing") from proposal through completion. `actual_impact` is filled in by
a human once observed — never computed/inferred automatically, since a
before/after quality delta requires human judgment about what changed and
why, not just a raw metric diff.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

INITIATIVE_STATUSES: list[str] = ["proposed", "in_progress", "completed", "abandoned"]


class ContinuousImprovementInitiative(Base):
    __tablename__ = "continuous_improvement_initiatives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )
    initiative: Mapped[str] = mapped_column(String(500), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    target_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False, index=True)
    expected_impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actual_impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
