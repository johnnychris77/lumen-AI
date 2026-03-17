from datetime import datetime, timezone
from app.models.inspection import Inspection
from app.models.user import User
from app.models.review import Review

__all__ = ["Inspection", "User", "Review"]

class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, nullable=False, index=True)
    vendor_name = Column(String(100), nullable=False, default="unknown")
    instrument_type = Column(String(100), nullable=False, default="unknown")
    detected_issue = Column(String(100), nullable=False, default="unknown")
    risk_score = Column(Integer, nullable=False, default=0)

    channel = Column(String(50), nullable=False)
    sent = Column(Boolean, nullable=False, default=False)
    status_code = Column(String(50), nullable=False, default="")
    failure_reason = Column(String(500), nullable=False, default="")
    dispatch_batch_id = Column(String(100), nullable=False, default="")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, nullable=False, index=True)
    vendor_name = Column(String(100), nullable=False, default="unknown")
    instrument_type = Column(String(100), nullable=False, default="unknown")
    detected_issue = Column(String(100), nullable=False, default="unknown")
    risk_score = Column(Integer, nullable=False, default=0)

    channel = Column(String(50), nullable=False)
    sent = Column(Boolean, nullable=False, default=False)
    status_code = Column(String(50), nullable=False, default="")
    failure_reason = Column(String(500), nullable=False, default="")
    dispatch_batch_id = Column(String(100), nullable=False, default="")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
