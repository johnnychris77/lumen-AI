"""P20: Network Intelligence Platform & Market Leadership — data models.

Covers:
  - National SPD Registry (Phase 1)
  - Instrument Lifecycle Intelligence (Phase 2)
  - Recall Early Warning System (Phase 3)
  - Research Data Exchange (Phase 4)
  - Executive Intelligence (Phase 5)

Privacy: tenant_id/facility_id are NEVER exposed in cross-network aggregates.
k-anonymity floor of 5 is enforced at the route layer. All cross-network
records carry anonymized pseudonyms only. No causation claims; all signals
require human review before action.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


# ---------------------------------------------------------------------------
# Phase 1: National SPD Registry
# ---------------------------------------------------------------------------

class SPDRegistryEntry(Base):
    """One registered SPD department in the national network.

    Facility identity is protected via pseudonym (rotated periodically).
    Coarse attributes only — never exact bed count, exact address, or name.
    """
    __tablename__ = "p20_spd_registry"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)          # internal use only, not published
    facility_pseudonym = Column(String, nullable=False, unique=True) # rotating anonymized ID
    facility_type = Column(String, default="hospital")              # hospital/health_system/asc/ltac
    bed_count_range = Column(String, nullable=True)                 # "100-299", "300-499", "500+"
    region = Column(String, nullable=True)                          # northeast/southeast/midwest/west/mountain
    annual_case_volume_range = Column(String, nullable=True)        # "<5000","5000-15000",">15000"
    sterilization_methods = Column(String, nullable=True)           # comma-separated: steam,eto,vhp
    registry_status = Column(String, default="active")             # active/suspended/withdrawn
    participation_tier = Column(String, default="contributor")      # observer/contributor/full_member
    opted_in_at = Column(DateTime, default=datetime.utcnow)
    last_data_contribution = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IntelligenceSharingAgreement(Base):
    """Participation agreement record — opt-in, reversible, audit-logged."""
    __tablename__ = "p20_intelligence_sharing_agreements"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    agreement_version = Column(String, default="1.0")
    agreed_at = Column(DateTime, default=datetime.utcnow)
    agreed_by = Column(String, nullable=False)           # user who accepted
    withdrawn_at = Column(DateTime, nullable=True)
    withdrawn_by = Column(String, nullable=True)
    status = Column(String, default="active")            # active/withdrawn
    sharing_scope = Column(String, default="benchmark")  # benchmark/research/full


class NetworkAggregateSnapshot(Base):
    """Point-in-time anonymized aggregate for the intelligence network.

    Never contains raw tenant data. Noise applied; k-anonymity floor enforced.
    """
    __tablename__ = "p20_network_aggregate_snapshots"

    id = Column(Integer, primary_key=True)
    captured_at = Column(DateTime, default=datetime.utcnow)
    metric_name = Column(String, nullable=False)
    cohort = Column(String, default="all")              # all/hospital/asc/region
    cohort_value = Column(String, nullable=True)
    n_participants = Column(Integer, nullable=False)    # must be >= 5
    p25 = Column(Float, nullable=True)
    p50 = Column(Float, nullable=False)
    p75 = Column(Float, nullable=True)
    p90 = Column(Float, nullable=True)
    mean = Column(Float, nullable=False)
    noise_applied = Column(Boolean, default=True)
    captured_by = Column(String, nullable=True)


# ---------------------------------------------------------------------------
# Phase 2: Instrument Lifecycle Intelligence
# ---------------------------------------------------------------------------

class InstrumentLifecycleRecord(Base):
    """Full lifecycle record for a tracked instrument at a given facility.

    Tenant-scoped: one facility's view of one instrument.
    Cross-network anonymized aggregates are derived separately.
    """
    __tablename__ = "p20_instrument_lifecycle"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    facility_id = Column(String, nullable=False, index=True)
    instrument_uid = Column(String, nullable=False, index=True)  # internal UID
    udi = Column(String, nullable=True)                          # FDA UDI if available
    manufacturer_name = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    instrument_category = Column(String, nullable=False)
    serial_number = Column(String, nullable=True)

    # Lifecycle stages
    acquisition_date = Column(DateTime, nullable=True)
    acquisition_source = Column(String, nullable=True)  # new_purchase/transfer/loaner
    first_inspection_date = Column(DateTime, nullable=True)
    last_inspection_date = Column(DateTime, nullable=True)
    total_inspections = Column(Integer, default=0)
    total_defects_found = Column(Integer, default=0)
    total_repairs = Column(Integer, default=0)
    last_repair_date = Column(DateTime, nullable=True)
    last_repair_type = Column(String, nullable=True)    # vendor_repair/in_house/replacement_part
    replacement_recommended_at = Column(DateTime, nullable=True)
    replacement_recommended_by = Column(String, nullable=True)
    retired_at = Column(DateTime, nullable=True)
    retirement_reason = Column(String, nullable=True)   # end_of_life/recall/beyond_repair/lost

    lifecycle_status = Column(String, default="active") # active/repair/retired/recalled
    defect_rate = Column(Float, default=0.0)            # rolling rate
    estimated_remaining_cycles = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class LifecycleEvent(Base):
    """Immutable event log for an instrument's lifecycle — acquisition→retirement."""
    __tablename__ = "p20_lifecycle_events"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    instrument_uid = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)  # acquired/inspected/repaired/replacement_recommended/retired/recalled
    event_date = Column(DateTime, default=datetime.utcnow)
    performed_by = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    outcome = Column(String, nullable=True)      # pass/fail/repaired/retired
    cost_usd = Column(Float, nullable=True)      # repair/replacement cost if applicable
    created_at = Column(DateTime, default=datetime.utcnow)


class LifecycleBenchmark(Base):
    """Anonymized cross-network lifecycle benchmark (instrument category level).

    k-anonymity floor of 5 enforced. Laplace noise applied to all numeric fields.
    Never contains facility or tenant identity.
    """
    __tablename__ = "p20_lifecycle_benchmarks"

    id = Column(Integer, primary_key=True)
    instrument_category = Column(String, nullable=False)
    metric_name = Column(String, nullable=False)     # median_lifespan_cycles/repair_rate/defect_rate
    cohort = Column(String, default="all")
    n_facilities = Column(Integer, nullable=False)   # >= 5
    p50 = Column(Float, nullable=False)
    p75 = Column(Float, nullable=True)
    p90 = Column(Float, nullable=True)
    mean = Column(Float, nullable=False)
    noise_applied = Column(Boolean, default=True)
    computed_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 3: Recall Early Warning System
# ---------------------------------------------------------------------------

class RecallEarlyWarning(Base):
    """Aggregated early-warning signal surfaced before formal recall announcement.

    Candidate signal only — requires human review and steward approval before
    any escalation or external notification. No causation claim.
    """
    __tablename__ = "p20_recall_early_warnings"

    id = Column(Integer, primary_key=True)
    signal_ref = Column(String, unique=True, nullable=False)     # internal ref e.g. REW-2026-001
    instrument_category = Column(String, nullable=False)
    manufacturer_pseudonym = Column(String, nullable=True)       # anonymized, never real name in DB
    model_pseudonym = Column(String, nullable=True)              # anonymized
    finding_type = Column(String, nullable=False)                # contamination/defect/failure/corrosion
    anomaly_score = Column(Float, nullable=False)                # 0.0–1.0; higher = stronger signal
    n_facilities_reporting = Column(Integer, nullable=False)     # k-floor: >= 3 to surface internally
    first_observed = Column(DateTime, nullable=False)
    last_observed = Column(DateTime, nullable=False)
    trend = Column(String, default="stable")                     # increasing/stable/decreasing
    warning_level = Column(String, default="watch")              # watch/advisory/alert
    status = Column(String, default="candidate")                 # candidate/under_review/escalated/closed/suppressed
    human_review_required = Column(Boolean, default=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    escalated_to_steward_at = Column(DateTime, nullable=True)
    steward_decision = Column(String, nullable=True)             # notify_fda/monitor/close
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ManufacturerIntelligenceProfile(Base):
    """Anonymized aggregate intelligence profile per manufacturer (category level).

    Manufacturer is identified by pseudonym in published data. Internal mapping
    is governance-controlled and never published.
    """
    __tablename__ = "p20_manufacturer_intelligence"

    id = Column(Integer, primary_key=True)
    manufacturer_pseudonym = Column(String, nullable=False, index=True)
    instrument_category = Column(String, nullable=False)
    n_facilities_contributing = Column(Integer, nullable=False)  # >= 5 to publish
    network_defect_rate = Column(Float, nullable=False)
    network_pass_rate = Column(Float, nullable=False)
    network_repair_rate = Column(Float, nullable=False)
    open_early_warnings = Column(Integer, default=0)
    formal_recall_count = Column(Integer, default=0)
    intelligence_grade = Column(String, default="B")  # A/B/C/D/F based on aggregated performance
    last_computed = Column(DateTime, default=datetime.utcnow)
    noise_applied = Column(Boolean, default=True)


class AnomalyDetectionRun(Base):
    """Log of each automated anomaly-detection scan against the network aggregate."""
    __tablename__ = "p20_anomaly_detection_runs"

    id = Column(Integer, primary_key=True)
    run_at = Column(DateTime, default=datetime.utcnow)
    triggered_by = Column(String, default="scheduled")  # scheduled/manual
    instrument_categories_scanned = Column(Integer, default=0)
    signals_surfaced = Column(Integer, default=0)
    signals_escalated = Column(Integer, default=0)
    run_status = Column(String, default="complete")     # complete/partial/failed
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Phase 4: Research Data Exchange
# ---------------------------------------------------------------------------

class ResearchDataset(Base):
    """Anonymized research dataset derived from the network aggregate.

    Never contains raw records. All fields anonymized + noise-applied.
    IRB/governance sign-off required before release.
    """
    __tablename__ = "p20_research_datasets"

    id = Column(Integer, primary_key=True)
    dataset_ref = Column(String, unique=True, nullable=False)    # e.g. RDS-2026-001
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    dataset_type = Column(String, nullable=False)                # benchmark_series/lifecycle_cohort/recall_signal_cohort
    instrument_categories = Column(String, nullable=True)        # comma-separated
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    n_facilities_contributing = Column(Integer, nullable=False)  # >= 5
    n_records = Column(Integer, nullable=False)
    anonymization_method = Column(String, default="pseudonym+noise+k_anonymity")
    k_floor = Column(Integer, default=5)
    irb_approval_number = Column(String, nullable=True)
    governance_approved = Column(Boolean, default=False)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    release_status = Column(String, default="draft")             # draft/under_review/approved/released/withdrawn
    released_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchStudy(Base):
    """Research study record linked to one or more released datasets."""
    __tablename__ = "p20_research_studies"

    id = Column(Integer, primary_key=True)
    study_ref = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    principal_investigator = Column(String, nullable=False)
    institution = Column(String, nullable=True)
    study_type = Column(String, default="observational")         # observational/retrospective/quality_improvement
    dataset_refs = Column(String, nullable=True)                 # comma-separated dataset_refs
    status = Column(String, default="proposed")                  # proposed/approved/active/completed/published
    irb_approval_number = Column(String, nullable=True)
    publication_doi = Column(String, nullable=True)
    claims_discipline_acknowledged = Column(Boolean, default=False)  # PI acknowledged no-causation rule
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ResearchPublication(Base):
    """Publication record for a completed study — LumenAI network data cited."""
    __tablename__ = "p20_research_publications"

    id = Column(Integer, primary_key=True)
    study_ref = Column(String, nullable=False, index=True)
    publication_title = Column(String, nullable=False)
    journal = Column(String, nullable=True)
    doi = Column(String, nullable=True)
    published_date = Column(DateTime, nullable=True)
    lumenai_data_cited = Column(Boolean, default=True)
    causation_claim_present = Column(Boolean, default=False)     # must be False for governance approval
    governance_cleared = Column(Boolean, default=False)
    cleared_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Phase 5: Executive Intelligence
# ---------------------------------------------------------------------------

class ExecutiveIntelligenceDashboard(Base):
    """Named executive intelligence dashboard configuration per tenant."""
    __tablename__ = "p20_executive_dashboards"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    dashboard_name = Column(String, nullable=False)
    dashboard_type = Column(String, default="national_benchmark")  # national_benchmark/manufacturer/lifecycle/recall_watch
    config_json = Column(Text, nullable=True)                      # selected metrics, filters
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ExecutiveIntelligenceSnapshot(Base):
    """Point-in-time snapshot of executive intelligence KPIs for a tenant.

    Benchmarks shown here are anonymized aggregates — tenant's own data
    positioned against the network without exposing peers.
    """
    __tablename__ = "p20_executive_snapshots"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    captured_at = Column(DateTime, default=datetime.utcnow)
    network_pass_rate_p50 = Column(Float, nullable=True)          # anonymized network median
    tenant_pass_rate = Column(Float, nullable=True)               # this tenant's own rate
    network_defect_rate_p50 = Column(Float, nullable=True)
    tenant_defect_rate = Column(Float, nullable=True)
    open_early_warnings_network = Column(Integer, default=0)
    tenant_recall_exposure_score = Column(Float, default=0.0)     # 0–100, higher = more exposure
    accreditation_readiness_score = Column(Float, nullable=True)
    network_percentile = Column(Float, nullable=True)             # where tenant sits vs network
    human_review_required = Column(Boolean, default=True)
    captured_by = Column(String, nullable=True)
