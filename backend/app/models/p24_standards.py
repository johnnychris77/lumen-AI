"""P24: Global Healthcare Intelligence Ecosystem & Standards Leadership — SQLAlchemy models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


# ---------------------------------------------------------------------------
# Phase 1: Quality Standards
# ---------------------------------------------------------------------------


class QualityStandard(Base):
    """Published quality classification standard for instrument inspection."""

    __tablename__ = "p24_quality_standards"

    id = Column(Integer, primary_key=True)
    standard_type = Column(String, nullable=False)
    # contamination_classification / instrument_defect / baseline_variance / inspection_scoring
    version = Column(String, nullable=False, default="1.0")
    status = Column(String, nullable=False, default="draft")
    # draft / under_review / published / deprecated
    title = Column(String, nullable=False)
    description = Column(Text)
    criteria = Column(Text)  # JSON: grading criteria
    applicable_categories = Column(Text)  # JSON: instrument categories
    regulatory_alignment = Column(Text)  # JSON: {FDA, EUMDR, TGA, ...}
    human_review_required = Column(Boolean, default=True, nullable=False)
    published_by = Column(String)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 2: Baseline Governance
# ---------------------------------------------------------------------------


class BaselineGovernanceRecord(Base):
    """Governance record for a baseline approval, version change, or audit event."""

    __tablename__ = "p24_baseline_governance"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    governance_type = Column(String, nullable=False)
    # approval / version_change / provenance / audit
    instrument_category = Column(String)
    baseline_version_from = Column(String)
    baseline_version_to = Column(String)
    provenance_source = Column(String)
    # manufacturer_data / network_contributed / clinical_study / regulatory_guidance
    approval_status = Column(String, default="pending")
    # pending / approved / rejected / deprecated
    approver = Column(String)
    approval_notes = Column(Text)
    change_rationale = Column(Text)
    contributing_facilities = Column(Integer, default=0)
    k_anonymity_verified = Column(Boolean, default=False)
    human_review_required = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Phase 3: Benchmark Program
# ---------------------------------------------------------------------------


class BenchmarkReport(Base):
    """Published benchmark report (annual, contamination, reliability, or executive scorecard)."""

    __tablename__ = "p24_benchmark_reports"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    report_type = Column(String, nullable=False)
    # annual / contamination / reliability / executive_scorecard
    report_period = Column(String)  # e.g. "2025-H1", "2025-Annual"
    region = Column(String, default="global")
    facility_count = Column(Integer, default=0)  # k-anonymity >=10
    network_percentile = Column(Float)  # where this tenant sits
    contamination_rate = Column(Float)
    reliability_score = Column(Float)
    inspection_pass_rate = Column(Float)
    capa_closure_rate = Column(Float)
    benchmark_summary = Column(Text)
    executive_summary = Column(Text)
    human_review_required = Column(Boolean, default=True, nullable=False)
    disclaimer = Column(
        Text,
        default=(
            "Benchmark data derived from anonymized aggregate network contributions. "
            "Does not identify individual facilities, patients, or instruments. "
            "For planning and awareness purposes only. Human review required."
        ),
    )
    status = Column(String, default="draft")  # draft / under_review / published
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 4: International Expansion
# ---------------------------------------------------------------------------


class RegionalDeployment(Base):
    """Regional deployment configuration for international expansion."""

    __tablename__ = "p24_regional_deployments"

    id = Column(Integer, primary_key=True)
    region = Column(String, nullable=False, unique=True)
    # north_america / europe / apac / australia / latam / mena
    deployment_status = Column(String, default="planning")
    # planning / pilot / active / suspended
    data_residency_country = Column(String)
    privacy_framework = Column(String)  # GDPR / PIPEDA / PDPA / Privacy_Act / LGPD
    regulatory_frameworks = Column(Text)  # JSON: [FDA, EUMDR, TGA, ...]
    compliance_status = Column(String, default="assessing")
    # assessing / compliant / partial / non_compliant
    active_participants = Column(Integer, default=0)
    data_residency_verified = Column(Boolean, default=False)
    cross_border_transfer_approved = Column(Boolean, default=False)
    human_review_required = Column(Boolean, default=True, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 5: Intelligence APIs
# ---------------------------------------------------------------------------


class APIPartnerApplication(Base):
    """Partner API application and approval record."""

    __tablename__ = "p24_api_partners"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    partner_name = Column(String, nullable=False)
    api_tier = Column(String, nullable=False)
    # partner / manufacturer / research / governance
    requested_scopes = Column(Text)  # JSON: list of API scopes requested
    approved_scopes = Column(Text)   # JSON: approved subset
    application_status = Column(String, default="pending")
    # pending / approved / rejected / suspended / revoked
    rate_limit_per_hour = Column(Integer, default=100)
    data_anonymization_required = Column(Boolean, default=True)
    dpa_signed = Column(Boolean, default=False)
    human_review_required = Column(Boolean, default=True, nullable=False)
    approved_by = Column(String)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 6: Advisory Consortium
# ---------------------------------------------------------------------------


class AdvisoryConsortiumMember(Base):
    """Advisory consortium member (hospital / manufacturer / regulator / academic)."""

    __tablename__ = "p24_consortium_members"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True, unique=True)
    organization_type = Column(String, nullable=False)
    # hospital / manufacturer / regulator / academic / standards_body
    region = Column(String)
    membership_tier = Column(String, default="observer")
    # observer / contributor / voting / steering
    membership_status = Column(String, default="pending")
    # pending / active / suspended / resigned
    governance_roles = Column(Text)  # JSON: [standards_reviewer, publication_approver, ...]
    standards_review_active = Column(Boolean, default=False)
    voting_rights = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StandardsPublication(Base):
    """Published standards document from the Advisory Consortium."""

    __tablename__ = "p24_standards_publications"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    publication_type = Column(String, nullable=False)
    # standard / guidance / benchmark_report / position_paper / technical_note
    version = Column(String, default="1.0")
    status = Column(String, default="draft")
    # draft / consortium_review / public_comment / approved / published / superseded
    abstract = Column(Text)
    authors = Column(Text)  # JSON: list of contributing organizations (anonymized)
    regulatory_bodies_aligned = Column(Text)  # JSON: [FDA, EUMDR, TGA, ...]
    public_comment_period_days = Column(Integer, default=30)
    human_review_required = Column(Boolean, default=True, nullable=False)
    disclaimer = Column(
        Text,
        default=(
            "This publication represents consensus guidance from consortium members. "
            "It does not constitute regulatory approval or clearance. "
            "Implementation requires local clinical and regulatory review."
        ),
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
