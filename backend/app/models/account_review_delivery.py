from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountReviewDelivery(Base):
    __tablename__ = "account_review_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    account_review_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    export_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_channel: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    delivery_target: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    delivery_status: Mapped[str] = mapped_column(String(50), nullable=False, default="not_sent")
    result_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
