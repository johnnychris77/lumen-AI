from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GovernanceRollback(Base):
    __tablename__ = "governance_rollbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    approval_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_resource: Mapped[str] = mapped_column(String(100), nullable=False)
    target_resource_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    before_state: Mapped[str] = mapped_column(String(4000), default="", nullable=False)
    after_state: Mapped[str] = mapped_column(String(4000), default="", nullable=False)
    rollback_status: Mapped[str] = mapped_column(String(50), default="available", nullable=False, index=True)
    rollback_notes: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    rolled_back_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
