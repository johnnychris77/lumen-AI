"""P15: National SPD Intelligence Network — instrument registry model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from app.db.base import Base


class RegistryInstrument(Base):
    __tablename__ = "registry_instruments"

    id = Column(Integer, primary_key=True)
    udi = Column(String, nullable=True, index=True)
    barcode = Column(String, nullable=True, index=True)
    qr_code = Column(String, nullable=True)
    keydot_id = Column(String, nullable=True)
    manufacturer_name = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    instrument_category = Column(String, nullable=False)
    sterilization_method = Column(String, nullable=True)
    ifu_reference = Column(String, nullable=True)
    network_inspection_count = Column(Integer, default=0)  # aggregate across network
    network_defect_rate = Column(Float, default=0.0)  # anonymized aggregate
    network_pass_rate = Column(Float, default=1.0)
    contributing_facilities = Column(Integer, default=0)  # N contributing (>=5 to publish)
    registry_status = Column(String, default="active")  # active/recalled/discontinued
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
