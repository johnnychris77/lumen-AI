from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountReviewPacket(Base):
    __tablename__ = "account_review_packets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    review_type: Mapped[str] = mapped_column(String(100), nullable=False, default="qbr")
    period_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    executive_summary: Mapped[str] = mapped_column(String(12000), nullable=False, default="")
    qbr_narrative: Mapped[str] = mapped_column(String(12000), nullable=False, default="")
    summary_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    risks_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="[]")
    next_steps_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
