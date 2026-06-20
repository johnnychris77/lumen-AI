from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from sqlalchemy import Column


class EnterpriseFacility(Base):
    __tablename__ = "enterprise_facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    facility_type: Mapped[str] = mapped_column(String(100), default="hospital", nullable=False)
    region: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseDepartment(Base):
    __tablename__ = "enterprise_departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    facility_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    department_type: Mapped[str] = mapped_column(String(100), default="spd", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseVendor(Base):
    __tablename__ = "enterprise_vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    vendor_type: Mapped[str] = mapped_column(String(100), default="medical_device", nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    risk_tier: Mapped[str] = mapped_column(String(50), default="unassigned", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseInstrument(Base):
    __tablename__ = "enterprise_instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    vendor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    instrument_type: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="unknown", nullable=False)
    model_number: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    risk_class: Mapped[str] = mapped_column(String(50), default="unassigned", nullable=False)
    ifu_reference: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseEvidence(Base):
    __tablename__ = "enterprise_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    evidence_type: Mapped[str] = mapped_column(String(100), default="inspection_photo", nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseFinding(Base):
    __tablename__ = "enterprise_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    instrument_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    vendor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    finding_category: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    finding_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="unassigned", nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    human_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseRiskScore(Base):
    __tablename__ = "enterprise_risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    finding_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    patient_safety_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    regulatory_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    operational_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vendor_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String(50), default="low", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseDisposition(Base):
    __tablename__ = "enterprise_dispositions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    finding_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    recommended_action: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    final_action: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="recommended", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseCapa(Base):
    __tablename__ = "enterprise_capas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    finding_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    vendor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    capa_number: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseGovernancePacket(Base):
    __tablename__ = "enterprise_governance_packets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    packet_type: Mapped[str] = mapped_column(String(100), default="executive_summary", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    generated_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class EnterpriseInstrumentBaseline(Base):
    __tablename__ = "enterprise_instrument_baselines"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, index=True, default="default")
    vendor_id = Column(Integer, nullable=True)
    instrument_id = Column(Integer, nullable=False, index=True)

    manufacturer_name = Column(String, default="")
    model_number = Column(String, default="")
    catalog_number = Column(String, default="")
    baseline_type = Column(String, default="manufacturer_reference")

    file_name = Column(String, default="")
    storage_uri = Column(String, default="")
    content_type = Column(String, default="")

    known_normal_characteristics = Column(Text, default="")
    known_abnormal_characteristics = Column(Text, default="")
    baseline_notes = Column(Text, default="")

    baseline_status = Column(String, default="pending_review")
    approved_by = Column(String, default="")
    approved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EnterpriseExportReadinessHistory(Base):
    __tablename__ = "enterprise_export_readiness_history"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, index=True, nullable=False)
    tenant_id = Column(String, default="", index=True)

    generated_at = Column(DateTime, nullable=True)

    governance_zip_ready = Column(Boolean, default=False)
    vendor_pdf_ready = Column(Boolean, default=False)
    infection_prevention_pdf_ready = Column(Boolean, default=False)
    executive_pdf_ready = Column(Boolean, default=True)

    baseline_evidence_count = Column(Integer, default=0)
    approved_baseline_count = Column(Integer, default=0)
    evidence_attachment_count = Column(Integer, default=0)

    readiness_summary = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EnterpriseVendorBaselineSubscription(Base):
    __tablename__ = "enterprise_vendor_baseline_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    vendor_name = Column(String, nullable=True)
    instrument_name = Column(String, nullable=True)
    instrument_category = Column(String, nullable=True)

    catalog_number = Column(String, nullable=True)
    model_number = Column(String, nullable=True)
    barcode_value = Column(String, nullable=True)
    qr_code_value = Column(String, nullable=True)
    key_dot_value = Column(String, nullable=True)

    tray_name = Column(String, nullable=True)
    baseline_image_url = Column(Text, nullable=True)

    acceptable_condition_notes = Column(Text, nullable=True)
    unacceptable_condition_examples = Column(Text, nullable=True)
    ifu_reference = Column(Text, nullable=True)

    subscription_tier = Column(String, nullable=True, default="vendor_standard")
    baseline_source = Column(String, nullable=True, default="vendor")
    baseline_status = Column(String, nullable=True, default="vendor_submitted")
    approval_status = Column(String, nullable=True, default="pending_hospital_review")
    baseline_version = Column(String, nullable=True, default="v1.0")

    approved_by = Column(String, nullable=True)
    approval_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EnterpriseScoringProfile(Base):
    """Tenant-configurable scoring weights for the Ranking Engine."""
    __tablename__ = "enterprise_scoring_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    profile_name = Column(String, default="Default", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # JSON blobs storing override dicts (null = use engine defaults)
    category_weights_json = Column(Text, nullable=True)
    severity_multipliers_json = Column(Text, nullable=True)

    # Compound risk escalation — floor score to Critical when N+ critical findings on same instrument in window_days
    compound_escalation_threshold = Column(Integer, default=2, nullable=False)
    compound_escalation_window_days = Column(Integer, default=90, nullable=False)

    created_by = Column(String, default="", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
