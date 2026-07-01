"""Phase 15 §10 — Instrument Knowledge Library (extensible, multi-manufacturer).

Foundation for manufacturer/model-specific instrument knowledge: anatomy zones,
high-risk zones, known failure modes, maintenance interval, and repair/
replacement criteria. Deliberately NOT hardcoded to one manufacturer — entries
are data rows keyed by manufacturer + model + family.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InstrumentKnowledge(Base):
    __tablename__ = "instrument_knowledge"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    manufacturer: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    ifu_reference: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    # JSON-encoded lists (kept as text for portability across SQLite/Postgres).
    anatomy_zones: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    high_risk_zones: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    known_failure_modes: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    maintenance_interval: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    repair_criteria: Mapped[str] = mapped_column(Text, default="", nullable=False)
    replacement_criteria: Mapped[str] = mapped_column(Text, default="", nullable=False)
