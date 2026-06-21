"""P15: National SPD Intelligence Network — baseline library model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base


class BaselineLibraryEntry(Base):
    __tablename__ = "baseline_library"

    id = Column(Integer, primary_key=True)
    udi = Column(String, nullable=True, index=True)
    instrument_category = Column(String, nullable=False)
    manufacturer_name = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    baseline_type = Column(String, default="manufacturer")  # manufacturer/vendor/network_contributed
    baseline_version = Column(String, default="1.0")
    approval_status = Column(String, default="pending")  # pending/approved/deprecated
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    contributing_facilities = Column(Integer, default=1)
    governance_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
