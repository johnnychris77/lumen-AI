from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PacketReleaseHold(Base):
    __tablename__ = "packet_release_holds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    packet_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hold_type: Mapped[str] = mapped_column(String(100), nullable=False, default="compliance")
    reason: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    placed_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    placed_role: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cleared_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    cleared_role: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    cleared_notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
