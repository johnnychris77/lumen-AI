from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetentionEvent(Base):
    __tablename__ = "retention_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    legal_hold_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
