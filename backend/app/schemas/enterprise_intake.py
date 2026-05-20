from pydantic import BaseModel, Field


class EnterpriseInspectionIntakeRequest(BaseModel):
    tenant_id: str = Field(default="bonsecours")
    tenant_name: str = Field(default="Bon Secours")
    facility_name: str
    department_name: str = Field(default="Sterile Processing")
    vendor_name: str
    instrument_name: str
    instrument_category: str = Field(default="lumened instrument")
    finding_category: str
    finding_description: str = Field(default="")
    severity: str = Field(default="high")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_action: str = Field(default="Quarantine + reclean + second inspection")
    evidence_file_name: str = Field(default="")
    evidence_file_url: str = Field(default="")


class EnterpriseInspectionIntakeResponse(BaseModel):
    status: str
    message: str
    tenant_id: str
    facility_id: int
    department_id: int
    vendor_id: int
    instrument_id: int
    evidence_id: int | None
    finding_id: int
    risk_score_id: int
    disposition_id: int
    workflow_status: str


class EnterpriseIntakeHistoryItem(BaseModel):
    finding_id: int
    vendor_id: int | None = None
    instrument_id: int | None = None
    risk_score_id: int | None = None
    disposition_id: int | None = None
    vendor_name: str = ""
    instrument_name: str = ""
    instrument_category: str = ""
    finding_category: str = ""
    finding_description: str = ""
    severity: str = ""
    confidence_score: float = 0.0
    risk_tier: str = ""
    overall_score: int = 0
    recommended_action: str = ""
    final_action: str = ""
    disposition_status: str = ""
    workflow_status: str = "created_pending_human_review"
    created_at: str = ""


class EnterpriseIntakeHistoryResponse(BaseModel):
    items: list[EnterpriseIntakeHistoryItem]


class EnterpriseGovernancePacketResponse(BaseModel):
    packet_type: str
    title: str
    summary: str
    finding_id: int
    vendor_name: str = ""
    instrument_name: str = ""
    instrument_category: str = ""
    finding_category: str = ""
    finding_description: str = ""
    severity: str = ""
    confidence_score: float = 0.0
    risk_tier: str = ""
    overall_score: int = 0
    recommended_action: str = ""
    final_action: str = ""
    workflow_status: str = "created_pending_human_review"
    evidence_to_action_chain: list[str]
    audit_readiness: dict[str, str | int | None]


class EnterpriseAuditTrailItem(BaseModel):
    id: int
    tenant_id: str
    actor_email: str
    actor_role: str
    action_type: str
    resource_type: str
    resource_id: str
    status: str
    request_method: str
    request_path: str
    details: str
    compliance_flag: bool
    created_at: str


class EnterpriseAuditTrailResponse(BaseModel):
    items: list[EnterpriseAuditTrailItem]


class EnterpriseHumanReviewRequest(BaseModel):
    reviewer_name: str = Field(default="Demo Reviewer")
    reviewer_role: str = Field(default="quality_reviewer")
    decision: str = Field(default="approve")
    review_notes: str = Field(default="")
    human_confirmed: bool = Field(default=True)


class EnterpriseHumanReviewResponse(BaseModel):
    status: str
    message: str
    finding_id: int
    decision: str
    reviewer_name: str
    reviewer_role: str
    human_confirmed: bool
    workflow_status: str
