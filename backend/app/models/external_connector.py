"""P16: External system connector models for patient safety integration."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.db.base import Base


class ExternalSystemConnector(Base):
    __tablename__ = "external_system_connectors"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    system_name = Column(String, nullable=False)  # "safecare", "rldatix", "midas", etc.
    system_category = Column(
        String, nullable=False
    )  # "spd_tracking", "quality_event", "infection_prevention", "vendor", "ehr"
    connection_status = Column(
        String, default="configured"
    )  # configured/active/error/disabled
    last_sync_at = Column(DateTime, nullable=True)
    events_imported = Column(Integer, default=0)
    config_json = Column(Text, nullable=True)  # non-sensitive config (endpoint URL, etc.)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ExternalEventImport(Base):
    __tablename__ = "external_event_imports"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    connector_id = Column(Integer, ForeignKey("external_system_connectors.id"), nullable=True)
    external_event_id = Column(String, nullable=True)  # ID from source system
    event_type = Column(
        String, nullable=False
    )  # "adverse_event", "near_miss", "capa", "hai", "sse"
    event_date = Column(DateTime, nullable=False)
    instrument_reference = Column(String, nullable=True)  # UDI/barcode from source system
    de_identified = Column(Boolean, default=True)
    raw_payload_hash = Column(String, nullable=True)  # SHA-256 of original, for audit
    imported_at = Column(DateTime, default=datetime.utcnow)
