from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneratedBriefing(Base):
    __tablename__ = "generated_briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    briefing_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    audience: Mapped[str] = mapped_column(String(100), nullable=False, default="executive")
    period_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    slide_outline_json: Mapped[str] = mapped_column(String(12000), nullable=False, default="[]")
    memo_text: Mapped[str] = mapped_column(String(12000), nullable=False, default="")
    summary_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
