"""P14: Manufacturer registration model."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ManufacturerRegistration(Base):
    __tablename__ = "manufacturer_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    manufacturer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    company_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    instruments_manufactured: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    registration_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")

    def get_instruments(self) -> list:
        try:
            return json.loads(self.instruments_manufactured)
        except Exception:
            return []
