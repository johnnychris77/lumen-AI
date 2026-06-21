"""P18 Mobile, Offline & Point-of-Use Inspection Platform models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


class OfflineInspectionSession(Base):
    __tablename__ = "offline_inspection_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    technician_id = Column(String, nullable=False)
    device_id = Column(String, nullable=True)
    instrument_id = Column(String, nullable=True)
    tray_id = Column(String, nullable=True)
    inspection_type = Column(String, default="standard")
    started_at_device = Column(DateTime, nullable=False)
    completed_at_device = Column(DateTime, nullable=True)
    sync_status = Column(String, default="PENDING_SYNC")
    synced_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    offline_findings_json = Column(Text, nullable=True)
    offline_capa_notes = Column(Text, nullable=True)
    image_count = Column(Integer, default=0)
    images_synced = Column(Integer, default=0)
    linked_inspection_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True)
    scan_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    scan_type = Column(String, nullable=False)
    decoded_value = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    scan_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    device_id = Column(String, nullable=True)
    image_ref = Column(String, nullable=True)
    instrument_id_resolved = Column(String, nullable=True)
    lookup_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class ImageCaptureSession(Base):
    __tablename__ = "image_capture_sessions"

    id = Column(Integer, primary_key=True)
    capture_session_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    inspection_session_id = Column(String, nullable=True)
    capture_type = Column(String, nullable=False)
    device_type = Column(String, default="camera")
    image_count = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)
    upload_status = Column(String, default="pending")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MobileNotification(Base):
    __tablename__ = "mobile_notifications"

    id = Column(Integer, primary_key=True)
    notification_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=True)
    recipient_id = Column(String, nullable=False)
    notification_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    priority = Column(String, default="normal")
    delivery_channel = Column(String, default="in_app")
    read_status = Column(String, default="unread")
    action_required = Column(Boolean, default=False)
    action_url = Column(String, nullable=True)
    action_taken = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeviceSession(Base):
    __tablename__ = "device_sessions"

    id = Column(Integer, primary_key=True)
    device_session_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    device_id = Column(String, nullable=False)
    device_type = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    auth_method = Column(String, default="token")
    is_active = Column(Boolean, default=True)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    remote_logout_requested = Column(Boolean, default=False)
    remote_wipe_requested = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class MobileSyncQueue(Base):
    __tablename__ = "mobile_sync_queue"

    id = Column(Integer, primary_key=True)
    queue_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True)
    tenant_id = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    payload_type = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    queue_status = Column(String, default="pending")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    queued_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
