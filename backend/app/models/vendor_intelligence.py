"""P6: Vendor Intelligence Exchange & Manufacturer Collaboration Network — data models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean

from app.db.base import Base


class VendorScorecard(Base):
    """Composite quality scorecard for a vendor within a tenant/period."""
    __tablename__ = "vendor_scorecards"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    vendor_id = Column(String(100), nullable=False, index=True)
    vendor_name = Column(String(255), nullable=False, default="")
    period_label = Column(String(20), nullable=False, default="")
    period_type = Column(String(20), nullable=False, default="monthly")

    # Baseline
    baseline_adoption_rate_pct = Column(Float, default=0.0, nullable=False)
    baseline_approval_rate_pct = Column(Float, default=0.0, nullable=False)

    # Defects
    defect_rate_pct = Column(Float, default=0.0, nullable=False)
    contamination_recurrence_rate_pct = Column(Float, default=0.0, nullable=False)

    # CAPA
    capa_avg_response_days = Column(Float, default=0.0, nullable=False)
    capa_closure_rate_pct = Column(Float, default=0.0, nullable=False)

    # Inspection
    inspection_failure_rate_pct = Column(Float, default=0.0, nullable=False)

    # Composite
    composite_score = Column(Float, default=0.0, nullable=False)   # 0-100
    risk_tier = Column(String(20), nullable=False, default="low")
    portfolio_rank = Column(Integer, default=0, nullable=False)

    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class VendorPerformanceMetric(Base):
    """Single named metric for a vendor in a period."""
    __tablename__ = "vendor_performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    vendor_id = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, default=0.0, nullable=False)
    period_label = Column(String(20), nullable=False, default="")
    period_type = Column(String(20), nullable=False, default="monthly")
    recorded_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class VendorDefectTrend(Base):
    """Defect counts and trend direction for a vendor over a period."""
    __tablename__ = "vendor_defect_trends"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    vendor_id = Column(String(100), nullable=False, index=True)
    period_label = Column(String(20), nullable=False, default="")

    total_defects = Column(Integer, default=0, nullable=False)
    critical_defects = Column(Integer, default=0, nullable=False)
    blood_findings = Column(Integer, default=0, nullable=False)
    defect_rate_pct = Column(Float, default=0.0, nullable=False)
    trend_direction = Column(String(20), nullable=False, default="stable")  # improving|stable|worsening

    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class VendorResponseMetric(Base):
    """CAPA and recall response time metrics for a vendor."""
    __tablename__ = "vendor_response_metrics"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    vendor_id = Column(String(100), nullable=False, index=True)

    avg_capa_response_days = Column(Float, default=0.0, nullable=False)
    avg_capa_closure_days = Column(Float, default=0.0, nullable=False)
    overdue_capas = Column(Integer, default=0, nullable=False)
    recall_response_days = Column(Float, nullable=True)
    last_computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class ManufacturerScorecard(Base):
    """Composite quality scorecard for a manufacturer within a tenant/period."""
    __tablename__ = "manufacturer_scorecards"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    manufacturer_id = Column(String(100), nullable=False, index=True)
    manufacturer_name = Column(String(255), nullable=False, default="")
    period_label = Column(String(20), nullable=False, default="")
    period_type = Column(String(20), nullable=False, default="monthly")

    # Baseline quality
    baseline_quality_score = Column(Float, default=0.0, nullable=False)
    baseline_adoption_rate_pct = Column(Float, default=0.0, nullable=False)

    # Inspection
    inspection_pass_rate_pct = Column(Float, default=0.0, nullable=False)
    contamination_recurrence_rate_pct = Column(Float, default=0.0, nullable=False)

    # Instruments / recalls
    instrument_defect_frequency = Column(Float, default=0.0, nullable=False)
    recall_count = Column(Integer, default=0, nullable=False)
    capa_effectiveness_score = Column(Float, default=0.0, nullable=False)

    # Composite
    composite_score = Column(Float, default=0.0, nullable=False)
    risk_tier = Column(String(20), nullable=False, default="low")
    portfolio_rank = Column(Integer, default=0, nullable=False)

    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class ManufacturerDefectTrend(Base):
    """Defect trend for a manufacturer over a period."""
    __tablename__ = "manufacturer_defect_trends"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    manufacturer_id = Column(String(100), nullable=False, index=True)
    period_label = Column(String(20), nullable=False, default="")

    total_defects = Column(Integer, default=0, nullable=False)
    critical_defects = Column(Integer, default=0, nullable=False)
    trend_direction = Column(String(20), nullable=False, default="stable")

    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class ManufacturerBaselineQuality(Base):
    """Baseline submission quality metrics for a manufacturer."""
    __tablename__ = "manufacturer_baseline_quality"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    manufacturer_id = Column(String(100), nullable=False, index=True)
    period_label = Column(String(20), nullable=False, default="")

    baselines_submitted = Column(Integer, default=0, nullable=False)
    baselines_approved = Column(Integer, default=0, nullable=False)
    baselines_rejected = Column(Integer, default=0, nullable=False)
    avg_review_days = Column(Float, default=0.0, nullable=False)
    quality_score = Column(Float, default=0.0, nullable=False)

    computed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class SharedDefectSignal(Base):
    """Anonymized aggregate defect signal — NO hospital or tenant identifiers."""
    __tablename__ = "shared_defect_signals"

    id = Column(Integer, primary_key=True, index=True)
    signal_type = Column(String(50), nullable=False, index=True)  # instrument_failure|contamination|baseline_deviation|damage
    instrument_category = Column(String(100), nullable=False, default="")
    finding_category = Column(String(100), nullable=False, default="")
    occurrence_count = Column(Integer, default=0, nullable=False)   # aggregate — NO hospital IDs
    severity = Column(String(20), nullable=False, default="medium")
    confidence_score = Column(Float, default=0.0, nullable=False)
    first_seen_period = Column(String(20), nullable=False, default="")
    last_seen_period = Column(String(20), nullable=False, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class CrossHospitalTrend(Base):
    """Anonymized cross-hospital aggregate trend — counts only, never IDs."""
    __tablename__ = "cross_hospital_trends"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    period_label = Column(String(20), nullable=False, index=True)
    hospital_count_contributing = Column(Integer, default=0, nullable=False)  # never IDs
    aggregate_value = Column(Float, default=0.0, nullable=False)
    trend_direction = Column(String(20), nullable=False, default="stable")
    significance_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class InstrumentRiskPattern(Base):
    """Global anonymized instrument risk pattern — no tenant or hospital IDs."""
    __tablename__ = "instrument_risk_patterns"

    id = Column(Integer, primary_key=True, index=True)
    instrument_category = Column(String(100), nullable=False, index=True)
    pattern_type = Column(String(50), nullable=False, index=True)  # contamination|damage|baseline_fail
    risk_score = Column(Float, default=0.0, nullable=False)
    occurrence_rate_pct = Column(Float, default=0.0, nullable=False)
    hospital_count_affected = Column(Integer, default=0, nullable=False)  # anonymized count
    description = Column(Text, default="", nullable=False)
    recommended_action = Column(Text, default="", nullable=False)
    detected_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True, nullable=False)


class RecallEvent(Base):
    """Recall event record (FDA, manufacturer, or internal)."""
    __tablename__ = "recall_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    vendor_id = Column(String(100), nullable=False, index=True, default="")
    manufacturer_id = Column(String(100), nullable=True, index=True)

    recall_number = Column(String(100), nullable=False, default="")
    recall_title = Column(String(255), nullable=False, default="")
    recall_description = Column(Text, default="", nullable=False)
    affected_instrument_categories = Column(Text, default="[]", nullable=False)  # JSON

    severity = Column(String(20), nullable=False, default="class_ii")  # class_i|class_ii|class_iii|advisory
    recall_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolution_date = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="active")  # active|resolved|monitoring

    source = Column(String(20), nullable=False, default="fda")  # fda|manufacturer|internal
    source_url = Column(Text, default="", nullable=False)

    # FDA MedWatch-ready fields (Enhancement 4)
    fda_product_code = Column(String(50), nullable=True)
    fda_classification = Column(String(20), nullable=True)  # "Class I", "Class II", "Class III"
    lot_numbers = Column(Text, nullable=True)  # JSON list
    distribution_pattern = Column(Text, nullable=True)  # geographic scope
    voluntary = Column(Boolean, nullable=True)  # voluntary vs FDA-mandated

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class RecallImpactAssessment(Base):
    """Impact assessment for a recall event within a tenant."""
    __tablename__ = "recall_impact_assessments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    recall_event_id = Column(Integer, nullable=False, index=True)

    affected_instruments_count = Column(Integer, default=0, nullable=False)
    affected_hospitals_count = Column(Integer, default=0, nullable=False)  # anonymized
    risk_level = Column(String(20), nullable=False, default="medium")
    assessment_notes = Column(Text, default="", nullable=False)
    assessed_by = Column(String(100), nullable=False, default="system")
    assessed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class VendorRecallResponse(Base):
    """Vendor's response to a recall event."""
    __tablename__ = "vendor_recall_responses"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True, default="default-tenant")
    recall_event_id = Column(Integer, nullable=False, index=True)
    vendor_id = Column(String(100), nullable=False, index=True)

    response_status = Column(String(30), nullable=False, default="acknowledged")  # acknowledged|investigating|resolved|no_action
    response_notes = Column(Text, default="", nullable=False)
    response_date = Column(DateTime, nullable=True)
    corrective_action_taken = Column(Text, default="", nullable=False)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class IntelligenceSharingConsent(Base):
    """Per-hospital opt-in consent for contributing to cross-hospital intelligence pool."""
    __tablename__ = "intelligence_sharing_consents"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, index=True)
    consented_by = Column(String(200), nullable=False)  # user/role who consented
    consent_version = Column(String(20), nullable=False, default="1.0")
    is_active = Column(Boolean, nullable=False, default=True)
    modules = Column(Text, nullable=False, default="[]")  # JSON list: ["defect_signals","risk_patterns"]
    consented_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(200), nullable=True)
    audit_log = Column(Text, nullable=False, default="[]")  # JSON list of audit events
