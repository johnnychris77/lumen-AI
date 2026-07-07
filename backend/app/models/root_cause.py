"""v1.5 — Root Cause Intelligence.

A finding can be categorized by its probable root cause (by a supervisor —
never inferred automatically, since guessing "why" a finding occurred without
a human judgment would be a fabricated causal claim). Recurring root causes
across inspections are what Root Cause Intelligence trends.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Accepted root-cause vocabulary. "unknown" is a legitimate, honest choice —
# not every finding has an identifiable cause at review time.
ROOT_CAUSES: list[str] = [
    "incomplete_manual_cleaning",
    "improper_brushing",
    "improper_flushing",
    "missed_inspection_zone",
    "poor_lighting",
    "image_quality",
    "instrument_damage",
    "manufacturer_wear",
    "unknown",
]


class RootCauseAssignment(Base):
    __tablename__ = "root_cause_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    root_cause: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    assigned_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
