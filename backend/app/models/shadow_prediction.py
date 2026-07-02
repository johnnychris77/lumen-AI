"""Phase 17 §9 — Shadow-mode predictions.

A shadow model runs silently: its prediction is stored but never shown as a
clinical recommendation. Once a supervisor records the final human decision, the
shadow prediction is compared to it — giving real, pre-deployment performance
evidence without ever influencing care.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ShadowPrediction(Base):
    __tablename__ = "shadow_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    model_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    model_type: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)

    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # The silent prediction — stored, never surfaced as a clinical recommendation.
    predicted_label: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    predicted_confidence: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    prediction_payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    # Filled in later when the human final decision is known (§9 comparison).
    supervisor_final_label: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    agreed_with_human: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Always true for shadow rows — a hard invariant the API relies on.
    shadow_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
