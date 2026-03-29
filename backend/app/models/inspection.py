from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    stain_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    material_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)

    model_name: Mapped[str] = mapped_column(String(100), default="lumenai-baseline", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="0.1.0", nullable=False)
    inference_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    instrument_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    detected_issue: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    inference_mode: Mapped[str] = mapped_column(String(50), default="deterministic-fallback", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    vendor_name: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)

    alert_status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    alert_owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    alert_notes: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    alert_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    alert_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    qa_review_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    qa_reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    qa_review_notes: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    qa_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    qa_override_stain_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    qa_override_material_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    qa_override_instrument_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    qa_override_detected_issue: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    qa_override_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
