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

    # Added for LumenAI Network v5.3 -- Project Genesis AI, Section 1 (Global
    # Instrument Registry). Purely additive: the pre-existing columns above
    # and instrument_registry_service.py's seeded-mock-fallback behavior are
    # untouched.
    instrument_family = Column(String, nullable=True)
    ifu_versions_json = Column(String, nullable=True, default="[]")
    anatomy_profile_id = Column(Integer, nullable=True)
    inspection_zones_json = Column(String, nullable=True, default="[]")
    digital_twin_template_ref = Column(String, nullable=True)
    baseline_template_ref = Column(String, nullable=True)
    failure_modes_json = Column(String, nullable=True, default="[]")
    repair_guidance = Column(String, nullable=True)
    knowledge_references_json = Column(String, nullable=True, default="[]")
