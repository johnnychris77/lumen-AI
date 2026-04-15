from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerHealthSnapshot(Base):
    __tablename__ = "customer_health_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    health_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    usage_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    governance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adoption_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_flags_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="[]")
    summary_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
