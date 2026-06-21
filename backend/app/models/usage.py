"""P14: Usage metering model."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TenantUsageCounter(Base):
    __tablename__ = "tenant_usage_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    month_year: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    inspection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cap: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
