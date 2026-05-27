from pydantic import BaseModel, Field, ConfigDict


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
    human_review_status: str = ""
    human_confirmed: bool = False
    created_at: str = ""


class EnterpriseIntakeHistoryResponse(BaseModel):
    items: list[EnterpriseIntakeHistoryItem]


class EnterpriseGovernanceEvidenceItem(BaseModel):
    evidence_id: int
    evidence_type: str
    file_name: str
    storage_uri: str
    content_type: str = ""
    notes: str = ""
    created_at: str = ""


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
    human_review_status: str = ""
    human_confirmed: bool = False
    evidence_to_action_chain: list[str]
    audit_readiness: dict[str, str | int | None]
    evidence_attachments: list[EnterpriseGovernanceEvidenceItem] = Field(default_factory=list)
    baseline_evidence: list[dict] = []

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


class EnterpriseCapaCreateRequest(BaseModel):
    title: str = Field(default="CAPA for enterprise quality finding")
    description: str = Field(default="")
    owner_id: int | None = Field(default=None)
    due_date: str = Field(default="")
    status: str = Field(default="open")


class EnterpriseCapaCreateResponse(BaseModel):
    status: str
    message: str
    finding_id: int
    capa_id: int
    capa_number: str
    capa_status: str
    workflow_status: str


class EnterpriseCapaListItem(BaseModel):
    capa_id: int
    finding_id: int | None = None
    vendor_id: int | None = None
    capa_number: str
    title: str
    description: str
    status: str
    due_date: str = ""
    closed_at: str = ""
    created_at: str = ""


class EnterpriseCapaListResponse(BaseModel):
    items: list[EnterpriseCapaListItem]


class EnterpriseCapaCreateRequest(BaseModel):
    title: str = Field(default="CAPA for enterprise quality finding")
    description: str = Field(default="")
    owner_id: int | None = Field(default=None)
    due_date: str = Field(default="")
    status: str = Field(default="open")


class EnterpriseCapaCreateResponse(BaseModel):
    status: str
    message: str
    finding_id: int
    capa_id: int
    capa_number: str
    capa_status: str
    workflow_status: str


class EnterpriseCapaListItem(BaseModel):
    capa_id: int
    finding_id: int | None = None
    vendor_id: int | None = None
    capa_number: str
    title: str
    description: str
    status: str
    due_date: str = ""
    closed_at: str = ""
    created_at: str = ""


class EnterpriseCapaListResponse(BaseModel):
    items: list[EnterpriseCapaListItem]


class EnterpriseCapaStatusUpdateRequest(BaseModel):
    status: str = Field(default="in_progress")
    note: str = Field(default="")


class EnterpriseCapaStatusUpdateResponse(BaseModel):
    status: str
    message: str
    capa_id: int
    capa_number: str
    capa_status: str
    workflow_status: str
    closed_at: str = ""


class EnterpriseCapaSummaryResponse(BaseModel):
    total_capas: int
    open_capas: int
    in_progress_capas: int
    pending_review_capas: int
    closed_capas: int
    overdue_capas: int
    cancelled_capas: int
    average_days_open: float
    closure_rate: float
    risk_message: str


class EnterpriseCapaSummaryResponse(BaseModel):
    total_capas: int
    open_capas: int
    in_progress_capas: int
    pending_review_capas: int
    closed_capas: int
    overdue_capas: int
    cancelled_capas: int
    average_days_open: float
    closure_rate: float
    risk_message: str


class EnterpriseEvidenceUploadResponse(BaseModel):
    status: str
    message: str
    finding_id: int
    evidence_id: int
    evidence_type: str
    file_name: str
    storage_uri: str
    workflow_status: str


class EnterpriseEvidenceListItem(BaseModel):
    evidence_id: int
    finding_id: int | None = None
    evidence_type: str
    file_name: str
    storage_uri: str
    content_type: str = ""
    notes: str = ""
    created_at: str = ""


class EnterpriseEvidenceListResponse(BaseModel):
    items: list[EnterpriseEvidenceListItem]



class EnterpriseInstrumentBaselineCreateResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    status: str
    message: str
    baseline_id: int
    instrument_id: int
    vendor_id: int | None = None
    manufacturer_name: str
    model_number: str = ""
    catalog_number: str = ""
    baseline_type: str
    file_name: str
    storage_uri: str
    baseline_status: str
    workflow_status: str


class EnterpriseInstrumentBaselineItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    baseline_id: int
    instrument_id: int
    vendor_id: int | None = None
    manufacturer_name: str
    model_number: str = ""
    catalog_number: str = ""
    baseline_type: str
    file_name: str
    storage_uri: str
    known_normal_characteristics: str = ""
    known_abnormal_characteristics: str = ""
    baseline_notes: str = ""
    baseline_status: str = ""
    approved_by: str = ""
    approved_at: str = ""
    created_at: str = ""


class EnterpriseInstrumentBaselineListResponse(BaseModel):
    items: list[EnterpriseInstrumentBaselineItem]


class EnterpriseBaselineComparisonResponse(BaseModel):
    status: str
    message: str
    finding_id: int
    instrument_id: int | None = None
    vendor_id: int | None = None
    baseline_id: int | None = None
    evidence_id: int | None = None
    comparison_score: int
    deviation_level: str
    baseline_alignment: str
    vendor_management_signal: str
    recommended_action: str
    workflow_status: str


class EnterpriseBaselineApprovalRequest(BaseModel):
    reviewer_name: str = "Baseline Reviewer"
    reviewer_role: str = "quality_reviewer"
    decision: str
    review_notes: str = ""


class EnterpriseBaselineApprovalResponse(BaseModel):
    status: str
    message: str
    baseline_id: int
    instrument_id: int
    vendor_id: int | None = None
    baseline_status: str
    approved_by: str = ""
    approved_at: str = ""
    workflow_status: str


class EnterpriseGovernanceBaselineEvidence(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    baseline_id: int
    instrument_id: int
    vendor_id: int | None = None
    manufacturer_name: str = ""
    model_number: str = ""
    catalog_number: str = ""
    baseline_type: str = ""
    file_name: str = ""
    storage_uri: str = ""
    baseline_status: str = ""
    approved_by: str = ""
    approved_at: str = ""
    known_normal_characteristics: str = ""
    known_abnormal_characteristics: str = ""
    baseline_notes: str = ""
    audit_significance: str = ""


class EnterpriseGovernanceExportPackageResponse(BaseModel):
    status: str = "success"
    finding_id: int
    package_type: str = "enterprise_governance_export_package"
    readiness_status: str = ""
    json_packet_url: str = ""
    pdf_packet_url: str = ""
    baseline_evidence_count: int = 0
    approved_baseline_count: int = 0
    evidence_attachment_count: int = 0
    comparison_score_count: int = 0
    capa_count: int = 0
    audit_event_count: int = 0
    included_sections: list[str] = []
    recommended_use: list[str] = []
    message: str = ""


class EnterpriseVendorEscalationPacketResponse(BaseModel):
    status: str = "success"
    finding_id: int
    packet_type: str = "vendor_escalation_packet"
    escalation_status: str = ""
    vendor_id: int | None = None
    vendor_name: str = ""
    instrument_id: int | None = None
    instrument_name: str = ""
    instrument_category: str = ""
    finding_category: str = ""
    finding_description: str = ""
    severity: str = ""
    confidence_score: float | None = None
    baseline_evidence_count: int = 0
    approved_baseline_count: int = 0
    comparison_score: int | None = None
    deviation_level: str = ""
    baseline_alignment: str = ""
    vendor_management_signal: str = ""
    recommended_vendor_action: str = ""
    requested_vendor_response: str = ""
    supporting_evidence: list[dict] = []
    baseline_evidence: list[dict] = []
    escalation_summary: str = ""
    message: str = ""


class EnterpriseInfectionPreventionReviewPacketResponse(BaseModel):
    status: str = "success"
    finding_id: int
    packet_type: str = "infection_prevention_review_packet"
    ip_review_status: str = ""
    patient_safety_signal: str = ""
    infection_risk_signal: str = ""
    vendor_id: int | None = None
    vendor_name: str = ""
    instrument_id: int | None = None
    instrument_name: str = ""
    instrument_category: str = ""
    finding_category: str = ""
    finding_description: str = ""
    severity: str = ""
    confidence_score: float | None = None
    baseline_evidence_count: int = 0
    approved_baseline_count: int = 0
    comparison_score: int | None = None
    deviation_level: str = ""
    baseline_alignment: str = ""
    recommended_ip_action: str = ""
    recommended_documentation: list[str] = []
    supporting_evidence: list[dict] = []
    baseline_evidence: list[dict] = []
    ip_review_summary: str = ""
    message: str = ""


class EnterpriseExecutiveQualityReviewDashboardResponse(BaseModel):
    status: str = "success"
    dashboard_type: str = "executive_quality_review_dashboard"
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    baseline_evidence_count: int = 0
    approved_baseline_count: int = 0
    vendor_escalation_ready_count: int = 0
    ip_review_recommended_count: int = 0
    open_capa_count: int = 0
    closed_capa_count: int = 0
    audit_event_count: int = 0
    governance_export_count: int = 0
    quality_signal: str = ""
    executive_summary: str = ""
    recommended_leadership_actions: list[str] = []
    top_vendor_signals: list[dict] = []
    recent_findings: list[dict] = []


class EnterpriseExportReadinessStatusResponse(BaseModel):
    status: str = "success"
    finding_id: int
    generated_at: str = ""
    governance_zip_ready: bool = False
    vendor_pdf_ready: bool = False
    infection_prevention_pdf_ready: bool = False
    executive_pdf_ready: bool = True
    baseline_evidence_count: int = 0
    approved_baseline_count: int = 0
    evidence_attachment_count: int = 0
    governance_zip_url: str = ""
    vendor_pdf_url: str = ""
    infection_prevention_pdf_url: str = ""
    executive_pdf_url: str = ""
    readiness_summary: str = ""
    cards: list[dict] = []


class EnterpriseExportReadinessHistoryItem(BaseModel):
    finding_id: int
    generated_at: str = ""
    governance_zip_ready: bool = False
    vendor_pdf_ready: bool = False
    infection_prevention_pdf_ready: bool = False
    executive_pdf_ready: bool = False
    baseline_evidence_count: int = 0
    approved_baseline_count: int = 0
    evidence_attachment_count: int = 0
    readiness_summary: str = ""


class EnterpriseExportReadinessHistoryResponse(BaseModel):
    status: str = "success"
    history_type: str = "export_readiness_history"
    items: list[EnterpriseExportReadinessHistoryItem] = []
