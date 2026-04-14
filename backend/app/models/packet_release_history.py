from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PacketReleaseHistory(Base):
    __tablename__ = "packet_release_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    release_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    packet_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, default="requested")
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    actor_role: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    details_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
