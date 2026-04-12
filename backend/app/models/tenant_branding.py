from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TenantBranding(Base):
    __tablename__ = "tenant_branding"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    logo_url: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    accent_color: Mapped[str] = mapped_column(String(50), nullable=False, default="#2563eb")
    welcome_text: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    export_prefix: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    support_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
