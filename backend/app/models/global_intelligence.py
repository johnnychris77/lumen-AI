"""P23: Global Surgical Intelligence Network — SQLAlchemy models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class GlobalIntelligenceSignal(Base):
    """Anonymized cross-network quality signal (published after k-anonymity + human review)."""

    __tablename__ = "global_intelligence_signals"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)  # originating tenant (kept for audit; never published)
    signal_type = Column(String, nullable=False)
    # instrument_quality/recall_early_warning/contamination_pattern/baseline_deviation/capa_pattern
    instrument_category = Column(String)
    finding_type = Column(String)
    region = Column(String)  # north_america/europe/apac/australia/global
    # Anonymized aggregates only (no facility identifiers)
    facility_count = Column(Integer, default=0)  # k-anonymity: must be >=10 before publishing
    signal_strength = Column(Float, default=0.0)
    trend_direction = Column(String, default="stable")
    # Governance
    k_anonymity_verified = Column(Boolean, default=False)
    human_review_completed = Column(Boolean, default=False)
    published = Column(Boolean, default=False)
    human_review_required = Column(Boolean, default=True, nullable=False)
    association_reason = Column(Text)
    disclaimer = Column(
        Text,
        default=(
            "Global signal represents anonymized aggregate patterns across participating facilities. "
            "Does not identify any individual facility, patient, or instrument. "
            "Does not establish causation."
        ),
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)


class InstrumentRiskRegistryEntry(Base):
    """Cross-network instrument risk pattern (anonymized, aggregated)."""

    __tablename__ = "instrument_risk_registry"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    instrument_category = Column(String, nullable=False)
    manufacturer_category = Column(String)  # generalized, not specific manufacturer name
    risk_pattern = Column(String)  # contamination/physical_defect/identification_failure/baseline_deviation
    risk_score = Column(Float, default=0.0)
    facilities_reporting = Column(Integer, default=0)  # must be >=5 before inclusion
    finding_count = Column(Integer, default=0)
    trend_direction = Column(String, default="stable")
    registry_status = Column(String, default="monitoring")  # monitoring/elevated/active_signal/resolved
    human_review_required = Column(Boolean, default=True, nullable=False)
    association_reason = Column(Text)
    disclaimer = Column(
        Text,
        default=(
            "Registry entry based on anonymized aggregate quality signal data. "
            "Does not identify specific instruments, facilities, or patients. "
            "Investigation recommended before operational decisions."
        ),
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GlobalRecallEarlyWarning(Base):
    """Early warning signal when N>=5 facilities report same pattern (pre-recall detection)."""

    __tablename__ = "global_recall_early_warnings"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    instrument_category = Column(String, nullable=False)
    finding_type = Column(String, nullable=False)
    region = Column(String, default="global")
    facilities_count = Column(Integer, default=0)  # >=5 threshold
    signal_strength_score = Column(Float, default=0.0)
    recency_days = Column(Integer, default=90)
    # Recall coordination
    manufacturer_notified = Column(Boolean, default=False)
    regulatory_notified = Column(Boolean, default=False)
    human_review_required = Column(Boolean, default=True, nullable=False)
    association_reason = Column(Text)
    disclaimer = Column(
        Text,
        default=(
            "Early warning signal based on anonymized aggregate reporting patterns. "
            "Does not constitute a regulatory recall notice. "
            "Human review and regulatory consultation required before any action."
        ),
    )
    status = Column(String, default="active")  # active/under_review/escalated/resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GSINParticipant(Base):
    """GSIN participant registry (hospitals, vendors, manufacturers)."""

    __tablename__ = "gsin_participants"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True, unique=True)
    participant_type = Column(String, nullable=False)  # hospital/vendor/manufacturer/regulator
    region = Column(String, nullable=False)
    contribution_categories = Column(Text)  # JSON list: inspection_metrics, quality_rates, etc.
    baa_signed = Column(Boolean, default=False)
    dpa_signed = Column(Boolean, default=False)
    security_attestation_date = Column(DateTime(timezone=True), nullable=True)
    enrollment_status = Column(String, default="pending")  # pending/active/suspended/withdrawn
    minimum_contribution_met = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class RegulatoryEvidencePackage(Base):
    """Aggregated regulatory evidence archive entry."""

    __tablename__ = "regulatory_evidence_packages"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    target_authority = Column(String, nullable=False)  # FDA/HealthCanada/EUMDR/TGA/PMDA/MFDS
    evidence_type = Column(String, nullable=False)  # quality_performance/recall_signals/safety_patterns/benchmarking
    data_period_start = Column(DateTime(timezone=True), nullable=True)
    data_period_end = Column(DateTime(timezone=True), nullable=True)
    facility_count = Column(Integer, default=0)  # k-anonymity >=10 required
    summary = Column(Text)
    evidence_hash = Column(String)  # SHA-256 of package content for integrity
    human_review_required = Column(Boolean, default=True, nullable=False)
    disclaimer = Column(
        Text,
        default=(
            "Regulatory evidence package contains anonymized aggregate data only. "
            "Does not contain facility-identifiable information. "
            "Does not constitute regulatory clearance or approval."
        ),
    )
    status = Column(String, default="draft")  # draft/under_review/published/archived
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
