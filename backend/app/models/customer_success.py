"""P17: Customer Success snapshots — persisted onboarding/training inputs and
computed health scores for reproducible, auditable CSM triage."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerSuccessSnapshot(Base):
    __tablename__ = "customer_success_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    captured_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # CSM-supplied inputs (0–100).
    onboarding_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    training_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Derived dimensions and composite captured at snapshot time.
    adoption_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    utilization_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="at_risk", nullable=False)
