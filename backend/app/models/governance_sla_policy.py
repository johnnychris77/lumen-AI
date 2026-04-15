from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GovernanceSlaPolicy(Base):
    __tablename__ = "governance_sla_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    threshold_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    escalation_channel: Mapped[str] = mapped_column(String(50), nullable=False, default="email")
    escalation_target: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
