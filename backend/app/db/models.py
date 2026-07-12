from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.alert_event import AlertEvent
from app.models.audit_log import AuditLog
from app.models.inspection import Inspection
from app.models.review import Review
from app.models.user import User
from app.models.external_connector import ExternalSystemConnector, ExternalEventImport  # noqa: F401
# Pre-existing bug, fixed while building Project Vanguard's Governance
# Dashboard: `release_governance_dashboard.py`/`governance_sla.py`/
# `governance_sla_scanner.py` reference `models.LeadershipPacket`,
# `models.LeadershipPacketDelivery`, `models.PacketRelease`,
# `models.PacketReleaseHold`, `models.PacketReleaseOverride`,
# `models.GovernanceSlaEvent`, and `models.GovernanceSlaPolicy`, but none
# of these six models were ever imported here — every call into that
# whole release-governance/SLA dependency chain raised AttributeError,
# in any environment, since Python doesn't expose a submodule's classes
# without an import.
from app.models.governance_sla_event import GovernanceSlaEvent  # noqa: F401
from app.models.governance_sla_policy import GovernanceSlaPolicy  # noqa: F401
from app.models.leadership_packet import LeadershipPacket  # noqa: F401
from app.models.leadership_packet_delivery import LeadershipPacketDelivery  # noqa: F401
from app.models.packet_release import PacketRelease  # noqa: F401
from app.models.packet_release_hold import PacketReleaseHold  # noqa: F401
from app.models.packet_release_override import PacketReleaseOverride  # noqa: F401
# Same pre-existing gap: `governance_console.py`'s own
# `/governance-console/summary` route references `models.RetentionPolicy`,
# also never imported here.
from app.models.retention_policy import RetentionPolicy  # noqa: F401
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
from app.models.apollo_quality import (  # noqa: F401
    CustomerComplaint, QualityPolicy, QualityTwinSnapshot,
)
from app.models.athena_knowledge import (  # noqa: F401
    ExperienceGraphEdge, ExperienceGraphNode, KnowledgeMediaAttachment, KnowledgePreservationSession,
)
from app.models.phoenix_intelligence import (  # noqa: F401
    AIInferenceLatencySample, ImprovementRecommendation, InnovationIdea, PlatformMaturitySnapshot, ValidationOutcome,
)
from app.models.infinity_platform import (  # noqa: F401
    DeveloperAccount, DeveloperApiKey, DeveloperSandboxSession, MarketplaceInstallation,
    MarketplaceListing, MarketplaceRevenueEvent, PartnerLicense,
)
from app.models.olympus_network import (  # noqa: F401
    AIModelRegistryEntry, HIXExchangePackage, NetworkGovernanceCase, NetworkTrustSnapshot,
)
from app.models.guardianx_assurance import (  # noqa: F401
    AIAssuranceTrustSnapshot, AIExplainabilityRecord, AIModelRiskEntry,
    ComplianceCapabilityMapping, EvidenceLedgerEntry,
)
from app.models.genesis_ai_intelligence_cloud import (  # noqa: F401
    AnatomyProfile, ManufacturerKnowledgeUpdate,
)
from app.models.nova_agent_platform import (  # noqa: F401
    AgentCollaborationRequest, AgentDefinition, AgentMemoryEntry, AgentMessage, AgentTaskRun,
)
from app.models.vulcan_reliability import (  # noqa: F401
    VulcanFeedback, VulcanReliabilityAssessment, VulcanRepairEffectivenessAssessment,
)
from app.models.sage_education import (  # noqa: F401
    SageAssessment, SageEducationImageEntry, SageEffectivenessAssessment, SageFeedback,
    SageKnowledgeGap, SageLearningPlan, SageMicrolearningModule,
)
from app.models.veritas_evidence import (  # noqa: F401
    VeritasBaselineGovernanceAction, VeritasBaselineResolution, VeritasEvidenceConflict,
    VeritasEvidenceProvenanceRecord, VeritasEvidenceReadinessAssessment, VeritasFeedback,
    VeritasTrainingDatasetEntry,
)
from app.models.sentinelx_risk import (  # noqa: F401
    SentinelXPatientSafetyAlert, SentinelXRiskAssessment, SentinelXSupervisorOverride,
)
from app.models.maestro_orchestration import (  # noqa: F401
    MaestroDailyBrief, MaestroDecisionJournalEntry, MaestroOperationalHealthSnapshot,
    MaestroPriorityItem, MaestroRecommendation,
)
from app.models.council_leadership import (  # noqa: F401
    CouncilCase, CouncilDecisionOption, CouncilDissentRecord, CouncilHumanDecision,
    CouncilMeetingNotes, CouncilOutcomeReview, CouncilSpecialistAssessment, CouncilTeamConfig,
)
from app.models.governed_action import (  # noqa: F401
    GovernedAction, GovernedActionAuditEvent, GovernedActionOutcomeReview,
    GovernedActionResidualRiskReview, GovernedActionRollout, GovernedActionUnintendedConsequence,
    GovernedActionVerification,
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
