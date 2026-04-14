from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScheduledLeadershipPacket(Base):
    __tablename__ = "scheduled_leadership_packets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    briefing_type: Mapped[str] = mapped_column(String(100), nullable=False, default="board_packet")
    audience: Mapped[str] = mapped_column(String(100), nullable=False, default="executive")
    days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    schedule_cron: Mapped[str] = mapped_column(String(100), nullable=False, default="0 8 * * 1")
    delivery_channel: Mapped[str] = mapped_column(String(50), nullable=False, default="email")
    delivery_target: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    include_docx: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_pptx: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_pdf: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
