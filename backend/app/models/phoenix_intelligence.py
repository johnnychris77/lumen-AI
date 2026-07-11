"""v4.9 — LumenAI OS: Project Phoenix — Self-Improving Healthcare
Intelligence Platform.

## Naming disambiguation (read this first)

Phoenix is the 18th additive sprint. Before writing any code, every
existing performance/analytics/maturity-adjacent system was read in full:

  * **AI Performance Observatory (Section 3)**: `app/services/ml/
    pilot_validation.py`'s `clinical_metrics`/`confidence_calibration`/
    `zone_performance` and `sentinel_ai_health_service.compute_ai_health`
    already compute precision/recall/F1/FP-FN rates/agreement/drift from
    real `SupervisorReview` rows. Phoenix composes these directly — the
    only genuinely new metrics are **Inference Latency** (nothing
    anywhere measures AI scoring wall-clock time) and **Coverage** as "%
    of inspections that received a real AI confidence score" (distinct
    from `inspection_coverage.py`'s image/zone-capture-completeness
    "coverage", a different concept with the same name).
  * **Knowledge Evolution Center (Section 5)**: `athena_curator_service.
    py` (v4.8) already detects duplicates/outdated guidance/retirement
    candidates/emerging practices/knowledge gaps. Phoenix composes it
    directly, adding only **contradictory guidance** detection — a
    genuine gap (confirmed via grep: no "contradict" logic exists
    anywhere in this codebase).
  * **Competency Intelligence (Section 6)**: `competency_intelligence_
    service.py` (v2.9) already detects coaching/team-education/
    department-retraining opportunities via the shared `CompetencyOpportunity`
    model. Two of that model's five `OPPORTUNITY_TYPES` — `annual_competency`
    and `recurring_learning` — were defined but never produced by any
    detector; Phoenix adds detectors for those plus three new types
    (`simulation`, `mentoring`, `knowledge_sharing`) to the same table.
  * **Workflow Optimization Engine (Section 4)**: `WorkflowExecution`
    (`workflow_forge.py`, v4.1) already records real `execution_time_ms`/
    `decision_path_json`, but no duration/bottleneck/queue-delay/rule-
    complexity analytics exists anywhere over it — genuine gap. Phoenix
    reads these rows directly; it does not duplicate the model, and any
    optimization it recommends is surfaced as a *recommendation*, never
    an automatic `revise_workflow` call.
  * **Platform Maturity Index (Section 10)**: Apollo's
    `apollo_quality_twin_service.compute_quality_twin` (v4.7) is already
    an 8-dimension "Quality Maturity Index." Phoenix's 9-dimension
    Platform Maturity Index takes that `overall_score` as its own
    "Quality" dimension input rather than re-deriving CAPA/competency/
    audit-readiness numbers a third time. "Executive Intelligence"
    composes `vanguard_executive_intelligence_service`/`vanguard_
    governance_service` (v4.6) the same way.
  * **Continuous Validation (Section 9)**: `WorkflowApprovalChain`/
    `WorkflowApprovalInstance` (`workflow_forge.py`, v4.1,
    `forge_approval_service.py`) already implement exactly the ordered
    multi-step approval primitive Phoenix's Review → Clinical Validation
    → Technical Review → Pilot → Measurement → Production pipeline
    needs. Phoenix creates one chain per recommendation with those six
    steps and drives it via the existing `start_instance`/`decide_step`
    — no second approval-chain model. Note: `app/models/pilot.py`/
    `pilot_config.py`/`pilot_error_log.py` are a completely different,
    older "pilot" concept (customer/site sales-pilot tracking) — zero
    collision, but Phoenix avoids the bare word "pilot" as a table/field
    name to prevent confusion.
  * **Innovation Pipeline (Section 8)**: confirmed via grep — no Idea/
    Evidence/ROI/Clinical-Impact/Roadmap model exists anywhere. Genuinely
    new.

## Genuinely new tables in this file

  * `ImprovementRecommendation` — the core recommendation entity
    (Section 2), carrying Evidence/Expected Benefit/Confidence/Impact
    Assessment/Required Approvals, and its Continuous Validation stage.
  * `ValidationOutcome` — per-stage outcomes and lessons learned for a
    recommendation moving through the reused Forge approval chain.
  * `InnovationIdea` — the Innovation Pipeline backlog (Section 8).
  * `PlatformMaturitySnapshot` — the 9-dimension Platform Maturity Index,
    tracked over time (Section 10).
  * `AIInferenceLatencySample` — real, explicitly recorded latency
    measurements (Section 3) — never a fabricated typical value; the
    Observatory reports "insufficient data" when none exist.

Phoenix never modifies production automatically — every recommendation
and idea starts in a draft/proposal state and only advances through an
explicit human decision at each stage.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Improvement Recommendation types (Section 2) ─────────────────────────────
REC_IMPROVE_ANATOMY_MODEL = "improve_anatomy_model"
REC_COLLECT_BASELINE_IMAGES = "collect_baseline_images"
REC_UPDATE_WORKFLOW = "update_workflow"
REC_REVISE_INSPECTION_GUIDANCE = "revise_inspection_guidance"
REC_IMPROVE_KNOWLEDGE_GRAPH = "improve_knowledge_graph"
REC_REVIEW_AI_CONFIDENCE = "review_ai_confidence"
REC_CREATE_COMPETENCY = "create_competency"
REC_UPDATE_SOP = "update_sop"
RECOMMENDATION_TYPES = [
    REC_IMPROVE_ANATOMY_MODEL, REC_COLLECT_BASELINE_IMAGES, REC_UPDATE_WORKFLOW,
    REC_REVISE_INSPECTION_GUIDANCE, REC_IMPROVE_KNOWLEDGE_GRAPH, REC_REVIEW_AI_CONFIDENCE,
    REC_CREATE_COMPETENCY, REC_UPDATE_SOP,
]

# The engine that generated a recommendation.
SOURCE_AI_OBSERVATORY = "ai_observatory"
SOURCE_WORKFLOW_OPTIMIZER = "workflow_optimizer"
SOURCE_KNOWLEDGE_EVOLUTION = "knowledge_evolution"
SOURCE_COMPETENCY_INTELLIGENCE = "competency_intelligence"
RECOMMENDATION_SOURCES = [
    SOURCE_AI_OBSERVATORY, SOURCE_WORKFLOW_OPTIMIZER, SOURCE_KNOWLEDGE_EVOLUTION, SOURCE_COMPETENCY_INTELLIGENCE,
]

# ── Continuous Validation pipeline stages (Section 9) — mirrors the six
# steps driven through the reused Forge WorkflowApprovalChain primitive.
STAGE_REVIEW = "review"
STAGE_CLINICAL_VALIDATION = "clinical_validation"
STAGE_TECHNICAL_REVIEW = "technical_review"
STAGE_PILOT = "pilot"
STAGE_MEASUREMENT = "measurement"
STAGE_PRODUCTION = "production"
VALIDATION_STAGES = [
    STAGE_REVIEW, STAGE_CLINICAL_VALIDATION, STAGE_TECHNICAL_REVIEW, STAGE_PILOT, STAGE_MEASUREMENT, STAGE_PRODUCTION,
]

RECOMMENDATION_STATUSES = ["draft", *VALIDATION_STAGES, "rejected"]

# ── Innovation Pipeline (Section 8) ───────────────────────────────────────────
IMPACT_LOW = "low"
IMPACT_MEDIUM = "medium"
IMPACT_HIGH = "high"
IMPACT_CRITICAL = "critical"
CLINICAL_IMPACT_LEVELS = [IMPACT_LOW, IMPACT_MEDIUM, IMPACT_HIGH, IMPACT_CRITICAL]
TECHNICAL_COMPLEXITY_LEVELS = [IMPACT_LOW, IMPACT_MEDIUM, IMPACT_HIGH]
PRIORITY_LEVELS = [IMPACT_LOW, IMPACT_MEDIUM, IMPACT_HIGH, IMPACT_CRITICAL]

IDEA_DRAFT = "draft"
IDEA_APPROVED = "approved"
IDEA_REJECTED = "rejected"
IDEA_IN_PROGRESS = "in_progress"
IDEA_COMPLETED = "completed"
IDEA_APPROVAL_STATUSES = [IDEA_DRAFT, IDEA_APPROVED, IDEA_REJECTED, IDEA_IN_PROGRESS, IDEA_COMPLETED]

# ── AI Observatory latency sample stages (Section 3) ─────────────────────────
LATENCY_STAGE_DETECTION = "detection"
LATENCY_STAGE_ANATOMY_MODEL = "anatomy_model"
LATENCY_STAGE_FULL_PIPELINE = "full_pipeline"
LATENCY_STAGES = [LATENCY_STAGE_DETECTION, LATENCY_STAGE_ANATOMY_MODEL, LATENCY_STAGE_FULL_PIPELINE]

DISCLAIMER = (
    "LumenAI Phoenix analyzes real platform performance, knowledge quality, AI accuracy, workflow "
    "efficiency, and operational outcomes to surface evidence-based improvement recommendations — it "
    "never modifies production automatically. Every recommendation, innovation idea, and maturity score "
    "is decision support only and requires explicit human governance and approval at every stage."
)


class ImprovementRecommendation(Base):
    """A single explainable improvement recommendation (Section 2),
    carrying Evidence/Expected Benefit/Confidence/Impact Assessment/
    Required Approvals, and its Continuous Validation stage (Section 9).
    Never auto-applied — `status` only ever advances via an explicit
    human decision recorded through the reused Forge approval chain."""

    __tablename__ = "phoenix_improvement_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    recommendation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)

    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    expected_benefit: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    impact_assessment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    required_approvals_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    approval_chain_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approval_instance_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # A reference to whatever real record triggered this recommendation
    # (e.g. a workflow_id, article_id, opportunity_id) — blank when the
    # recommendation is tenant-wide rather than object-specific.
    related_object_type: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    related_object_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class ValidationOutcome(Base):
    """Tracked outcome and lessons learned for one stage of a
    recommendation's journey through Continuous Validation (Section 9)."""

    __tablename__ = "phoenix_validation_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    recommendation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    outcome_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lessons_learned: Mapped[str] = mapped_column(Text, default="", nullable=False)
    measured_impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class InnovationIdea(Base):
    """One Innovation Pipeline backlog entry (Section 8) — Ideas/Evidence/
    Estimated ROI/Clinical Impact/Technical Complexity/Priority/Approval
    Status/Roadmap Assignment."""

    __tablename__ = "phoenix_innovation_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)

    estimated_roi_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    clinical_impact: Mapped[str] = mapped_column(String(20), default=IMPACT_MEDIUM, nullable=False, index=True)
    technical_complexity: Mapped[str] = mapped_column(String(20), default=IMPACT_MEDIUM, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=IMPACT_MEDIUM, nullable=False, index=True)
    approval_status: Mapped[str] = mapped_column(String(20), default=IDEA_DRAFT, nullable=False, index=True)
    roadmap_assignment: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    submitted_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class PlatformMaturitySnapshot(Base):
    """A Platform Maturity Index snapshot (Section 10) across nine named
    dimensions, tracked over time — a pure composition of real,
    already-computed scores from prior sprints, plus Phoenix's own
    Workflow/Analytics/AI-observatory-derived dimensions."""

    __tablename__ = "phoenix_platform_maturity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    inspection_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    knowledge_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    workflow_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    analytics_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    education_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    digital_twins_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    governance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    executive_intelligence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    factors_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class AIInferenceLatencySample(Base):
    """A real, explicitly recorded AI-scoring latency measurement
    (Section 3) — never a fabricated typical value. The Observatory
    reports "insufficient data" when no samples exist for a stage rather
    than inventing a number."""

    __tablename__ = "phoenix_ai_inference_latency_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    stage: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
