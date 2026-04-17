from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScheduledAccountReview(Base):
    __tablename__ = "scheduled_account_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    review_type: Mapped[str] = mapped_column(String(100), nullable=False, default="qbr")
    audience: Mapped[str] = mapped_column(String(100), nullable=False, default="executive")
    period_label_template: Mapped[str] = mapped_column(String(255), nullable=False, default="Quarterly Business Review")
    schedule_cron: Mapped[str] = mapped_column(String(100), nullable=False, default="0 8 1 */3 *")
    delivery_channel: Mapped[str] = mapped_column(String(50), nullable=False, default="email")
    delivery_target: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    distribution_list_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    include_docx: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_pptx: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_pdf: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
