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
from app.models.digital_quality_twin import (  # noqa: F401
    QualityTwinState,
    ScenarioSimulation,
    QualityForecast,
    InterventionModel,
    ExecutiveDecisionBrief,
    ForecastOutcome,
)
from app.models.global_intelligence import (  # noqa: F401
    GlobalIntelligenceSignal,
    InstrumentRiskRegistryEntry,
    GlobalRecallEarlyWarning,
    GSINParticipant,
    RegulatoryEvidencePackage,
)
from app.models.consent_record import ConsentRecord  # noqa: F401
from app.models.enterprise_hierarchy import (  # noqa: F401
    HealthSystem,
    EnterpriseMarket,
    EnterpriseRegion,
    EnterpriseFacility,
    EnterpriseDepartment,
    OnboardingWorkflow,
    EnterpriseBaseline,
    FacilityReadinessScore,
)
from app.models.customer_success import CustomerSuccessSnapshot  # noqa: F401
from app.models.growth import (  # noqa: F401
    StrategicPartnership, ReferenceCustomer, PartnershipNote, NetworkBenchmarkSnapshot,
)
from app.models.accreditation import (  # noqa: F401
    AccreditationProgram, EvidenceItem, ReadinessAssessment,
    SurveyEvidencePackage, CertifiedSite, BenchmarkPublication,
    AdvisoryBoardMember, CriteriaProposal,
)
from app.models.p20_network_intelligence import (  # noqa: F401
    SPDRegistryEntry, IntelligenceSharingAgreement, NetworkAggregateSnapshot,
    InstrumentLifecycleRecord, LifecycleEvent, LifecycleBenchmark,
    RecallEarlyWarning, ManufacturerIntelligenceProfile, AnomalyDetectionRun,
    ResearchDataset, ResearchStudy, ResearchPublication,
    ExecutiveIntelligenceDashboard, ExecutiveIntelligenceSnapshot,
)
from app.models.p22_operations import (  # noqa: F401
    OperationsWorkflow, WorkflowStep, WorkflowExecution, WorkflowStepExecution,
    WorkQueueItem, OperationalRiskSnapshot, CopilotQuery, CopilotRecommendation,
)
from app.models.p24_standards import (  # noqa: F401
    QualityStandard, BaselineGovernanceRecord, BenchmarkReport,
    RegionalDeployment, APIPartnerApplication, AdvisoryConsortiumMember, StandardsPublication,
)
from app.models.p25_infrastructure import (  # noqa: F401
    InstrumentDigitalIdentity, SurgicalReadinessScore, InstrumentPassportEvent,
    GlobalQualityRegistryEntry, IndustryAPICredential,
)


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(255), index=True, nullable=False)
    user_email = Column(String(255), index=True, nullable=False)
    role = Column(String(100), nullable=False, default="viewer")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tenant_region = Column(String(50), nullable=True, default="north_america")


__all__ = [
    "AuditLog",
    "Inspection",
    "User",
    "Review",
    "AlertEvent",
    "TenantMembership",
]
