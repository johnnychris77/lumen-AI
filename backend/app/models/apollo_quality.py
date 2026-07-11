"""v4.7 — LumenAI OS: Project Apollo — Autonomous Clinical Quality
Management System (CQMS).

## Naming disambiguation (read this first)

Before writing any Apollo code, every existing quality-adjacent surface
was read in full — this codebase already has an extensive quality
management ecosystem across five prior sprints:

  * **`/api/quality`** (`app/routes/quality_dashboard.py`, v1.5) already
    owns this exact prefix (`/dashboard`, `/finding-trends`,
    `/root-cause`, `/capa-suggestions`, `/improvement-initiatives`, etc.)
    — Apollo's backend is mounted at **`/api/apollo`** instead.
  * Frontend routes `/quality-command-center`, `/quality-intelligence`,
    and `/quality-dashboard` are all already taken by earlier sprints.
    **`/quality`** (bare, exact) was confirmed free and is Apollo's new
    Quality Management Center root — deliberately positioned as the
    unifying front door across all of them, not a fourth competing page.
  * **CAPA**: `capa_service.py` (the canonical sqlite-backed store) +
    `capa_lifecycle_service.py` (the open→assigned→in_progress→
    verified→closed state machine, added in v2.9) together already cover
    Owner/Root-Cause-link/Actions/Verification/Closure. Apollo does not
    add a sixth CAPA store (a legacy `EnterpriseCapa` table and a
    `CAPARecommendation` suggestion queue already exist too) — it
    extends `capa_suggestion_service.py`'s existing auto-trigger
    detectors with the specific new trigger types this sprint's brief
    names that don't already exist (repeat repairs, supervisor
    overrides, AI confidence decline, inspection failures, customer
    complaints — repeated blood findings and repeated corrosion are
    already detected by that service's existing zone/condition
    counters).
  * **Root cause**: `RootCauseAssignment` (human-assigned, never
    inferred) + `RCADraft`/`rca_engine_service` (AI-assisted evidence/
    historical-recurrence/similar-events drafting, supervisor-approved)
    already exist. Apollo adds a *structuring layer* (5 Whys/Fishbone/
    Pareto/Trend Analysis views) over these, never a new root-cause data
    model, and never a path that finalizes a root cause without the
    existing `rca_engine_service.approve_draft` supervisor step.
  * **Audits**: `accreditation_engine.py` + `regulatory_standards_
    catalogue.py` already cover Joint Commission, AAMI ST79, FDA, CMS,
    ISO. Apollo extends the standards catalogue and `generate_audit_
    package`'s `package_type` enum with AAMI ST91, AORN, DNV, Internal,
    and Vendor — it does not add a second audit-package generator.
  * **Standards**: `beacon_standards_service.py` (governed publications)
    and `p24_standards_service.py` (internal quality-classification
    standards) already exist; Apollo composes both plus the regulatory
    catalogue into one Standards Knowledge Library view.
  * **Competencies**: `competency_service.py`'s single `CompetencyEvent`
    log already tracks findings-reviewed/supervisor-corrections/
    repeated-errors/education-completed. Apollo adds four new event
    types (annual competency, procedure validation, simulation result,
    knowledge contribution) to the *same* log rather than a parallel
    competency model.
  * **Continuous Improvement**: `ContinuousImprovementInitiative`
    (v1.5) already tracks named initiatives; Apollo adds methodology/
    cost-savings/executive-visibility as additive columns, not a new
    table.
  * **Executive Quality Dashboard**: `quality_command_center_service.
    quality_command_center_summary` (v2.9) and Vanguard's
    `vanguard_governance_service.governance_dashboard` (v4.6) already
    compute the large majority of the named tiles. Apollo composes both
    rather than re-deriving CAPA/root-cause/competency/audit-readiness
    numbers a third time.

## Genuinely new tables in this file

  * `CustomerComplaint` — no complaint-intake model existed anywhere;
    this is the real gap needed as a sixth CAPA auto-trigger source.
  * `QualityPolicy` — no clinical/quality policy versioning system
    existed anywhere (`RetentionPolicy`/`GovernanceSlaPolicy` are
    unrelated infrastructure policies). Follows the same
    `supersedes_id` + `status` self-FK chain Beacon/Forge established.
  * `QualityTwinSnapshot` — no department-level quality composite
    existed; `digital_twin_engine.py` is facility/instrument-scoped
    workflow telemetry, a different thing entirely. This is a pure
    composition snapshot (trend history), not a new telemetry source.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Customer complaints (CAPA Engine trigger source, Section 2) ─────────────
COMPLAINT_SEVERITY_LOW = "low"
COMPLAINT_SEVERITY_MEDIUM = "medium"
COMPLAINT_SEVERITY_HIGH = "high"
COMPLAINT_SEVERITIES = [COMPLAINT_SEVERITY_LOW, COMPLAINT_SEVERITY_MEDIUM, COMPLAINT_SEVERITY_HIGH]

COMPLAINT_OPEN = "open"
COMPLAINT_LINKED_TO_CAPA = "linked_to_capa"
COMPLAINT_CLOSED = "closed"
COMPLAINT_STATUSES = [COMPLAINT_OPEN, COMPLAINT_LINKED_TO_CAPA, COMPLAINT_CLOSED]

# ── Quality Policy lifecycle (Section 6) ─────────────────────────────────────
POLICY_DRAFT = "draft"
POLICY_PUBLISHED = "published"
POLICY_SUPERSEDED = "superseded"
POLICY_STATUSES = [POLICY_DRAFT, POLICY_PUBLISHED, POLICY_SUPERSEDED]

# ── Root Cause Intelligence methodologies (Section 3) ────────────────────────
RCA_FIVE_WHYS = "five_whys"
RCA_FISHBONE = "fishbone"
RCA_PARETO = "pareto"
RCA_TREND_ANALYSIS = "trend_analysis"
RCA_METHODOLOGIES = [RCA_FIVE_WHYS, RCA_FISHBONE, RCA_PARETO, RCA_TREND_ANALYSIS]

FISHBONE_CATEGORIES = ["man", "machine", "method", "material", "measurement", "environment"]

DISCLAIMER = (
    "LumenAI Apollo composes real, already-computed quality/compliance/competency intelligence "
    "from across the platform into one Clinical Quality Management System — it does not finalize "
    "a root cause, a CAPA closure, an audit finding, or a policy change without explicit human "
    "review and approval. Nothing here is a substitute for supervisor, quality, or regulatory "
    "judgment; every output is decision support only."
)


class CustomerComplaint(Base):
    """A logged customer/clinical complaint (Section 2 CAPA trigger
    source) — no existing intake model covered this before Apollo."""

    __tablename__ = "apollo_customer_complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    source: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default=COMPLAINT_SEVERITY_MEDIUM, nullable=False, index=True)
    instrument_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=COMPLAINT_OPEN, nullable=False, index=True)
    linked_capa_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    reported_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class QualityPolicy(Base):
    """A versioned clinical/quality policy (Section 6) — genuinely new;
    follows the same `supersedes_id`/`status` self-FK chain Beacon's
    `StandardsPublication` and Forge's `WorkflowDefinition` already
    established."""

    __tablename__ = "apollo_quality_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=POLICY_DRAFT, nullable=False, index=True)
    supersedes_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)

    references_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    linked_standards_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    affected_workflows_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    affected_competencies_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    affected_ai_rules_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    published_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QualityTwinSnapshot(Base):
    """A department-level Quality Digital Twin snapshot (Section 9) —
    a pure composition over Compliance/Competency/Audit Readiness/Policy
    Maturity/CAPA Health/Education/Knowledge/Continuous Improvement.
    Distinct from `digital_twin_engine.py`'s facility/instrument-scoped
    workflow telemetry twin — this tracks governance health, not
    instrument flow."""

    __tablename__ = "apollo_quality_twin_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(255), default="unspecified", nullable=False, index=True)

    compliance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    competency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    audit_readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    policy_maturity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    capa_health_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    education_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    knowledge_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    continuous_improvement_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    factors_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)
