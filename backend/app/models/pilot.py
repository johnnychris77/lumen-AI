"""P14: Pilot conversion gate model."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PilotStatus(Base):
    __tablename__ = "pilot_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    pilot_start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    pilot_end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agreed_kpis: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    current_kpis: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    conversion_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Shadow (Phase 6 — Prospective Shadow-Mode Clinical Validation) §2 —
    # pilot site configuration fields, additive to the pre-existing P14
    # pilot-conversion row. Blank/"" for pilots started before this pass.
    organization: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    department: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    clinical_lead: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    technical_lead: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    quality_lead: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    validation_coordinator: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # Advisor (Phase 7 — Supervised Advisory Pilot & Human-AI Collaboration)
    # §2 — the remaining pilot-governance roles/fields §2 requires that
    # weren't already covered by Shadow's additions above. success_criteria
    # is a distinct, structured narrative field — not a substitute for the
    # pre-existing agreed_kpis JSON (which is purely numeric target/actual
    # tracking). pilot_duration_days is the planned/target duration,
    # editable independently of the actual pilot_start_date/pilot_end_date
    # (e.g. when a pilot is extended, the dates change but the originally
    # agreed duration is worth keeping for reference).
    pilot_sponsor: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    product_owner: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    engineering_lead: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    success_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pilot_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def get_agreed_kpis(self) -> dict:
        try:
            return json.loads(self.agreed_kpis)
        except Exception:
            return {}

    def get_current_kpis(self) -> dict:
        try:
            return json.loads(self.current_kpis)
        except Exception:
            return {}
