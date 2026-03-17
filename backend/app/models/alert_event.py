from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    vendor_name: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    detected_issue: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_code: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    failure_reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    dispatch_batch_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
