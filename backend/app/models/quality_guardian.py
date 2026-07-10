"""v2.9 — LumenAI Quality: Closed-Loop Quality Intelligence (Project Guardian).

Connects OR quality events to Digital Twin / Inspection / Technician / Tray /
Knowledge Graph / Root Cause / CAPA / Competency / Continuous Improvement.

Deliberately does NOT duplicate three systems that already exist in this
codebase:
  * CAPA — the real store is `capa_service.py`'s raw-sqlite `capas` table
    (see `docs/quality/capa-integration.md`: "no parallel CAPA system").
    `capa_lifecycle_service.py` extends that table additively (new nullable
    columns) rather than adding a second CAPA model here.
  * Root cause assignment — `RootCauseAssignment` (app/models/root_cause.py)
    already exists and is deliberately human-only ("never inferred
    automatically... would be a fabricated causal claim"). `RCADraft` below
    is an AI-drafted *suggestion* a supervisor edits and either approves
    (which calls the existing `root_cause_service.assign_root_cause` to
    create the real, human-confirmed assignment) or rejects — it never
    writes a RootCauseAssignment itself.
  * Competency events — `CompetencyEvent` (app/models/competency_event.py)
    remains the one event log; `CompetencyOpportunity` here is a derived
    signal computed from that log, not a second log.

Seven additive tables:
  * QualityEvent — Section 1 intake + Section 2 classification (kept on one
    row so the original narrative always sits alongside its structured
    interpretation, per the spec).
  * QualityTaxonomyTerm — Section 3, a versioned/configurable governed
    taxonomy (distinct from the AI agents' own finding-type vocabularies,
    which are left untouched).
  * EventCorrelation — Section 4, one row per attempted correlation target,
    with confidence and supervisor confirmation. Targets with no real
    tracked entity in LumenAI today (shift, washer, inspection session) are
    recorded honestly as untracked, never fabricated.
  * RCADraft — Section 5, AI-assisted draft RCA pending supervisor review.
  * CAPARecommendation — Section 6, a typed suggestion that, once accepted,
    materializes into the existing CAPA store via `capa_lifecycle_service`.
  * CompetencyOpportunity — Section 7, a derived coaching/education signal.
  * FirstPassYieldSnapshot — Section 8, persisted FPY rollups for trending.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 1 — intake sources ──────────────────────────────────────────────
SOURCE_SAFECARE = "safecare"
SOURCE_RLDATIX = "rldatix"
SOURCE_MIDAS = "midas"
SOURCE_OCCURRENCE_REPORTING = "occurrence_reporting"
SOURCE_CSV_IMPORT = "csv_import"
SOURCE_MANUAL = "manual"
SOURCE_FHIR_HL7 = "fhir_hl7"
SOURCE_SYSTEMS = [
    SOURCE_SAFECARE, SOURCE_RLDATIX, SOURCE_MIDAS, SOURCE_OCCURRENCE_REPORTING,
    SOURCE_CSV_IMPORT, SOURCE_MANUAL, SOURCE_FHIR_HL7,
]

SEVERITIES = ["low", "medium", "high", "critical"]

# ── Section 3 — SPD Quality Taxonomy (versioned, configurable) ─────────────
CATEGORY_ORGANIC_RESIDUE = "organic_residue"
CATEGORY_INSTRUMENT_CONDITION = "instrument_condition"
CATEGORY_ASSEMBLY = "assembly"
CATEGORY_PACKAGING = "packaging"
CATEGORY_STERILIZATION_INDICATORS = "sterilization_indicators"
CATEGORY_UNKNOWN = "unknown"

TAXONOMY_VERSION = 1
DEFAULT_TAXONOMY: dict[str, list[str]] = {
    CATEGORY_ORGANIC_RESIDUE: ["blood", "bone", "tissue", "protein", "debris"],
    CATEGORY_INSTRUMENT_CONDITION: ["rust", "corrosion", "pitting", "crack", "wear"],
    CATEGORY_ASSEMBLY: ["missing_instrument", "wrong_instrument", "missing_component"],
    CATEGORY_PACKAGING: ["wet_tray", "wrapper_tear", "filter_failure", "missing_lock"],
    CATEGORY_STERILIZATION_INDICATORS: ["failed_indicator", "missing_indicator"],
    CATEGORY_UNKNOWN: ["requires_supervisor_classification"],
}

# ── Section 4 — correlation targets ─────────────────────────────────────────
TARGET_CASE = "case"
TARGET_PROCEDURE = "procedure"
TARGET_TRAY = "tray"
TARGET_DIGITAL_TWIN = "digital_twin"
TARGET_INSPECTION = "inspection"
TARGET_TECHNICIAN = "technician"
TARGET_SHIFT = "shift"
TARGET_SUPERVISOR = "supervisor"
TARGET_WASHER = "washer"
TARGET_INSPECTION_SESSION = "inspection_session"
TARGET_MANUFACTURER_BASELINE = "manufacturer_baseline"
CORRELATION_TARGETS = [
    TARGET_CASE, TARGET_PROCEDURE, TARGET_TRAY, TARGET_DIGITAL_TWIN, TARGET_INSPECTION,
    TARGET_TECHNICIAN, TARGET_SHIFT, TARGET_SUPERVISOR, TARGET_WASHER,
    TARGET_INSPECTION_SESSION, TARGET_MANUFACTURER_BASELINE,
]
# LumenAI does not persist these as real entities today — correlation attempts
# against them are recorded honestly as untracked, never fabricated.
UNTRACKED_TARGETS = {TARGET_SHIFT, TARGET_WASHER, TARGET_INSPECTION_SESSION}

# ── Section 6 — CAPA recommendation types ───────────────────────────────────
RECOMMEND_EDUCATION = "education"
RECOMMEND_COMPETENCY_REVIEW = "competency_review"
RECOMMEND_POLICY_REVIEW = "policy_review"
RECOMMEND_EQUIPMENT_EVALUATION = "equipment_evaluation"
RECOMMEND_REPAIR_REFERRAL = "repair_referral"
RECOMMEND_PROCESS_AUDIT = "process_audit"
RECOMMEND_OBSERVATION = "observation"
RECOMMEND_FOLLOW_UP_INSPECTION = "follow_up_inspection"
RECOMMENDATION_TYPES = [
    RECOMMEND_EDUCATION, RECOMMEND_COMPETENCY_REVIEW, RECOMMEND_POLICY_REVIEW,
    RECOMMEND_EQUIPMENT_EVALUATION, RECOMMEND_REPAIR_REFERRAL, RECOMMEND_PROCESS_AUDIT,
    RECOMMEND_OBSERVATION, RECOMMEND_FOLLOW_UP_INSPECTION,
]

# ── Section 7 — competency opportunity types ────────────────────────────────
OPPORTUNITY_COACHING = "coaching"
OPPORTUNITY_TEAM_EDUCATION = "team_education"
OPPORTUNITY_DEPARTMENT_RETRAINING = "department_retraining"
OPPORTUNITY_ANNUAL_COMPETENCY = "annual_competency"
OPPORTUNITY_RECURRING_LEARNING = "recurring_learning"
OPPORTUNITY_TYPES = [
    OPPORTUNITY_COACHING, OPPORTUNITY_TEAM_EDUCATION, OPPORTUNITY_DEPARTMENT_RETRAINING,
    OPPORTUNITY_ANNUAL_COMPETENCY, OPPORTUNITY_RECURRING_LEARNING,
]

DISCLAIMER = (
    "LumenAI Quality transforms perioperative quality feedback into structured SPD intelligence "
    "for decision support only. Classifications, correlations, draft root causes, and CAPA "
    "recommendations are potential associations, not causal determinations — human review and "
    "approval are required before any classification, root cause, or corrective action is finalized."
)


class QualityEvent(Base):
    __tablename__ = "quality_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    event_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    source_system: Mapped[str] = mapped_column(String(30), default=SOURCE_MANUAL, nullable=False, index=True)
    external_event_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    facility_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    procedure: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    service_line: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    case_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    reporter_role: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False, index=True)
    attachments_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Section 2 — Clinical NLP Classification (nullable until classified;
    # narrative above is never overwritten by classification).
    instrument_type_guess: Mapped[str | None] = mapped_column(String(100), nullable=True)
    finding_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    spd_category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    classification_risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requires_supervisor_classification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Section 10 — Quality Learning Loop trigger.
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QualityTaxonomyTerm(Base):
    __tablename__ = "quality_taxonomy_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    term: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    display_label: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=TAXONOMY_VERSION, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EventCorrelation(Base):
    __tablename__ = "quality_event_correlations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    event_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tracked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)

    supervisor_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RCADraft(Base):
    __tablename__ = "quality_rca_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    event_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    likely_process_stage: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    contributing_factors_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    historical_recurrence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    similar_events_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    investigation_questions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    supervisor_edits: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # draft | approved | rejected
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    approved_root_cause: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    root_cause_assignment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class CAPARecommendation(Base):
    __tablename__ = "quality_capa_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    rca_draft_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    recommendation_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # suggested | accepted | dismissed
    status: Mapped[str] = mapped_column(String(20), default="suggested", nullable=False, index=True)
    created_capa_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    decided_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompetencyOpportunity(Base):
    __tablename__ = "quality_competency_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    # individual | team | department
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    opportunity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    finding_type: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # open | addressed
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    addressed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effectiveness_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class FirstPassYieldSnapshot(Base):
    __tablename__ = "quality_fpy_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    # department | instrument | technician | facility
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    total_pass_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confirmed_miss_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    true_fpy_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    false_pass_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
