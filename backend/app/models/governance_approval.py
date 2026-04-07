from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GovernanceApproval(Base):
    __tablename__ = "governance_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    request_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_resource: Mapped[str] = mapped_column(String(100), nullable=False)
    target_resource_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    requested_role: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    requested_payload: Mapped[str] = mapped_column(String(4000), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    review_notes: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    execution_status: Mapped[str] = mapped_column(String(50), default="not_started", nullable=False)
    execution_notes: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
