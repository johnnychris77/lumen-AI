"""P17 Healthcare Quality & Safety Ecosystem Integration models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


class ExternalSystemConnection(Base):
    __tablename__ = "external_system_connections"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    system_name = Column(String, nullable=False)
    system_category = Column(String, nullable=False)
    connector_type = Column(String, default="api_pull")
    connection_status = Column(String, default="configured")
    endpoint_url = Column(String, nullable=True)
    auth_type = Column(String, nullable=True)
    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String, nullable=True)
    last_import_at = Column(DateTime, nullable=True)
    total_records_imported = Column(Integer, default=0)
    consecutive_errors = Column(Integer, default=0)
    config_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class IntegrationImportRun(Base):
    __tablename__ = "integration_import_runs"

    id = Column(Integer, primary_key=True)
    import_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    connection_id = Column(Integer, nullable=True)
    system_name = Column(String, nullable=False)
    import_type = Column(String, nullable=False)
    status = Column(String, default="running")
    records_attempted = Column(Integer, default=0)
    records_imported = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_summary = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class InstrumentTrackingRecord(Base):
    __tablename__ = "instrument_tracking_records"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    source_system = Column(String, nullable=False)
    source_record_id = Column(String, nullable=True)
    source_event_type = Column(String, nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    instrument_id = Column(String, nullable=True)
    udi = Column(String, nullable=True)
    barcode = Column(String, nullable=True)
    qr_code = Column(String, nullable=True)
    keydot_id = Column(String, nullable=True)
    tray_id = Column(String, nullable=True)
    sterilization_status = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    import_status = Column(String, default="imported")
    raw_payload_hash = Column(String, nullable=True)
    correlation_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class TrayTrackingRecord(Base):
    __tablename__ = "tray_tracking_records"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    source_system = Column(String, nullable=False)
    source_record_id = Column(String, nullable=True)
    source_event_type = Column(String, nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    tray_id = Column(String, nullable=True)
    tray_name = Column(String, nullable=True)
    service_line = Column(String, nullable=True)
    instrument_count = Column(Integer, nullable=True)
    sterilization_status = Column(String, nullable=True)
    import_status = Column(String, default="imported")
    raw_payload_hash = Column(String, nullable=True)
    correlation_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class SterilizationCycleRecord(Base):
    __tablename__ = "sterilization_cycle_records"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    source_system = Column(String, nullable=False)
    source_record_id = Column(String, nullable=True)
    source_event_type = Column(String, default="sterilization_cycle")
    event_timestamp = Column(DateTime, nullable=False)
    cycle_id = Column(String, nullable=True)
    sterilizer_id = Column(String, nullable=True)
    cycle_type = Column(String, nullable=True)
    cycle_status = Column(String, nullable=True)
    tray_ids = Column(Text, nullable=True)
    import_status = Column(String, default="imported")
    raw_payload_hash = Column(String, nullable=True)
    correlation_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class RepairHistoryRecord(Base):
    __tablename__ = "repair_history_records"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    source_system = Column(String, nullable=False)
    source_record_id = Column(String, nullable=True)
    source_event_type = Column(String, default="repair")
    event_timestamp = Column(DateTime, nullable=False)
    instrument_id = Column(String, nullable=True)
    udi = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    repair_type = Column(String, nullable=True)
    repair_status = Column(String, nullable=True)
    defect_description = Column(Text, nullable=True)
    import_status = Column(String, default="imported")
    raw_payload_hash = Column(String, nullable=True)
    correlation_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class QualitySafetyEventRecord(Base):
    __tablename__ = "quality_safety_event_records"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    source_system = Column(String, nullable=False)
    source_record_id = Column(String, nullable=True)
    source_event_type = Column(String, nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    event_category = Column(String, nullable=True)
    event_severity = Column(String, nullable=True)
    instrument_reference = Column(String, nullable=True)
    tray_reference = Column(String, nullable=True)
    de_identified = Column(Boolean, default=True)
    capa_id = Column(String, nullable=True)
    rca_status = Column(String, nullable=True)
    import_status = Column(String, default="imported")
    raw_payload_hash = Column(String, nullable=True)
    correlation_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class InfectionPreventionEventRecord(Base):
    __tablename__ = "infection_prevention_event_records"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    source_system = Column(String, nullable=False)
    source_record_id = Column(String, nullable=True)
    source_event_type = Column(String, nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    pathogen = Column(String, nullable=True)
    procedure_type = Column(String, nullable=True)
    service_line = Column(String, nullable=True)
    instrument_reference = Column(String, nullable=True)
    de_identified = Column(Boolean, default=True)
    import_status = Column(String, default="imported")
    raw_payload_hash = Column(String, nullable=True)
    correlation_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class PatientImpactCorrelationCandidate(Base):
    __tablename__ = "patient_impact_correlation_candidates"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    instrument_tracking_record_id = Column(Integer, nullable=True)
    quality_safety_event_record_id = Column(Integer, nullable=True)
    infection_prevention_event_record_id = Column(Integer, nullable=True)
    repair_history_record_id = Column(Integer, nullable=True)
    instrument_id = Column(String, nullable=True)
    tray_id = Column(String, nullable=True)
    udi = Column(String, nullable=True)
    barcode = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    association_score = Column(Float, default=0.5)
    confidence_score = Column(Float, default=0.5)
    association_reason = Column(Text, nullable=True)
    recommended_review_action = Column(Text, nullable=True)
    human_review_required = Column(Boolean, default=True)
    human_review_status = Column(String, default="pending")
    correlation_method = Column(String, default="instrument_id_match")
    created_at = Column(DateTime, default=datetime.utcnow)
