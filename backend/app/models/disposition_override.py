"""v1.6 — Supervisor Disposition Workspace (Deliverable 6).

Records a supervisor's action on the AI's disposition recommendation:
approve as-is, or override it (modify, escalate, request reclean, request
repair, remove from service, require manufacturer review). A reason is
required for every action except a plain approval — enforced at the route,
not just the model.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# approve requires no reason; every other action does.
DISPOSITION_ACTIONS: list[str] = [
    "approve", "modify", "escalate", "reclean", "repair",
    "remove_from_service", "manufacturer_review",
]


class DispositionOverride(Base):
    __tablename__ = "disposition_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    reviewer_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    action: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    ai_recommended_disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    modified_disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
