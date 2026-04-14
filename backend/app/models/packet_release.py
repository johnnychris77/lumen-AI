from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PacketRelease(Base):
    __tablename__ = "packet_releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    packet_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    packet_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    audience_type: Mapped[str] = mapped_column(String(100), nullable=False, default="executive")
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    requested_role: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    approver_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    approver_role: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    approval_notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    attestation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attestation_text: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
