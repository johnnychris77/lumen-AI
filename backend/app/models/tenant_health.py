"""P14: Tenant health score model."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TenantHealthScore(Base):
    __tablename__ = "tenant_health_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    login_activity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inspection_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    override_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    support_tickets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_qbr_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
