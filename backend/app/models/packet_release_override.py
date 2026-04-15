from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PacketReleaseOverride(Base):
    __tablename__ = "packet_release_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    packet_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    override_type: Mapped[str] = mapped_column(String(100), nullable=False, default="emergency_release")
    justification: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    approved_role: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
