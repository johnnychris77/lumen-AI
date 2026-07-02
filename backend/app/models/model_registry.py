"""Phase 17 §5 — Model Registry.

One row per trained model version: what it is, which dataset it came from, how it
scored, its known limitations, and its approval status. This is the source of
truth for the deployment gate — a recommendation may only be driven by a model
whose registry stage permits it.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelRegistryEntry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    model_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)  # task key
    dataset_version: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    training_date: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    # not_started | training | trained | failed
    training_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)

    # JSON-encoded metrics + limitations (portable across SQLite/Postgres).
    evaluation_metrics: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    known_limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # experimental | pilot | validated | deprecated
    approval_status: Mapped[str] = mapped_column(
        String(20), default="experimental", nullable=False, index=True
    )
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    release_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
