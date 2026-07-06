"""v1.5 — Quality Intelligence: per-finding detection log.

Inspection only stores the rolled-up disposition (risk_level, recommended_action,
overall_cleaning_assessment) — not which individual finding types were actually
detected. Finding Trend Intelligence, the Anatomy Risk Dashboard, and Instrument
Family Performance all need real per-finding-type, per-zone data to aggregate
over time, so this logs one row per actionable finding (severity_index >= 1)
at analysis time — never fabricated after the fact.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InspectionFinding(Base):
    __tablename__ = "inspection_findings"

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
    instrument_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False, index=True)

    finding_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    severity_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
