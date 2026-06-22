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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


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
    testimonial_status: Mapped[str] = mapped_column(String(50), default="none", nullable=False)
    # consent gates — a customer is only externally citable when consented
    public_reference_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    modeled_annual_savings_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
