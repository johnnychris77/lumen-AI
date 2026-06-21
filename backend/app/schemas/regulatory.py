"""P8: Pydantic schemas for regulatory & accreditation."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class AccreditationFinding(BaseModel):
    standard_code: str
    finding_category: str
    occurrence_count: int = 0
    rate_pct: float = 0.0
    severity: str = "medium"        # low/medium/high/critical
    citation_text: str = ""
    remediation_guidance: str = ""
    auto_capa_required: bool = False


class AccreditationReadinessResult(BaseModel):
    tenant_id: str
    facility_id: str = ""
    assessment_date: str
    overall_score: float = 0.0
    joint_commission_score: float = 0.0
    aami_score: float = 0.0
    fda_score: float = 0.0
    cms_score: float = 0.0
    iso_score: float = 0.0
    deficiency_count: int = 0
    critical_deficiency_count: int = 0
    open_capa_count: int = 0
    readiness_tier: str = "needs_improvement"  # survey_ready/conditional/needs_improvement/at_risk
    findings: list[AccreditationFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    data_source: str = "real"


class AuditPackageResult(BaseModel):
    id: int | None = None
    tenant_id: str
    facility_id: str = ""
    package_type: str
    period_label: str
    status: str = "ready"
    generated_by: str = "system"
    generated_at: str
    accreditation_score: float = 0.0
    readiness_tier: str = ""
    standards_covered: list[str] = Field(default_factory=list)
    findings_count: int = 0
    findings: list[AccreditationFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    data_source: str = "real"


class AuditPackageRequest(BaseModel):
    tenant_id: str
    facility_id: str = ""
    package_type: str = "joint_commission"  # joint_commission|aami|fda|cms|full
    period_label: str = ""
    generated_by: str = "system"


class FDASubmissionResult(BaseModel):
    id: int | None = None
    tenant_id: str
    submission_type: str = "510k"
    submission_number: str | None = None
    device_name: str = ""
    manufacturer: str = ""
    status: str = "pending"
    submission_date: str | None = None
    decision_date: str | None = None
    notes: str = ""


class FDASubmissionCreate(BaseModel):
    tenant_id: str
    submission_type: str = "510k"
    submission_number: str | None = None
    device_name: str
    manufacturer: str
    status: str = "pending"
    submission_date: str | None = None
    notes: str = ""


class RegulatoryDashboard(BaseModel):
    tenant_id: str
    facility_id: str = ""
    generated_at: str
    data_source: str = "real"
    overall_readiness_score: float = 0.0
    readiness_tier: str = ""
    joint_commission_score: float = 0.0
    aami_score: float = 0.0
    fda_score: float = 0.0
    cms_score: float = 0.0
    iso_score: float = 0.0
    total_deficiencies: int = 0
    critical_deficiencies: int = 0
    open_capas: int = 0
    auto_capa_required_count: int = 0
    fda_submissions: list[FDASubmissionResult] = Field(default_factory=list)
    standards_summary: list[dict[str, Any]] = Field(default_factory=list)
    top_findings: list[AccreditationFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
