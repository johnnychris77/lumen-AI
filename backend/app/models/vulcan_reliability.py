"""LumenAI AI Specialist — Project Vulcan: Instrument Reliability, Failure
Analysis & Repair Intelligence.

## Naming disambiguation (read this first)

Vulcan composes existing, real data rather than inventing a parallel
instrument-history store:

  * **Finding history (Sections 3, 4)** — `InspectionFinding`
    (`app/models/inspection_finding.py`, v1.5) already logs one row per
    actionable finding (`finding_type`, `zone`, `severity_index`,
    `created_at`) per real inspection -- this *is* the progression
    history Vulcan analyzes. Vulcan never re-derives or duplicates it.
  * **Repair history (Section 5)** — `RepairRequest`
    (`app/models/or_connect.py`) already tracks `inspection_id`,
    `vendor_name`, `repair_type`, `status`, `expected_return_date`/
    `actual_return_date`, and a coarse `failure_category` (7 values:
    corrosion/mechanical_wear/electrical_fault/insulation_defect/
    misuse_damage/manufacturing_defect/other). Vulcan's granular
    taxonomy (Section 2, below) maps onto that coarse category where
    relevant for repair-effectiveness correlation -- never a second
    repair-request table.
  * **Instrument identity/anatomy (Sections 1, 4)** — `instrument_knowledge.py`
    (manufacturer/model/instrument_family/anatomy_zones/high_risk_zones/
    known_failure_modes) and `Inspection.instrument_udi`/
    `instrument_barcode` (the real cross-inspection identity key) are
    reused directly.
  * **Digital Twin / baseline versions (Section 15 audit)** —
    `digital_twin_engine`'s twin state and `BaselineLibraryEntry.baseline_version`
    are referenced by version string only, never copied.
  * **Supervisor feedback pattern** — `SupervisorReview`
    (`app/models/supervisor_review.py`) already captures AI-agreement
    feedback for the inspection pipeline; `VulcanFeedback` (below) is
    deliberately a separate, Vulcan-specific table because Section 13
    needs fields `SupervisorReview` was never built for (repair-vendor
    response, manufacturer response, progression/repair-effectiveness/
    probable-cause correctness) -- not a duplicate of the same concept.
  * **Aegis (Section 12)** — no "Aegis" agent or process-variation
    engine exists anywhere in this codebase yet. Rather than fabricate
    one, `vulcan_aegis_integration_service.py` builds a real, honestly
    minimal process-variation signal from actual `Inspection.technician`/
    `vendor_name` concentration patterns -- a genuine analysis, not a
    placeholder. `VulcanReliabilityAssessment.aegis_conclusion_json` is
    populated only when that signal is composed in, and is never merged
    into or overwritten by Vulcan's own conclusion fields -- "no agent
    may overwrite the other's conclusion."

## What is genuinely new in this file

Three tables: `VulcanReliabilityAssessment`, `VulcanRepairEffectivenessAssessment`,
`VulcanFeedback`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2: Instrument Failure Taxonomy ───────────────────────────────────
# Cleaning-related
FAIL_RETAINED_BLOOD = "retained_blood"
FAIL_RETAINED_BONE = "retained_bone"
FAIL_TISSUE = "tissue"
FAIL_ORGANIC_RESIDUE = "organic_residue"
FAIL_DEBRIS = "debris"
FAIL_OBSTRUCTION = "obstruction"
# Condition-related
FAIL_RUST = "rust"
FAIL_CORROSION = "corrosion"
FAIL_PITTING = "pitting"
FAIL_DISCOLORATION = "discoloration"
FAIL_SURFACE_DEGRADATION = "surface_degradation"
FAIL_STAINING = "staining"
# Mechanical
FAIL_CRACK = "crack"
FAIL_MISALIGNMENT = "misalignment"
FAIL_LOOSE_JOINT = "loose_joint"
FAIL_DAMAGED_HINGE = "damaged_hinge"
FAIL_DAMAGED_RATCHET = "damaged_ratchet"
FAIL_DAMAGED_SERRATION = "damaged_serration"
FAIL_WORN_CUTTING_EDGE = "worn_cutting_edge"
FAIL_BENT_COMPONENT = "bent_component"
FAIL_MISSING_COMPONENT = "missing_component"
# Scope-specific
FAIL_DAMAGED_O_RING = "damaged_o_ring"
FAIL_DAMAGED_SEAL = "damaged_seal"
FAIL_LENS_DAMAGE = "lens_damage"
FAIL_LIGHT_POST_DAMAGE = "light_post_damage"
FAIL_SHEATH_DAMAGE = "sheath_damage"
FAIL_PORT_DAMAGE = "port_damage"
FAIL_CHANNEL_DAMAGE = "channel_damage"
# Powered/orthopedic
FAIL_DAMAGED_DRILL_FLUTE = "damaged_drill_flute"
FAIL_DAMAGED_THREAD = "damaged_thread"
FAIL_WORN_CUTTING_TIP = "worn_cutting_tip"
FAIL_DAMAGED_HUB = "damaged_hub"
FAIL_METAL_DEFORMATION = "metal_deformation"
# Insulation-related
FAIL_INSULATION_BREACH = "insulation_breach"
FAIL_PEELING_INSULATION = "peeling_insulation"
FAIL_EXPOSED_CONDUCTOR = "exposed_conductor"
FAIL_SURFACE_NICK = "surface_nick"
# Unknown
FAIL_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
FAIL_IMAGE_QUALITY_LIMITATION = "image_quality_limitation"
FAIL_ANATOMY_NOT_RECOGNIZED = "anatomy_not_recognized"
FAIL_MANUFACTURER_EVALUATION_REQUIRED = "manufacturer_evaluation_required"

TAXONOMY_GROUP_CLEANING = "cleaning_related"
TAXONOMY_GROUP_CONDITION = "condition_related"
TAXONOMY_GROUP_MECHANICAL = "mechanical"
TAXONOMY_GROUP_SCOPE_SPECIFIC = "scope_specific"
TAXONOMY_GROUP_POWERED_ORTHOPEDIC = "powered_orthopedic"
TAXONOMY_GROUP_INSULATION = "insulation_related"
TAXONOMY_GROUP_UNKNOWN = "unknown"

FAILURE_TAXONOMY: dict[str, list[str]] = {
    TAXONOMY_GROUP_CLEANING: [
        FAIL_RETAINED_BLOOD, FAIL_RETAINED_BONE, FAIL_TISSUE, FAIL_ORGANIC_RESIDUE, FAIL_DEBRIS, FAIL_OBSTRUCTION,
    ],
    TAXONOMY_GROUP_CONDITION: [
        FAIL_RUST, FAIL_CORROSION, FAIL_PITTING, FAIL_DISCOLORATION, FAIL_SURFACE_DEGRADATION, FAIL_STAINING,
    ],
    TAXONOMY_GROUP_MECHANICAL: [
        FAIL_CRACK, FAIL_MISALIGNMENT, FAIL_LOOSE_JOINT, FAIL_DAMAGED_HINGE, FAIL_DAMAGED_RATCHET,
        FAIL_DAMAGED_SERRATION, FAIL_WORN_CUTTING_EDGE, FAIL_BENT_COMPONENT, FAIL_MISSING_COMPONENT,
    ],
    TAXONOMY_GROUP_SCOPE_SPECIFIC: [
        FAIL_DAMAGED_O_RING, FAIL_DAMAGED_SEAL, FAIL_LENS_DAMAGE, FAIL_LIGHT_POST_DAMAGE, FAIL_SHEATH_DAMAGE,
        FAIL_PORT_DAMAGE, FAIL_CHANNEL_DAMAGE,
    ],
    TAXONOMY_GROUP_POWERED_ORTHOPEDIC: [
        FAIL_DAMAGED_DRILL_FLUTE, FAIL_DAMAGED_THREAD, FAIL_WORN_CUTTING_TIP, FAIL_DAMAGED_HUB, FAIL_METAL_DEFORMATION,
    ],
    TAXONOMY_GROUP_INSULATION: [
        FAIL_INSULATION_BREACH, FAIL_PEELING_INSULATION, FAIL_EXPOSED_CONDUCTOR, FAIL_SURFACE_NICK,
    ],
    TAXONOMY_GROUP_UNKNOWN: [
        FAIL_INSUFFICIENT_EVIDENCE, FAIL_IMAGE_QUALITY_LIMITATION, FAIL_ANATOMY_NOT_RECOGNIZED,
        FAIL_MANUFACTURER_EVALUATION_REQUIRED,
    ],
}

# ── Section 3: Failure Progression Model ─────────────────────────────────────
PROGRESSION_STABLE = "stable"
PROGRESSION_IMPROVING = "improving"
PROGRESSION_SLOWLY_WORSENING = "slowly_worsening"
PROGRESSION_RAPIDLY_WORSENING = "rapidly_worsening"
PROGRESSION_INTERMITTENT = "intermittent"
PROGRESSION_UNRESOLVED = "unresolved"
PROGRESSION_INSUFFICIENT_HISTORY = "insufficient_history"
PROGRESSION_STATES = [
    PROGRESSION_STABLE, PROGRESSION_IMPROVING, PROGRESSION_SLOWLY_WORSENING, PROGRESSION_RAPIDLY_WORSENING,
    PROGRESSION_INTERMITTENT, PROGRESSION_UNRESOLVED, PROGRESSION_INSUFFICIENT_HISTORY,
]

# ── Section 5: Repair Effectiveness Intelligence ─────────────────────────────
REPAIR_OUTCOME_EFFECTIVE = "effective"
REPAIR_OUTCOME_PARTIALLY_EFFECTIVE = "partially_effective"
REPAIR_OUTCOME_FAILURE_RECURRED = "failure_recurred"
REPAIR_OUTCOME_NEW_DEFECT_DETECTED = "new_defect_detected"
REPAIR_OUTCOME_UNABLE_TO_DETERMINE = "unable_to_determine"
REPAIR_OUTCOMES = [
    REPAIR_OUTCOME_EFFECTIVE, REPAIR_OUTCOME_PARTIALLY_EFFECTIVE, REPAIR_OUTCOME_FAILURE_RECURRED,
    REPAIR_OUTCOME_NEW_DEFECT_DETECTED, REPAIR_OUTCOME_UNABLE_TO_DETERMINE,
]

# ── Section 6: Probable Cause Classification ─────────────────────────────────
CAUSE_INCOMPLETE_CLEANING = "incomplete_cleaning"
CAUSE_IMPROPER_BRUSHING = "improper_brushing"
CAUSE_IMPROPER_FLUSHING = "improper_flushing"
CAUSE_CHEMICAL_EXPOSURE = "chemical_exposure"
CAUSE_MOISTURE_EXPOSURE = "moisture_exposure"
CAUSE_INADEQUATE_DRYING = "inadequate_drying"
CAUSE_NORMAL_WEAR = "normal_wear"
CAUSE_HEAVY_USE = "heavy_use"
CAUSE_HANDLING_DAMAGE = "handling_damage"
CAUSE_ASSEMBLY_DAMAGE = "assembly_damage"
CAUSE_REPAIR_RECURRENCE = "repair_recurrence"
CAUSE_MATERIAL_DEGRADATION = "material_degradation"
CAUSE_SUSPECTED_MANUFACTURING_DESIGN_ISSUE = "suspected_manufacturing_design_issue"
CAUSE_UNKNOWN = "unknown"
PROBABLE_CAUSES = [
    CAUSE_INCOMPLETE_CLEANING, CAUSE_IMPROPER_BRUSHING, CAUSE_IMPROPER_FLUSHING, CAUSE_CHEMICAL_EXPOSURE,
    CAUSE_MOISTURE_EXPOSURE, CAUSE_INADEQUATE_DRYING, CAUSE_NORMAL_WEAR, CAUSE_HEAVY_USE, CAUSE_HANDLING_DAMAGE,
    CAUSE_ASSEMBLY_DAMAGE, CAUSE_REPAIR_RECURRENCE, CAUSE_MATERIAL_DEGRADATION,
    CAUSE_SUSPECTED_MANUFACTURING_DESIGN_ISSUE, CAUSE_UNKNOWN,
]

# ── Section 7: Reliability Score bands ────────────────────────────────────────
RELIABILITY_RELIABLE = "reliable"
RELIABILITY_MONITOR = "monitor"
RELIABILITY_ELEVATED_CONCERN = "elevated_concern"
RELIABILITY_REPAIR_MANUFACTURER_REVIEW = "repair_manufacturer_review"
RELIABILITY_REMOVE_FROM_SERVICE_CANDIDATE = "remove_from_service_candidate"


def reliability_category(score: float) -> str:
    if score >= 90:
        return RELIABILITY_RELIABLE
    if score >= 75:
        return RELIABILITY_MONITOR
    if score >= 50:
        return RELIABILITY_ELEVATED_CONCERN
    if score >= 25:
        return RELIABILITY_REPAIR_MANUFACTURER_REVIEW
    return RELIABILITY_REMOVE_FROM_SERVICE_CANDIDATE


# ── Section 8: Recommended Dispositions ───────────────────────────────────────
DISPOSITION_CONTINUE_ROUTINE_INSPECTION = "continue_routine_inspection"
DISPOSITION_INCREASE_INSPECTION_FREQUENCY = "increase_inspection_frequency"
DISPOSITION_RECLEAN_AND_REINSPECT = "reclean_and_reinspect"
DISPOSITION_SUPERVISOR_REVIEW = "supervisor_review"
DISPOSITION_REPAIR_EVALUATION = "repair_evaluation"
DISPOSITION_CLINICAL_ENGINEERING_REVIEW = "clinical_engineering_review"
DISPOSITION_MANUFACTURER_EVALUATION = "manufacturer_evaluation"
DISPOSITION_QUARANTINE_PENDING_REVIEW = "quarantine_pending_review"
DISPOSITION_REMOVE_FROM_SERVICE = "remove_from_service"
DISPOSITION_RETIREMENT_CANDIDATE = "retirement_candidate"
RECOMMENDED_DISPOSITIONS = [
    DISPOSITION_CONTINUE_ROUTINE_INSPECTION, DISPOSITION_INCREASE_INSPECTION_FREQUENCY,
    DISPOSITION_RECLEAN_AND_REINSPECT, DISPOSITION_SUPERVISOR_REVIEW, DISPOSITION_REPAIR_EVALUATION,
    DISPOSITION_CLINICAL_ENGINEERING_REVIEW, DISPOSITION_MANUFACTURER_EVALUATION,
    DISPOSITION_QUARANTINE_PENDING_REVIEW, DISPOSITION_REMOVE_FROM_SERVICE, DISPOSITION_RETIREMENT_CANDIDATE,
]

VULCAN_AGENT_VERSION = "1.0.0"

DISCLAIMER = (
    "Vulcan supports pre-sterilization inspection and asset-quality decisions. It does not "
    "certify instrument safety independently. Every conclusion is evidence-based, "
    "confidence-scored, and requires human review; supervisor, clinical engineering, repair "
    "vendor, and manufacturer review remain available where appropriate. Vulcan describes "
    "potential associations and probable contributors only, never a definitive root cause "
    "unless confirmed through approved investigation."
)


class VulcanReliabilityAssessment(Base):
    """One Instrument Reliability assessment (Sections 1, 3, 4, 6, 7, 8,
    11, 12, 15) -- the durable, auditable record of what Vulcan
    concluded, from what evidence, with what confidence, and what
    happened after human review. `final_disposition` is nullable and can
    only be set via a supervisor-gated action (`vulcan_feedback_service`)
    -- Vulcan's own compute step never sets it, satisfying "Vulcan
    cannot independently finalize irreversible disposition."
    """

    __tablename__ = "vulcan_reliability_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    instrument_identity: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    manufacturer_name: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)

    failure_category: Mapped[str] = mapped_column(String(50), default="", nullable=False, index=True)
    progression: Mapped[str] = mapped_column(String(30), default=PROGRESSION_INSUFFICIENT_HISTORY, nullable=False, index=True)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    reliability_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reliability_category: Mapped[str] = mapped_column(String(40), default=RELIABILITY_ELEVATED_CONCERN, nullable=False, index=True)
    score_breakdown_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    probable_causes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    recommended_disposition: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reasoning_narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)

    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    rules_applied_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    digital_twin_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    baseline_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    anatomy_profile_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=VULCAN_AGENT_VERSION, nullable=False)

    aegis_conclusion_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    combined_conclusion: Mapped[str] = mapped_column(Text, default="", nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    final_disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    finalized_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class VulcanRepairEffectivenessAssessment(Base):
    """One repair-effectiveness classification (Section 5), linked to a
    real `RepairRequest` row -- never a duplicate of its fields."""

    __tablename__ = "vulcan_repair_effectiveness_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    repair_request_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    instrument_identity: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)

    repair_outcome: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    time_to_recurrence_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class VulcanFeedback(Base):
    """Supervisor / repair-vendor / manufacturer feedback on a Vulcan
    assessment (Section 13) -- stored as a learning signal, distinct
    from `SupervisorReview` (a different pipeline's AI-agreement
    label store)."""

    __tablename__ = "vulcan_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )

    assessment_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    failure_classification_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    anatomy_zone_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    progression_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    repair_effectiveness_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    probable_contributor_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    final_disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    supervisor_rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    repair_vendor_response: Mapped[str] = mapped_column(Text, default="", nullable=False)
    manufacturer_response: Mapped[str] = mapped_column(Text, default="", nullable=False)

    submitted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    submitted_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
