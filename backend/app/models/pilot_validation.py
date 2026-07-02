"""Phase 18 — Real-World Pilot Validation ground-truth store.

Each row is one supervisor-adjudicated pilot inspection: what the AI predicted,
what the supervisor confirmed, and the resulting confusion-matrix label
(true/false positive/negative or inconclusive). This is the labeled dataset
that clinical-performance, zone-performance, the safety queue, and the
validation report are all computed from — no fabricated numbers.

Governance: ground_truth_label is always derived server-side from
ai_prediction + supervisor_finding (see services/pilot_validation_service.py),
never accepted directly from the client, so the label can't be gamed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PilotValidationCase(Base):
    __tablename__ = "pilot_validation_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    supervisor_review_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Study cohort tracking
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    baseline_source: Mapped[str] = mapped_column(String(50), default="none", nullable=False)
    has_baseline: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    finding_type: Mapped[str] = mapped_column(String(60), default="none", nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(30), default="none", nullable=False)
    disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    # AI prediction snapshot
    ai_prediction: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ai_recommended_disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    # Supervisor ground truth
    supervisor_finding: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    supervisor_zone_correction: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewer_rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Derived — never client-supplied.
    ground_truth_label: Mapped[str] = mapped_column(String(20), default="inconclusive", nullable=False, index=True)
    is_critical_finding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Provenance for the validation report.
    dataset_version: Mapped[str] = mapped_column(String(50), default="pilot-v1", nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
