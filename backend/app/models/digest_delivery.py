from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DigestDelivery(Base):
    __tablename__ = "digest_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    digest_type: Mapped[str] = mapped_column(String(50), default="weekly", nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    recipients: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_code: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    failure_reason: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    delivery_batch_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    payload_summary: Mapped[str] = mapped_column(String(4000), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
