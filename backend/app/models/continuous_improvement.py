"""v1.5 — Continuous Improvement Tracker.

Tracks named quality initiatives (e.g. "retrain on Kerrison box-lock
brushing") from proposal through completion. `actual_impact` is filled in by
a human once observed — never computed/inferred automatically, since a
before/after quality delta requires human judgment about what changed and
why, not just a raw metric diff.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

INITIATIVE_STATUSES: list[str] = ["proposed", "in_progress", "completed", "abandoned"]

# v4.7 Project Apollo — Continuous Improvement Portfolio methodologies
# (Section 8 of the brief); additive, not a new table.
METHODOLOGIES: list[str] = ["pi", "lean", "six_sigma", "kaizen", "other"]


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

    # v4.7 Project Apollo — Continuous Improvement Portfolio additions
    # (Section 8): methodology classification, cost savings, quality/risk
    # metrics, and executive visibility flag. All nullable/blank for older
    # rows and never fabricated — human-entered only, same as actual_impact.
    methodology: Mapped[str] = mapped_column(String(20), default="", nullable=False, index=True)
    cost_savings_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_improvement_metric: Mapped[str] = mapped_column(Text, default="", nullable=False)
    risk_reduction_metric: Mapped[str] = mapped_column(Text, default="", nullable=False)
    executive_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
