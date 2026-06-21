"""P15: National SPD Intelligence Network — recall signal models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String

from app.db.base import Base


class RecallSignal(Base):
    __tablename__ = "recall_signals"

    id = Column(Integer, primary_key=True)
    signal_id = Column(String, unique=True)  # uuid
    signal_type = Column(String)  # "recurring_defect"/"recurring_contamination"/"recurring_failure"
    manufacturer_pseudonym = Column(String, nullable=True)  # anonymized
    instrument_category = Column(String, nullable=False)
    finding_type = Column(String, nullable=False)
    n_facilities_reporting = Column(Integer, nullable=False)  # must be >= 3 to surface
    first_observed = Column(DateTime)
    last_observed = Column(DateTime)
    signal_strength = Column(Float)  # 0.0–1.0
    status = Column(String, default="active")  # active/escalated/resolved/suppressed
    escalated_to_fda = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class FacilityRecallSignalContribution(Base):
    __tablename__ = "facility_recall_contributions"

    id = Column(Integer, primary_key=True)
    signal_id = Column(String, ForeignKey("recall_signals.signal_id"))
    facility_pseudonym = Column(String, nullable=False)  # anonymized, never raw tenant_id
    contributed_at = Column(DateTime, default=datetime.utcnow)
    finding_count = Column(Integer, default=1)
