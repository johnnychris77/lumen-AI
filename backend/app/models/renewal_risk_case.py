from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RenewalRiskCase(Base):
    __tablename__ = "renewal_risk_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    playbook_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    health_snapshot_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False, default="watch")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open")
    trigger_reason: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    recommended_actions_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="[]")
    owner: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
