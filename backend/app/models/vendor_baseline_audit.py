from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

try:
    from app.db.base import Base
except ImportError:
    from app.database import Base


class VendorBaselineAuditEvent(Base):
    __tablename__ = "vendor_baseline_audit_events"

    id = Column(Integer, primary_key=True, index=True)

    baseline_id = Column(Integer, index=True, nullable=False)

    event_type = Column(String(100), nullable=False)
    actor = Column(String(255), nullable=True)
    actor_role = Column(String(100), nullable=True)

    decision = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    evidence_source = Column(Text, nullable=True)

    finding_id = Column(Integer, nullable=True)
    inspection_id = Column(Integer, nullable=True)

    matched_identifier_type = Column(String(100), nullable=True)
    matched_identifier_value = Column(String(255), nullable=True)

    previous_status = Column(String(100), nullable=True)
    new_status = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
