"""P19: Industry Standardization, Accreditation Integration & Ecosystem Leadership.

Models supporting accreditation-readiness tracking (Joint Commission, DNV, CMS,
HFAP, state survey), the readiness/evidence/risk scoring engine, survey-evidence
packages, and the certification program.

These store organization-level accreditation metadata and references to a
facility's own evidence — never raw cross-tenant data. All scoring is a
readiness-support indicator that requires human review; nothing here guarantees
accreditation or claims regulatory approval / FDA clearance.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccreditationProgram(Base):
    """A facility's engagement with a specific accrediting body."""

    __tablename__ = "accreditation_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    # joint_commission | dnv | cms | hfap | state
    accreditor: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    # preparing | scheduled | surveyed | accredited | inactive
    status: Mapped[str] = mapped_column(String(50), default="preparing", nullable=False)
    survey_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    survey_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class EvidenceItem(Base):
    """A single piece of survey evidence tracked toward accreditation readiness."""

    __tablename__ = "accreditation_evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    accreditor: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    # reference standard, e.g. "AAMI ST79", "Joint Commission IC.02.02.01"
    standard_ref: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="general", nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    # missing | in_progress | complete
    status: Mapped[str] = mapped_column(String(50), default="missing", nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ReadinessAssessment(Base):
    """A persisted, reproducible snapshot of readiness/evidence/risk scoring."""

    __tablename__ = "accreditation_readiness_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    accreditor: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_completeness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    readiness_status: Mapped[str] = mapped_column(String(30), default="not_ready", nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    captured_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class SurveyEvidencePackage(Base):
    """A generated survey binder / compliance report / audit evidence package."""

    __tablename__ = "accreditation_evidence_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    accreditor: Mapped[str] = mapped_column(String(50), nullable=False)
    # binder | compliance_report | audit_evidence
    package_type: Mapped[str] = mapped_column(String(50), default="binder", nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    complete_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    generated_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class CertifiedSite(Base):
    """A facility's certification under a LumenAI ecosystem-leadership program."""

    __tablename__ = "accreditation_certified_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    facility_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    # certified_site | baseline_excellence | inspection_intelligence
    certification_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    level: Mapped[str] = mapped_column(String(30), default="standard", nullable=False)
    # applicant | in_review | certified | expired
    status: Mapped[str] = mapped_column(String(30), default="applicant", nullable=False)
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
