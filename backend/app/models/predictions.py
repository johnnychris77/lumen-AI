"""P7: Predictive instrument failure analytics models."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from app.db.base import Base


class InstrumentFailurePrediction(Base):
    __tablename__ = "instrument_failure_predictions"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, index=True, default="")
    instrument_name = Column(String(255), nullable=False, index=True)
    instrument_category = Column(String(100), nullable=False, default="")
    prediction_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    horizon_days = Column(Integer, nullable=False, default=30)  # 30, 90, 180
    failure_probability = Column(Float, nullable=False, default=0.0)  # 0.0-1.0
    risk_score = Column(Float, nullable=False, default=0.0)           # 0-100
    risk_category = Column(String(20), nullable=False, default="low") # low/medium/high/critical
    confidence = Column(Float, nullable=False, default=0.0)           # 0.0-1.0
    records_used = Column(Integer, nullable=False, default=0)
    evidence_json = Column(Text, nullable=False, default="[]")
    recommended_action = Column(String(500), nullable=False, default="")
    data_source = Column(String(20), nullable=False, default="real")  # real/mock/insufficient


class ContaminationRecurrencePrediction(Base):
    __tablename__ = "contamination_recurrence_predictions"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, index=True, default="")
    instrument_name = Column(String(255), nullable=False, index=True)
    instrument_category = Column(String(100), nullable=False, default="")
    prediction_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    recurrence_probability = Column(Float, nullable=False, default=0.0)
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_category = Column(String(20), nullable=False, default="low")
    confidence = Column(Float, nullable=False, default=0.0)
    dominant_contaminant = Column(String(50), nullable=False, default="")  # blood/bone/tissue
    records_used = Column(Integer, nullable=False, default=0)
    evidence_json = Column(Text, nullable=False, default="[]")
    recommended_action = Column(String(500), nullable=False, default="")
    data_source = Column(String(20), nullable=False, default="real")


class RepairForecast(Base):
    __tablename__ = "repair_forecasts"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, index=True, default="")
    instrument_name = Column(String(255), nullable=False, index=True)
    instrument_category = Column(String(100), nullable=False, default="")
    prediction_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    repair_probability_90d = Column(Float, nullable=False, default=0.0)
    replacement_probability_180d = Column(Float, nullable=False, default=0.0)
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_category = Column(String(20), nullable=False, default="low")
    confidence = Column(Float, nullable=False, default=0.0)
    estimated_repair_cost_usd = Column(Float, nullable=False, default=0.0)
    estimated_replacement_cost_usd = Column(Float, nullable=False, default=0.0)
    recommended_action = Column(String(500), nullable=False, default="")
    records_used = Column(Integer, nullable=False, default=0)
    evidence_json = Column(Text, nullable=False, default="[]")
    data_source = Column(String(20), nullable=False, default="real")


class RecallRiskAssessment(Base):
    __tablename__ = "recall_risk_assessments"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    instrument_category = Column(String(100), nullable=False, index=True)
    assessment_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    exposure_score = Column(Float, nullable=False, default=0.0)      # 0-100
    active_recall_count = Column(Integer, nullable=False, default=0)
    critical_recall_count = Column(Integer, nullable=False, default=0)
    instruments_affected_estimate = Column(Integer, nullable=False, default=0)
    urgency_tier = Column(String(20), nullable=False, default="low") # low/watch/act/critical
    evidence_json = Column(Text, nullable=False, default="[]")
    recommended_action = Column(String(500), nullable=False, default="")
    data_source = Column(String(20), nullable=False, default="real")


class TrayRiskAssessment(Base):
    __tablename__ = "tray_risk_assessments"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    facility_id = Column(String(100), nullable=False, index=True, default="")
    tray_id = Column(String(100), nullable=False, index=True)  # logical group identifier
    assessment_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    tray_risk_score = Column(Float, nullable=False, default=0.0)      # 0-100
    risk_category = Column(String(20), nullable=False, default="low")
    instrument_count = Column(Integer, nullable=False, default=0)
    high_risk_instrument_count = Column(Integer, nullable=False, default=0)
    highest_risk_instrument = Column(String(255), nullable=False, default="")
    worst_failure_probability = Column(Float, nullable=False, default=0.0)
    recommended_action = Column(String(500), nullable=False, default="")
    evidence_json = Column(Text, nullable=False, default="[]")
    data_source = Column(String(20), nullable=False, default="real")
