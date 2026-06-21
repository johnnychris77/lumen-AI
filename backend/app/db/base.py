from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.models.integrations import (  # noqa: F401
    ExternalSystemConnection,
    IntegrationImportRun,
    InstrumentTrackingRecord,
    TrayTrackingRecord,
    SterilizationCycleRecord,
    RepairHistoryRecord,
    QualitySafetyEventRecord,
    InfectionPreventionEventRecord,
    PatientImpactCorrelationCandidate,
    VendorBaselineExternalRecord,
    RecallExternalRecord,
    IntegrationErrorRecord,
)
