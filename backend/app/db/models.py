from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.alert_event import AlertEvent
from app.models.audit_log import AuditLog
from app.models.inspection import Inspection
from app.models.review import Review
from app.models.user import User
from app.models.external_connector import ExternalSystemConnector, ExternalEventImport  # noqa: F401
from app.models.patient_safety import (  # noqa: F401
    InstrumentQualitySignal,
    PatientSafetyEventLink,
    PotentialHarmSignal,
    NearMissCorrelation,
    QualityInvestigation,
    InfectionPreventionSignal,
    CAPAEffectivenessSignal,
    ExecutiveRiskSignal,
)
from app.models.quality_intelligence import (  # noqa: F401
    EnterpriseRiskNode,
    EnterpriseRiskEdge,
    EmergingRiskSignal,
    QualityInvestigationP21,
    PreventiveActionRecommendation,
)


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), index=True, nullable=False)
    user_email = Column(String(255), index=True, nullable=False)
    role = Column(String(100), nullable=False, default="viewer")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


__all__ = [
    "AuditLog",
    "Inspection",
    "User",
    "Review",
    "AlertEvent",
    "TenantMembership",
]
