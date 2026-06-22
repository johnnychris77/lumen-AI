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


class BenchmarkPublication(Base):
    """An immutable, dated archive of a published anonymized industry benchmark.

    Stores only anonymized aggregates + methodology — never raw tenant data."""

    __tablename__ = "accreditation_benchmark_publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    edition: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), default="annual_industry_benchmark", nullable=False)
    active_participants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # JSON-serialized anonymized aggregate payload + methodology
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False
    )
    published_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class AdvisoryBoardMember(Base):
    """A member of the certification/benchmark advisory board (Phase 6 governance)."""

    __tablename__ = "accreditation_advisory_board_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), default="member", nullable=False)
    organization: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    term_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    term_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    conflict_of_interest_disclosed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class CriteriaProposal(Base):
    """A proposed change to certification criteria or benchmark methodology that
    the advisory board reviews and signs off (Phase 6 review process)."""

    __tablename__ = "accreditation_criteria_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # certification_criteria | benchmark_methodology
    proposal_type: Mapped[str] = mapped_column(String(50), default="certification_criteria", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # proposed | under_review | approved | rejected
    status: Mapped[str] = mapped_column(String(30), default="proposed", nullable=False)
    proposed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    signed_off_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    signed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
