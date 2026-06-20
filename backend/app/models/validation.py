"""P12 Clinical Validation — ORM models for FP/FN analysis."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.db import Base


def _now():
    return datetime.now(timezone.utc)


class ValidationCase(Base):
    """A single labeled case in the validation dataset."""

    __tablename__ = "validation_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(200), index=True, nullable=False)
    case_ref = Column(String(200), nullable=False)  # external case ID
    instrument_category = Column(String(100), nullable=False)
    finding_category = Column(String(100), nullable=False)
    ground_truth = Column(Boolean, nullable=False)  # True=positive, False=negative
    ai_prediction = Column(Boolean, nullable=True)  # AI output
    ai_confidence = Column(Float, default=0.0)
    human_prediction = Column(Boolean, nullable=True)  # human reader output
    reader_role = Column(String(100), default="")  # technician|educator|manager
    is_critical = Column(Boolean, default=False)  # crack|corrosion|insulation
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_now)


class ValidationRun(Base):
    """An aggregated validation run result."""

    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(200), index=True, nullable=False)
    run_label = Column(String(200), nullable=False)  # e.g. "Q1-2026-site-A"
    finding_category = Column(String(100), nullable=False)
    reader_type = Column(String(100), nullable=False)  # "ai" | "human" | role name
    tp = Column(Integer, default=0)
    tn = Column(Integer, default=0)
    fp = Column(Integer, default=0)
    fn = Column(Integer, default=0)
    precision = Column(Float, default=0.0)
    recall = Column(Float, default=0.0)
    specificity = Column(Float, default=0.0)
    f1 = Column(Float, default=0.0)
    kappa = Column(Float, default=0.0)
    auc = Column(Float, default=0.0)
    case_count = Column(Integer, default=0)
    data_source = Column(String(50), default="mock")
    run_at = Column(DateTime(timezone=True), default=_now)
