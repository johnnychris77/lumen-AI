"""LumenAI AI Specialist — Project Sage: SPD Education, Competency &
Workforce Intelligence.

## Naming disambiguation (read this first)

Sage composes existing, real workforce/education signal rather than
inventing a parallel competency store:

  * **Competency events (Section 2, 9)** — `CompetencyEvent`
    (`app/models/competency_event.py`) already logs
    finding_reviewed/supervisor_correction/repeated_error/
    education_completed/annual_competency/procedure_validation/
    simulation_passed/simulation_failed/knowledge_contribution per
    technician. Sage reads this log (via `competency_service.py`) rather
    than re-deriving a second competency ledger.
  * **Supervisor ground truth (Sections 3, 9)** — `SupervisorReview`
    (`app/models/supervisor_review.py`) already carries `agreement`,
    `finding_correct`, `zone_correct`, `instrument_family_correct`,
    `ground_truth` -- the real evidence Sage's gap-detection reads.
  * **Coverage / AI confidence (Section 9)** — `Inspection.coverage_pct`
    and `Inspection.ai_confidence` are real, already-persisted per-
    inspection fields Sage's before/after effectiveness comparison reads
    directly.
  * **Educational content (Sections 1, 6)** — `clinical_mentor.py`'s
    `FINDING_EDUCATION`/`STANDARDS_GUIDANCE` and `education_library.py`'s
    articles are the platform's one approved-content source; Sage's
    microlearning generator composes them (plus `InstrumentKnowledge` for
    anatomy) rather than authoring new unsupported clinical guidance.
  * **Institutional knowledge (Section 15)** — Athena's own composition
    services (`athena_memory_service.py`, `KnowledgeArticle`/
    `ClinicalCase` in `app/models/knowledge.py`, `WorkflowDefinition`
    playbooks in `workflow_forge.py`) are called through, never re-
    queried from their underlying tables directly.
  * **Competency/CAPA/audit records (Section 15)** — Apollo's
    `QualityTwinSnapshot` (`competency_score`/`education_score`) and CAPA/
    RCA services are read for evidence; Sage never duplicates them.
  * **Image library (Section 8)** — `RetainedImage`/`ImageLabel`
    (`app/models/retained_image.py`) is the real, already-governed
    (EXIF-stripped, consent-gated, gold-labeled) image store. Rather than
    duplicate image bytes or ML-training label lifecycle, `SageEducationImageEntry`
    (below) is a thin curation layer that references an existing
    `RetainedImage`/`ImageLabel` pair by ID and adds only the
    education-specific fields those tables don't carry (anatomy zone,
    dataset version, usage rights, PHI review status for education use).
  * **Aegis / Vulcan (Sections 13, 14)** — `vulcan_aegis_integration_service.
    compute_process_variation_signal` and `vulcan_reliability_agent_service.
    run_reliability_assessment` are called directly; their conclusions are
    referenced by ID/JSON snapshot in `SageKnowledgeGap.evidence_json`,
    never copied into a duplicate store, and never overwritten by Sage's
    own recommendation.

## What is genuinely new in this file

Seven tables: `SageKnowledgeGap`, `SageLearningPlan`,
`SageMicrolearningModule`, `SageAssessment`, `SageEducationImageEntry`,
`SageEffectivenessAssessment`, `SageFeedback`. Nothing else in this
codebase tracks adaptive learning plans, microlearning modules,
configurable competency assessments, or education-specific effectiveness
comparisons.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2: Competency Taxonomy ───────────────────────────────────────────
COMPETENCY_MANUFACTURER_RECOGNITION = "manufacturer_recognition"
COMPETENCY_INSTRUMENT_FAMILY_RECOGNITION = "instrument_family_recognition"
COMPETENCY_MODEL_RECOGNITION = "model_recognition"
COMPETENCY_INSTRUMENT_DIFFERENTIATION = "instrument_differentiation"
COMPETENCY_RIGID_VS_FLEXIBLE_SCOPE = "rigid_scope_vs_flexible_endoscope"
COMPETENCY_POWERED_VS_MANUAL = "powered_vs_manual_instrument"

COMPETENCY_SERRATIONS = "serrations"
COMPETENCY_GROOVES = "grooves"
COMPETENCY_BOX_LOCKS = "box_locks"
COMPETENCY_HINGES = "hinges"
COMPETENCY_RATCHETS = "ratchets"
COMPETENCY_DRILL_BIT_FLUTES = "drill_bit_flutes"
COMPETENCY_THREADED_REGIONS = "threaded_regions"
COMPETENCY_LUMENS = "lumens"
COMPETENCY_CANNULATED_CHANNELS = "cannulated_channels"
COMPETENCY_O_RING_AREAS = "o_ring_areas"
COMPETENCY_SCOPE_PORTS = "scope_ports"
COMPETENCY_INSULATION_EDGES = "insulation_edges"
COMPETENCY_HANDLE_SEAMS = "handle_seams"

COMPETENCY_VISUAL_INSPECTION = "visual_inspection"
COMPETENCY_MAGNIFICATION = "magnification"
COMPETENCY_BORESCOPE_INSPECTION = "borescope_inspection"
COMPETENCY_ARTICULATION_ACTUATION = "articulation_and_actuation"
COMPETENCY_IMAGE_CAPTURE = "image_capture"
COMPETENCY_LIGHTING = "lighting"
COMPETENCY_FOCUS = "focus"
COMPETENCY_ANGLE_SELECTION = "angle_selection"
COMPETENCY_INSPECTION_COVERAGE = "inspection_coverage"

COMPETENCY_BLOOD = "blood"
COMPETENCY_BONE = "bone"
COMPETENCY_TISSUE = "tissue"
COMPETENCY_ORGANIC_RESIDUE = "organic_residue"
COMPETENCY_DEBRIS = "debris"

COMPETENCY_RUST = "rust"
COMPETENCY_CORROSION = "corrosion"
COMPETENCY_DISCOLORATION = "discoloration"
COMPETENCY_PITTING = "pitting"
COMPETENCY_CRACK = "crack"
COMPETENCY_WEAR = "wear"
COMPETENCY_MISSING_COMPONENTS = "missing_components"
COMPETENCY_INSULATION_DAMAGE = "insulation_damage"

COMPETENCY_RECLEAN = "reclean"
COMPETENCY_REPEAT_INSPECTION = "repeat_inspection"
COMPETENCY_SUPERVISOR_REVIEW_DECISION = "supervisor_review_decision"
COMPETENCY_REPAIR_EVALUATION_DECISION = "repair_evaluation_decision"
COMPETENCY_MANUFACTURER_EVALUATION_DECISION = "manufacturer_evaluation_decision"
COMPETENCY_REMOVE_FROM_SERVICE_DECISION = "remove_from_service_decision"

COMPETENCY_INSPECTION_EVIDENCE_DOC = "inspection_evidence_documentation"
COMPETENCY_SUPERVISOR_NOTES_DOC = "supervisor_notes_documentation"
COMPETENCY_BASELINE_SELECTION_DOC = "baseline_selection_documentation"
COMPETENCY_ANATOMY_ZONE_LABELING_DOC = "anatomy_zone_labeling_documentation"
COMPETENCY_FINAL_DISPOSITION_DOC = "final_disposition_documentation"

COMPETENCY_DOMAIN_INSTRUMENT_ID = "instrument_identification"
COMPETENCY_DOMAIN_ANATOMY = "anatomy_recognition"
COMPETENCY_DOMAIN_TECHNIQUE = "inspection_technique"
COMPETENCY_DOMAIN_CONTAMINATION = "contamination_recognition"
COMPETENCY_DOMAIN_CONDITION = "condition_recognition"
COMPETENCY_DOMAIN_CLINICAL_DECISION = "clinical_decision_support"
COMPETENCY_DOMAIN_DOCUMENTATION = "documentation"

COMPETENCY_TAXONOMY: dict[str, list[str]] = {
    COMPETENCY_DOMAIN_INSTRUMENT_ID: [
        COMPETENCY_MANUFACTURER_RECOGNITION, COMPETENCY_INSTRUMENT_FAMILY_RECOGNITION,
        COMPETENCY_MODEL_RECOGNITION, COMPETENCY_INSTRUMENT_DIFFERENTIATION,
        COMPETENCY_RIGID_VS_FLEXIBLE_SCOPE, COMPETENCY_POWERED_VS_MANUAL,
    ],
    COMPETENCY_DOMAIN_ANATOMY: [
        COMPETENCY_SERRATIONS, COMPETENCY_GROOVES, COMPETENCY_BOX_LOCKS, COMPETENCY_HINGES,
        COMPETENCY_RATCHETS, COMPETENCY_DRILL_BIT_FLUTES, COMPETENCY_THREADED_REGIONS,
        COMPETENCY_LUMENS, COMPETENCY_CANNULATED_CHANNELS, COMPETENCY_O_RING_AREAS,
        COMPETENCY_SCOPE_PORTS, COMPETENCY_INSULATION_EDGES, COMPETENCY_HANDLE_SEAMS,
    ],
    COMPETENCY_DOMAIN_TECHNIQUE: [
        COMPETENCY_VISUAL_INSPECTION, COMPETENCY_MAGNIFICATION, COMPETENCY_BORESCOPE_INSPECTION,
        COMPETENCY_ARTICULATION_ACTUATION, COMPETENCY_IMAGE_CAPTURE, COMPETENCY_LIGHTING,
        COMPETENCY_FOCUS, COMPETENCY_ANGLE_SELECTION, COMPETENCY_INSPECTION_COVERAGE,
    ],
    COMPETENCY_DOMAIN_CONTAMINATION: [
        COMPETENCY_BLOOD, COMPETENCY_BONE, COMPETENCY_TISSUE, COMPETENCY_ORGANIC_RESIDUE, COMPETENCY_DEBRIS,
    ],
    COMPETENCY_DOMAIN_CONDITION: [
        COMPETENCY_RUST, COMPETENCY_CORROSION, COMPETENCY_DISCOLORATION, COMPETENCY_PITTING,
        COMPETENCY_CRACK, COMPETENCY_WEAR, COMPETENCY_MISSING_COMPONENTS, COMPETENCY_INSULATION_DAMAGE,
    ],
    COMPETENCY_DOMAIN_CLINICAL_DECISION: [
        COMPETENCY_RECLEAN, COMPETENCY_REPEAT_INSPECTION, COMPETENCY_SUPERVISOR_REVIEW_DECISION,
        COMPETENCY_REPAIR_EVALUATION_DECISION, COMPETENCY_MANUFACTURER_EVALUATION_DECISION,
        COMPETENCY_REMOVE_FROM_SERVICE_DECISION,
    ],
    COMPETENCY_DOMAIN_DOCUMENTATION: [
        COMPETENCY_INSPECTION_EVIDENCE_DOC, COMPETENCY_SUPERVISOR_NOTES_DOC,
        COMPETENCY_BASELINE_SELECTION_DOC, COMPETENCY_ANATOMY_ZONE_LABELING_DOC,
        COMPETENCY_FINAL_DISPOSITION_DOC,
    ],
}

# ── Section 3/4: Gap scope + Section 18 aggregation scopes ───────────────────
SCOPE_INDIVIDUAL = "individual"
SCOPE_SHIFT = "shift"
SCOPE_DEPARTMENT = "department"
SCOPE_FACILITY = "facility"
SCOPE_INSTRUMENT_FAMILY = "instrument_family"
SCOPE_ANATOMY_ZONE = "anatomy_zone"
SCOPE_FINDING_CATEGORY = "finding_category"
SCOPE_SERVICE_LINE = "service_line"
GAP_SCOPES = [
    SCOPE_INDIVIDUAL, SCOPE_SHIFT, SCOPE_DEPARTMENT, SCOPE_FACILITY, SCOPE_INSTRUMENT_FAMILY,
    SCOPE_ANATOMY_ZONE, SCOPE_FINDING_CATEGORY, SCOPE_SERVICE_LINE,
]

# ── Section 5: Learning plan completion status ───────────────────────────────
PLAN_STATUS_ASSIGNED = "assigned"
PLAN_STATUS_IN_PROGRESS = "in_progress"
PLAN_STATUS_COMPLETED = "completed"
PLAN_STATUS_OVERDUE = "overdue"
PLAN_STATUS_CANCELLED = "cancelled"
PLAN_STATUSES = [
    PLAN_STATUS_ASSIGNED, PLAN_STATUS_IN_PROGRESS, PLAN_STATUS_COMPLETED,
    PLAN_STATUS_OVERDUE, PLAN_STATUS_CANCELLED,
]

# ── Section 7: Assessment formats ────────────────────────────────────────────
ASSESSMENT_KNOWLEDGE_QUESTIONS = "knowledge_questions"
ASSESSMENT_IMAGE_CLASSIFICATION = "image_classification"
ASSESSMENT_ANATOMY_ZONE_IDENTIFICATION = "anatomy_zone_identification"
ASSESSMENT_CASE_REVIEW = "case_review"
ASSESSMENT_WORKFLOW_SIMULATION = "workflow_simulation"
ASSESSMENT_SUPERVISED_RETURN_DEMONSTRATION = "supervised_return_demonstration"
ASSESSMENT_SUPERVISOR_OBSERVATION = "supervisor_observation"
ASSESSMENT_PRACTICAL_CHECKLIST = "practical_checklist"
ASSESSMENT_FORMATS = [
    ASSESSMENT_KNOWLEDGE_QUESTIONS, ASSESSMENT_IMAGE_CLASSIFICATION,
    ASSESSMENT_ANATOMY_ZONE_IDENTIFICATION, ASSESSMENT_CASE_REVIEW, ASSESSMENT_WORKFLOW_SIMULATION,
    ASSESSMENT_SUPERVISED_RETURN_DEMONSTRATION, ASSESSMENT_SUPERVISOR_OBSERVATION,
    ASSESSMENT_PRACTICAL_CHECKLIST,
]

# ── Section 9: Learning effectiveness classification ────────────────────────
EFFECTIVENESS_IMPROVED = "improved"
EFFECTIVENESS_PARTIALLY_IMPROVED = "partially_improved"
EFFECTIVENESS_UNCHANGED = "unchanged"
EFFECTIVENESS_DECLINED = "declined"
EFFECTIVENESS_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
EFFECTIVENESS_CLASSIFICATIONS = [
    EFFECTIVENESS_IMPROVED, EFFECTIVENESS_PARTIALLY_IMPROVED, EFFECTIVENESS_UNCHANGED,
    EFFECTIVENESS_DECLINED, EFFECTIVENESS_INSUFFICIENT_EVIDENCE,
]

SAGE_AGENT_VERSION = "1.0.0"

DISCLAIMER = (
    "Sage supports technicians, supervisors, educators, and SPD leaders with evidence-based, "
    "confidence-scored education and competency recommendations. Sage does not discipline "
    "employees, independently determine competency, or replace supervisor and educator judgment. "
    "Language such as 'targeted education may be beneficial' or 'competency verification is "
    "recommended' reflects a possible pattern only -- never a conclusion that an individual is "
    "incompetent. Every recommendation requires human (educator/supervisor) approval before "
    "assignment or any workforce action."
)


class SageKnowledgeGap(Base):
    """A possible competency gap detected from validated patterns (Sections
    1, 3). Never a conclusion of incompetence -- `narrative` always uses
    non-punitive language, and `human_review_required` is always True."""

    __tablename__ = "sage_knowledge_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    competency_domain: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    scope_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    finding_category: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)

    occurrence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommended_education: Mapped[str] = mapped_column(Text, default="", nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=SAGE_AGENT_VERSION, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class SageLearningPlan(Base):
    """An adaptive learning plan (Section 5) -- requires approval by an
    authorized educator, supervisor, or manager before assignment. Vulcan/
    Sage terminology mirrors `recommended_disposition`/`final_disposition`:
    Sage's own recommendation never becomes an assigned plan without a
    human `approved_by`."""

    __tablename__ = "sage_learning_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    knowledge_gap_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    learner_or_group: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(30), default=SCOPE_INDIVIDUAL, nullable=False, index=True)

    identified_need: Mapped[str] = mapped_column(Text, default="", nullable=False)
    supporting_evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    learning_objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    finding_category: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)

    education_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    microlearning_module_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    practice_activity: Mapped[str] = mapped_column(Text, default="", nullable=False)
    return_demonstration_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    return_demonstration_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    evaluator: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_status: Mapped[str] = mapped_column(String(20), default=PLAN_STATUS_ASSIGNED, nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    effectiveness_assessment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=SAGE_AGENT_VERSION, nullable=False)


class SageMicrolearningModule(Base):
    """A short educational module (Section 6), composed only from approved
    Knowledge Graph / IFU / policy / institutional sources -- never
    unsupported clinical guidance."""

    __tablename__ = "sage_microlearning_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    learning_objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, default="", nullable=False)
    anatomy_overview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    common_findings_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    inspection_steps_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    corrective_actions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    knowledge_check_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    source_refs_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    competency_domain: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)

    approval_status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)


class SageAssessment(Base):
    """A configurable competency assessment (Section 7). Results remain
    advisory until validated by an authorized evaluator."""

    __tablename__ = "sage_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    learning_plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    assessment_format: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_learner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    competency_domain: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)

    content_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    result_status: Mapped[str] = mapped_column(String(20), default="advisory", nullable=False, index=True)

    validated_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SageEducationImageEntry(Base):
    """Education-curation metadata for one existing `RetainedImage`/
    `ImageLabel` pair (Section 8) -- references by ID, never duplicates
    the image bytes or the ML-training label lifecycle those tables own."""

    __tablename__ = "sage_education_image_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    retained_image_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    image_label_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    finding_category: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(30), default="", nullable=False)

    supervisor_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usage_rights: Mapped[str] = mapped_column(String(100), default="internal_education_use", nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    phi_review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)


class SageEffectivenessAssessment(Base):
    """Learning Effectiveness Engine result (Section 9) -- compares real
    before/after metrics (coverage, supervisor correction rate, image
    quality, finding/anatomy accuracy, workflow compliance). Never claims
    causation without adequate evidence."""

    __tablename__ = "sage_effectiveness_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    learning_plan_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    learner_or_group: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    before_metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    after_metrics_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    effectiveness: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SageFeedback(Base):
    """Educator/supervisor action on a Sage recommendation or learning plan
    (Section 12) -- approve/reject/edit/assign/observe/validate/close/
    review/comment. `override_reason` is required when overriding a
    high-confidence recommendation (enforced at the service layer)."""

    __tablename__ = "sage_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    learning_plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    knowledge_gap_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    override_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    submitted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    submitted_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
