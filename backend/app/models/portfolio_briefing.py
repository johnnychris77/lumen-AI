from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PortfolioBriefing(Base):
    __tablename__ = "portfolio_briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    briefing_type: Mapped[str] = mapped_column(String(100), nullable=False, default="board_portfolio")
    audience: Mapped[str] = mapped_column(String(100), nullable=False, default="board")
    period_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    executive_summary: Mapped[str] = mapped_column(String(12000), nullable=False, default="")
    board_narrative: Mapped[str] = mapped_column(String(12000), nullable=False, default="")
    summary_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="{}")
    top_risks_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="[]")
    next_steps_json: Mapped[str] = mapped_column(String(4000), nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
