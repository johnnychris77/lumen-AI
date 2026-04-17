from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountReviewExport(Base):
    __tablename__ = "account_review_exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_review_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    export_type: Mapped[str] = mapped_column(String(100), nullable=False, default="qbr")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    docx_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    pptx_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    pdf_path: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
