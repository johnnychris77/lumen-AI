"""P16: Patient Safety Intelligence models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.db.base import Base


class InstrumentQualitySignal(Base):
    __tablename__ = "instrument_quality_signals"

    id = Column(Integer, primary_key=True)
    signal_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    instrument_id = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    event_source = Column(
        String, nullable=False
    )  # "inspection", "baseline", "vendor", "recall", "rwe"
    event_type = Column(
        String, nullable=False
    )  # "contamination", "baseline_deviation", "repeat_failure", etc.
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Float, default=0.5)
    association_reason = Column(Text, nullable=True)
    recommended_review_action = Column(Text, nullable=True)
    human_review_status = Column(
        String, default="pending"
    )  # pending/under_review/reviewed/closed
    human_review_required = Column(Boolean, default=True)
    risk_tier = Column(String, default="low")  # low/medium/high/critical
    created_at = Column(DateTime, default=datetime.utcnow)


class PatientSafetyEventLink(Base):
    __tablename__ = "patient_safety_event_links"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    signal_id = Column(String, ForeignKey("instrument_quality_signals.signal_id"))
    external_event_id = Column(String, nullable=True)
    event_source_system = Column(String, nullable=True)  # "safecare", "rldatix", etc.
    event_type = Column(String, nullable=False)
    event_date = Column(DateTime, nullable=False)
    instrument_id = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    association_type = Column(
        String, default="potential"
    )  # potential/probable/confirmed_by_human
    association_reason = Column(Text, nullable=True)
    confidence_score = Column(Float, default=0.5)
    human_review_required = Column(Boolean, default=True)
    human_review_status = Column(String, default="pending")
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PotentialHarmSignal(Base):
    __tablename__ = "potential_harm_signals"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    signal_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    instrument_id = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    event_source = Column(String, nullable=False)
    event_type = Column(
        String, nullable=False
    )  # "potential_contamination_release", "undetected_defect_pattern", etc.
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Float, default=0.5)
    association_reason = Column(Text)
    recommended_review_action = Column(Text)
    human_review_status = Column(String, default="pending")
    human_review_required = Column(Boolean, default=True)
    risk_tier = Column(String, default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)


class NearMissCorrelation(Base):
    __tablename__ = "near_miss_correlations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    correlation_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    instrument_id = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    event_source = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Float, default=0.5)
    association_reason = Column(Text)
    recommended_review_action = Column(Text)
    human_review_status = Column(String, default="pending")
    human_review_required = Column(Boolean, default=True)
    near_miss_category = Column(
        String, nullable=True
    )  # "contamination_near_miss", "wrong_instrument", etc.
    created_at = Column(DateTime, default=datetime.utcnow)


class QualityInvestigation(Base):
    __tablename__ = "quality_investigations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    investigation_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    instrument_id = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    event_source = Column(String, default="internal")
    event_type = Column(String, nullable=False)
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Float, default=0.5)
    association_reason = Column(Text)
    recommended_review_action = Column(Text)
    human_review_status = Column(String, default="open")  # open/in_progress/closed
    human_review_required = Column(Boolean, default=True)
    investigation_status = Column(String, default="open")
    capa_id = Column(String, nullable=True)
    root_cause_category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class InfectionPreventionSignal(Base):
    __tablename__ = "infection_prevention_signals"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    signal_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    instrument_id = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    event_source = Column(
        String, nullable=False
    )  # "vigilanz", "icnet", "theradoc", "internal"
    event_type = Column(
        String, nullable=False
    )  # "hai_review_candidate", "ssi_review_candidate", "outbreak_signal"
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Float, default=0.5)
    association_reason = Column(Text)
    recommended_review_action = Column(Text)
    human_review_status = Column(String, default="pending")
    human_review_required = Column(Boolean, default=True)
    pathogen = Column(String, nullable=True)
    procedure_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CAPAEffectivenessSignal(Base):
    __tablename__ = "capa_effectiveness_signals"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    capa_id = Column(String, nullable=False)
    instrument_id = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    event_source = Column(String, default="internal")
    event_type = Column(
        String, nullable=False
    )  # "recurrence_detected", "effectiveness_confirmed"
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Float, default=0.5)
    association_reason = Column(Text)
    recommended_review_action = Column(Text)
    human_review_status = Column(String, default="pending")
    human_review_required = Column(Boolean, default=True)
    capa_status = Column(String, default="open")  # open/effective/ineffective/closed
    recurrence_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutiveRiskSignal(Base):
    __tablename__ = "executive_risk_signals"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    risk_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    instrument_id = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    event_source = Column(String, nullable=False)
    event_type = Column(
        String, nullable=False
    )  # "high_risk_vendor", "recall_exposure", "repeat_failure_pattern"
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    confidence_score = Column(Float, default=0.5)
    association_reason = Column(Text)
    recommended_review_action = Column(Text)
    human_review_status = Column(String, default="pending")
    human_review_required = Column(Boolean, default=True)
    risk_tier = Column(String, default="medium")  # low/medium/high/critical
    estimated_financial_exposure = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
