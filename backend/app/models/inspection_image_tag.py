"""v1.2 — Image View Tagging.

Each image uploaded during Guided Capture is tagged with which anatomy zone
and image view it depicts, plus a technician-assessed capture quality and
optional notes. This is metadata about the *view*, not pixel-level detection —
the same "structured knowledge, not computer vision" honesty convention as the
rest of the anatomy/coverage engine (see app/services/instrument_anatomy.py).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Technician's own assessment of whether the captured image is usable.
CAPTURE_QUALITY_VALUES = ("good", "acceptable", "poor", "unusable")


class InspectionImageTag(Base):
    __tablename__ = "inspection_image_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    anatomy_zone: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    image_view: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    capture_quality: Mapped[str] = mapped_column(String(20), default="acceptable", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Optional — links to the retained-image store when image retention is
    # enabled; blank when only the hash-only convention applies.
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
