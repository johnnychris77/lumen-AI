"""P18: Strategic growth — partnerships and reference-customer program.

Tracks strategic partnerships (manufacturers, vendors, industry orgs, GPOs)
and the reference-customer program (case studies, pilot→enterprise
conversions). No raw cross-tenant data is stored here; partnership and
reference records are organization-level commercial metadata only.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StrategicPartnership(Base):
    __tablename__ = "strategic_partnerships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partner_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # manufacturer | vendor | industry_org | gpo
    partner_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # prospect | engaged | active | inactive
    status: Mapped[str] = mapped_column(String(50), default="prospect", nullable=False)
    tier: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    region: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # SLA tracking — next scheduled review/touchpoint for this partnership
    next_review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # set when status last advanced; used for stalled-engagement escalation
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class PartnershipNote(Base):
    """Timestamped engagement note / touchpoint on a strategic partnership."""

    __tablename__ = "partnership_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    partnership_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    author: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class NetworkBenchmarkSnapshot(Base):
    """Periodic snapshot of an anonymized network aggregate metric, enabling
    trend history. Stores only aggregate values (never per-tenant data) and
    carries the participant count so k-anonymity can be enforced at read time."""

    __tablename__ = "network_benchmark_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        index=True, nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    cohort: Mapped[str] = mapped_column(String(50), default="all", nullable=False)
    cohort_value: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    n_participants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    p50: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mean: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    captured_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class ReferenceCustomer(Base):
    __tablename__ = "reference_customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    facility_type: Mapped[str] = mapped_column(String(50), default="hospital", nullable=False)
    region: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    # pilot | converting | enterprise | reference
    conversion_stage: Mapped[str] = mapped_column(String(50), default="pilot", nullable=False)
    case_study_status: Mapped[str] = mapped_column(String(50), default="none", nullable=False)
    case_study_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    case_study_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    testimonial_status: Mapped[str] = mapped_column(String(50), default="none", nullable=False)
    customer_quote: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # consent gates — a customer is only externally citable when consented
    public_reference_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    modeled_annual_savings_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # snapshot of the P17 ROI calculator output, linked for case-study consistency
    roi_payback_months: Mapped[float | None] = mapped_column(Float, nullable=True)
    roi_captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
