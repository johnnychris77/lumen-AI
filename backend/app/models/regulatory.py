"""P8: Regulatory & Accreditation models."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from app.db.base import Base


class RegulatoryStandard(Base):
    """Catalogue of regulatory standards (Joint Commission, AAMI, FDA, CMS, ISO)."""
    __tablename__ = "regulatory_standards"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True, index=True)  # e.g. "JC-IC.02.02.01"
    body = Column(String(50), nullable=False, index=True)  # "joint_commission"|"aami"|"fda"|"cms"|"iso"
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String(100), nullable=False, default="")  # e.g. "infection_control"
    applicability = Column(String(200), nullable=False, default="")  # e.g. "SPD,OR,ICU"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class FindingRegulatoryMapping(Base):
    """Maps CV finding categories to specific regulatory clauses."""
    __tablename__ = "finding_regulatory_mappings"
    id = Column(Integer, primary_key=True)
    finding_category = Column(String(100), nullable=False, index=True)  # "blood"|"bone"|"crack"|etc
    standard_code = Column(String(50), nullable=False, index=True)
    severity_threshold = Column(String(20), nullable=False, default="any")  # "any"|"high"|"critical"
    citation_text = Column(Text, nullable=False, default="")
    remediation_guidance = Column(Text, nullable=False, default="")
    auto_capa_required = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class AccreditationReadinessScore(Base):
    """Snapshot of a tenant's real-time accreditation readiness."""
    __tablename__ = "accreditation_readiness_scores"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, default="", index=True)
    assessment_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    overall_score = Column(Float, nullable=False, default=0.0)        # 0-100
    joint_commission_score = Column(Float, nullable=False, default=0.0)
    aami_score = Column(Float, nullable=False, default=0.0)
    fda_score = Column(Float, nullable=False, default=0.0)
    cms_score = Column(Float, nullable=False, default=0.0)
    deficiency_count = Column(Integer, nullable=False, default=0)
    critical_deficiency_count = Column(Integer, nullable=False, default=0)
    open_capa_count = Column(Integer, nullable=False, default=0)
    findings_json = Column(Text, nullable=False, default="[]")   # list of AccreditationFinding dicts
    data_source = Column(String(20), nullable=False, default="real")


class RegulatoryAuditPackage(Base):
    """Generated audit-ready export packages."""
    __tablename__ = "regulatory_audit_packages"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, default="")
    package_type = Column(String(50), nullable=False, default="joint_commission")  # "joint_commission"|"aami"|"fda"|"cms"|"full"
    period_label = Column(String(20), nullable=False, default="")
    status = Column(String(20), nullable=False, default="draft")  # draft|ready|submitted
    generated_by = Column(String(200), nullable=False, default="system")
    findings_count = Column(Integer, nullable=False, default=0)
    standards_covered = Column(Text, nullable=False, default="[]")  # JSON list of standard codes
    package_json = Column(Text, nullable=False, default="{}")       # full package content
    pdf_key = Column(String(500), nullable=True)                    # S3 key if exported
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime, nullable=True)


class FDASubmissionTracker(Base):
    """Track FDA 510(k) and MDR submission status."""
    __tablename__ = "fda_submission_trackers"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    submission_type = Column(String(50), nullable=False, default="510k")  # "510k"|"mdr"|"pma"
    submission_number = Column(String(100), nullable=True)
    device_name = Column(String(255), nullable=False, default="")
    manufacturer = Column(String(255), nullable=False, default="")
    status = Column(String(50), nullable=False, default="pending")  # pending|cleared|denied|withdrawn
    submission_date = Column(DateTime, nullable=True)
    decision_date = Column(DateTime, nullable=True)
    predicate_device = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
