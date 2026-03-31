from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DigestSubscription(Base):
    __tablename__ = "digest_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_scope: Mapped[str] = mapped_column(String(100), default="executive", nullable=False)
    site_name: Mapped[str] = mapped_column(String(100), default="all", nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="slack", nullable=False)
    recipients: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    digest_type: Mapped[str] = mapped_column(String(50), default="weekly", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
