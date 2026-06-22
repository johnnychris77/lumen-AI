"""P25: Global Surgical Quality Infrastructure & Industry Utility Platform — SQLAlchemy models."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


# ---------------------------------------------------------------------------
# Phase 1: Instrument Digital Identity
# ---------------------------------------------------------------------------


class InstrumentDigitalIdentity(Base):
    """Global digital identity record for a surgical instrument."""

    __tablename__ = "p25_instrument_identities"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    # Primary identifiers (at least one required)
    udi = Column(String, index=True)           # FDA UDI (GS1/HIBCC/ICCBBA)
    barcode = Column(String, index=True)       # 1D/2D barcode value
    qr_code = Column(String, index=True)       # QR code payload
    keydot_id = Column(String, index=True)     # KeyDot optical fingerprint ID
    internal_id = Column(String, index=True)   # Facility-assigned internal ID
    # Instrument classification
    instrument_category = Column(String, nullable=False)
    manufacturer_name = Column(String)
    model_name = Column(String)
    serial_number = Column(String)
    manufacture_date = Column(DateTime(timezone=True), nullable=True)
    # Lifecycle state
    lifecycle_status = Column(String, default="active")
    # active / in_maintenance / quarantined / retired / lost
    current_location = Column(String)          # tray / cabinet / sterilization / OR / repair
    total_cycle_count = Column(Integer, default=0)
    max_cycle_count = Column(Integer)          # manufacturer-specified limit
    # Identity governance
    identity_verified = Column(Boolean, default=False)
    verification_method = Column(String)       # udi / barcode / qr / keydot / manual
    human_review_required = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Phase 2: Surgical Readiness Index
# ---------------------------------------------------------------------------


class SurgicalReadinessScore(Base):
    """Computed surgical readiness score at facility, tray, or enterprise level."""

    __tablename__ = "p25_readiness_scores"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    scope = Column(String, nullable=False)  # facility / tray / enterprise
    reference_id = Column(String)           # tray_id, procedure_type, or "enterprise"
    # Readiness components (0.0–1.0)
    instrument_availability = Column(Float, default=0.0)
    contamination_status = Column(Float, default=0.0)
    inspection_compliance = Column(Float, default=0.0)
    capa_backlog_health = Column(Float, default=0.0)
    sterilization_cycle_compliance = Column(Float, default=0.0)
    # Composite score
    readiness_score = Column(Float, default=0.0)   # 0–100
    readiness_tier = Column(String, default="unknown")
    # green (>=90) / yellow (75–89) / amber (60–74) / red (<60)
    # Alerts
    blocking_issues = Column(Text)   # JSON: list of blocking items
    warnings = Column(Text)          # JSON: list of warning items
    human_review_required = Column(Boolean, default=True, nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 3: Instrument Passport
# ---------------------------------------------------------------------------


class InstrumentPassportEvent(Base):
    """Individual lifecycle event in an instrument's passport history."""

    __tablename__ = "p25_passport_events"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    instrument_id = Column(Integer, nullable=False, index=True)  # FK → InstrumentDigitalIdentity.id
    event_type = Column(String, nullable=False)
    # inspection / sterilization / maintenance / repair / transfer / quarantine / retirement
    event_detail = Column(String)      # pass/fail/finding_type/maintenance_type
    performed_by = Column(String)      # role or anonymized actor reference
    cycle_count_at_event = Column(Integer)
    finding_severity = Column(String)  # critical/major/moderate/minor (for inspection events)
    outcome = Column(String)           # pass / fail / repaired / retired / escalated
    notes = Column(Text)
    # Traceability
    related_capa_id = Column(String)
    related_inspection_id = Column(String)
    human_review_required = Column(Boolean, default=False, nullable=False)
    event_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 4: Global Quality Registry
# ---------------------------------------------------------------------------


class GlobalQualityRegistryEntry(Base):
    """Anonymized cross-network quality registry entry (contamination/defect/baseline/reliability)."""

    __tablename__ = "p25_quality_registry"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    registry_type = Column(String, nullable=False)
    # contamination / defect / baseline / reliability
    instrument_category = Column(String, nullable=False)
    region = Column(String, default="global")
    # Anonymized aggregates
    contributing_facilities = Column(Integer, default=0)   # k-anonymity floor
    event_count = Column(Integer, default=0)
    rate = Column(Float, default=0.0)                       # events per 1,000 cycles
    severity_distribution = Column(Text)                    # JSON: {critical: %, major: %, ...}
    trend_direction = Column(String, default="stable")      # increasing/stable/decreasing
    # Governance
    k_anonymity_verified = Column(Boolean, default=False)
    human_review_required = Column(Boolean, default=True, nullable=False)
    association_reason = Column(Text)
    disclaimer = Column(
        Text,
        default=(
            "Registry entry represents anonymized aggregate quality data across participating "
            "facilities. Does not identify individual facilities, patients, or instruments. "
            "Does not establish causation. Human review required before operational decisions."
        ),
    )
    period = Column(String)   # e.g. "2025-H1", "2025-Annual"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Phase 5: Industry Utility API Keys
# ---------------------------------------------------------------------------


class IndustryAPICredential(Base):
    """Industry utility API credential issued to hospital/manufacturer/researcher consumers."""

    __tablename__ = "p25_api_credentials"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    consumer_type = Column(String, nullable=False)  # hospital / manufacturer / researcher / governance
    api_key_hash = Column(String, nullable=False)   # SHA-256 hash of issued key
    scopes = Column(Text)                           # JSON: granted scope list
    rate_limit_per_hour = Column(Integer, default=500)
    anonymization_enforced = Column(Boolean, default=True)
    status = Column(String, default="active")       # active / suspended / revoked
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Phase 6: Predictive Infrastructure
# ---------------------------------------------------------------------------


class QualityForecast(Base):
    """Predictive quality forecast for contamination, failure, compliance, or workforce impact."""

    __tablename__ = "p25_quality_forecasts"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    forecast_type = Column(String, nullable=False)
    # contamination / failure / compliance / workforce_impact
    instrument_category = Column(String)
    forecast_horizon_days = Column(Integer, default=30)
    # Forecast outputs
    predicted_rate = Column(Float)           # predicted event rate per 1,000 cycles
    confidence_interval_low = Column(Float)
    confidence_interval_high = Column(Float)
    confidence_score = Column(Float, default=0.0)
    trend_signal = Column(String, default="stable")  # rising/stable/falling
    risk_level = Column(String, default="low")       # low/medium/high/critical
    recommended_actions = Column(Text)               # JSON: list of recommended actions
    # Governance
    human_review_required = Column(Boolean, default=True, nullable=False)
    model_version = Column(String, default="1.0")
    disclaimer = Column(
        Text,
        default=(
            "Forecast represents a statistical projection based on historical patterns. "
            "Does not establish causation. Confidence intervals reflect model uncertainty. "
            "Human review and clinical judgement required before any operational decisions. "
            "Association identified — causation not established."
        ),
    )
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    forecast_period_start = Column(DateTime(timezone=True), nullable=True)
    forecast_period_end = Column(DateTime(timezone=True), nullable=True)
