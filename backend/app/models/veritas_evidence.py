"""LumenAI AI Specialist — Project Veritas: Baseline Governance, Evidence
Integrity & Clinical Data Quality.

## Naming disambiguation (read this first)

Veritas composes real, already-built baseline/coverage/image/provenance
infrastructure rather than inventing a parallel evidence store:

  * **Baseline resolution (Section 2)** — `baseline_comparison_scoring_
    service.resolve_baseline(db, instrument_type, tenant_id)` already
    implements manufacturer -> vendor -> hospital priority across both real
    baseline sources (`BaselineLibraryEntry` in `app/models/baseline_
    library.py`, network baselines; `EnterpriseVendorBaselineSubscription`
    in `app/models/enterprise_quality.py`, the table the actual upload/
    approval UI writes to). Veritas's own hierarchy names five tiers
    (manufacturer / manufacturer-authorized / vendor / organization /
    instrument-specific historical); this codebase's real baseline sources
    only distinguish manufacturer / vendor / hospital(organization) --
    "manufacturer-authorized" and "instrument-specific historical" are
    honestly folded into the nearest real tier rather than fabricated as
    separately tracked. `veritas_baseline_resolution_service.py` calls
    `resolve_baseline` directly and enriches the result; it never
    re-implements resolution.
  * **Baseline governance status (Section 3)** — three real, divergent
    vocabularies already exist (`BaselineLibraryEntry.approval_status`:
    pending/approved/deprecated; `EnterpriseVendorBaselineSubscription`:
    baseline_status/approval_status with its own `_APPROVED_VALUES` set;
    `Inspection.baseline_status`: not_checked/approved_baseline_found/
    pending_baseline_review/no_approved_baseline/baseline_not_available/
    approved). None of the three matches this brief's seven-status
    vocabulary. Rather than rewrite any of those tables (each belongs to
    an established feature), `VeritasBaselineGovernanceAction` is a new,
    append-only governance-action log keyed to (source_type, source_id) of
    whichever real baseline was resolved -- Veritas's canonical seven-
    status vocabulary is the *effective* status computed from the latest
    action in this log, never a mutation of the source tables.
  * **Coverage (Section 6)** — `inspection_coverage.compute_coverage`
    already returns required/inspected/missing zones and a quality band
    (not_assessed/complete/acceptable/incomplete/insufficient) that maps
    almost 1:1 onto this brief's coverage statuses. Reused directly.
  * **Image quality (Section 5)** — confirmed via repo-wide search: no
    real CV-based focus/blur/lighting/glare/exposure/obstruction/framing/
    magnification/orientation/duplication/compression-artifact detector
    exists anywhere in this codebase. Rather than fabricate these metrics,
    `veritas_image_quality_service.py` reports per-signal availability
    honestly (`"available": false"` for anything not actually measured,
    the same discipline as Nova's observability summary) and derives
    `quality_status` only from real proxy signals (image presence,
    historical `image_view_correct` supervisor corrections).
  * **Evidence provenance (Section 7)** — `guardianx_assurance.
    EvidenceLedgerEntry` is a *different* concept (what evidence backed an
    AI-assurance conclusion: knowledge/model/workflow versions + digital
    signature) -- not per-inspection-image provenance. The real per-image
    store is `RetainedImage`/`ImageLabel` (`app/models/retained_image.py`).
    `VeritasEvidenceProvenanceRecord` (below) references those by ID
    (never duplicating bytes/labels) and adds the file-hash/storage-
    location/modification-history/usage-scope fields neither existing
    table carries -- the same reference-by-ID pattern Sage's
    `SageEducationImageEntry` already established.
  * **Model/dataset versions (Section 1, 8)** — `app/models/model_
    registry.py`'s `ModelRegistryEntry` already carries first-class
    `model_version`/`dataset_version` columns; Veritas reads these rather
    than inventing new version fields.
  * **Training dataset assurance (Section 15)** — mirrors Sage's
    `SageEducationImageEntry` gate pattern (supervisor_validated +
    phi_review_status + usage_rights) exactly, adding the training-
    specific checks (instrument family/anatomy zone/finding/severity
    confirmed, duplicate detection) the brief names.
  * **Aegis / Vulcan / Sage (Section 16)** — read their real outputs
    (`vulcan_aegis_integration_service.compute_process_variation_signal`,
    `VulcanReliabilityAssessment`, `SageEducationImageEntry`) by reference
    only; Veritas never overwrites another specialist's conclusion, and no
    specialist may overwrite Veritas's own evidence findings.

## What is genuinely new in this file

Seven tables: `VeritasBaselineResolution`, `VeritasBaselineGovernanceAction`,
`VeritasEvidenceProvenanceRecord`, `VeritasEvidenceReadinessAssessment`,
`VeritasEvidenceConflict`, `VeritasTrainingDatasetEntry`, `VeritasFeedback`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Section 2: Baseline Resolution Hierarchy ─────────────────────────────────
BASELINE_TIER_MANUFACTURER = "manufacturer"
BASELINE_TIER_MANUFACTURER_AUTHORIZED = "manufacturer_authorized"
BASELINE_TIER_VENDOR = "vendor"
BASELINE_TIER_ORGANIZATION = "organization"
BASELINE_TIER_INSTRUMENT_HISTORICAL = "instrument_specific_historical"
BASELINE_TIER_NONE = "none"
BASELINE_TIERS = [
    BASELINE_TIER_MANUFACTURER, BASELINE_TIER_MANUFACTURER_AUTHORIZED, BASELINE_TIER_VENDOR,
    BASELINE_TIER_ORGANIZATION, BASELINE_TIER_INSTRUMENT_HISTORICAL, BASELINE_TIER_NONE,
]

RESOLUTION_STATUS_RESOLVED = "resolved"
RESOLUTION_STATUS_SUPERVISOR_REVIEW_REQUIRED = "SUPERVISOR_REVIEW_REQUIRED"
NO_APPROVED_BASELINE_MESSAGE = (
    "No approved baseline is available for this instrument and anatomy zone. "
    "A final baseline-dependent score cannot be issued."
)

# ── Section 3: Baseline Governance Rules (Veritas's canonical vocabulary) ────
BASELINE_STATUS_DRAFT = "draft"
BASELINE_STATUS_PENDING_REVIEW = "pending_review"
BASELINE_STATUS_APPROVED = "approved"
BASELINE_STATUS_CONDITIONALLY_APPROVED = "conditionally_approved"
BASELINE_STATUS_SUPERSEDED = "superseded"
BASELINE_STATUS_REJECTED = "rejected"
BASELINE_STATUS_ARCHIVED = "archived"
BASELINE_STATUSES = [
    BASELINE_STATUS_DRAFT, BASELINE_STATUS_PENDING_REVIEW, BASELINE_STATUS_APPROVED,
    BASELINE_STATUS_CONDITIONALLY_APPROVED, BASELINE_STATUS_SUPERSEDED, BASELINE_STATUS_REJECTED,
    BASELINE_STATUS_ARCHIVED,
]
# Only these statuses may influence a clinical recommendation.
BASELINE_STATUSES_USABLE_FOR_SCORING = {BASELINE_STATUS_APPROVED, BASELINE_STATUS_CONDITIONALLY_APPROVED}

# Section 13 governance actions (each logged row is its own audit event).
GOVERNANCE_ACTION_APPROVE = "approve"
GOVERNANCE_ACTION_CONDITIONALLY_APPROVE = "conditionally_approve"
GOVERNANCE_ACTION_REJECT = "reject"
GOVERNANCE_ACTION_SUPERSEDE = "supersede"
GOVERNANCE_ACTION_ARCHIVE = "archive"
GOVERNANCE_ACTION_REQUEST_ADDITIONAL_IMAGES = "request_additional_images"
GOVERNANCE_ACTIONS = [
    GOVERNANCE_ACTION_APPROVE, GOVERNANCE_ACTION_CONDITIONALLY_APPROVE, GOVERNANCE_ACTION_REJECT,
    GOVERNANCE_ACTION_SUPERSEDE, GOVERNANCE_ACTION_ARCHIVE, GOVERNANCE_ACTION_REQUEST_ADDITIONAL_IMAGES,
]
_GOVERNANCE_ACTION_TO_STATUS = {
    GOVERNANCE_ACTION_APPROVE: BASELINE_STATUS_APPROVED,
    GOVERNANCE_ACTION_CONDITIONALLY_APPROVE: BASELINE_STATUS_CONDITIONALLY_APPROVED,
    GOVERNANCE_ACTION_REJECT: BASELINE_STATUS_REJECTED,
    GOVERNANCE_ACTION_SUPERSEDE: BASELINE_STATUS_SUPERSEDED,
    GOVERNANCE_ACTION_ARCHIVE: BASELINE_STATUS_ARCHIVED,
}


def status_for_action(action: str) -> str:
    """The canonical status a governance action resolves to. Actions that
    don't themselves change status (e.g. request_additional_images) return
    an empty string -- the caller keeps the prior effective status."""
    return _GOVERNANCE_ACTION_TO_STATUS.get(action, "")


# ── Section 4: Instrument-to-Baseline Matching ───────────────────────────────
MATCH_EXACT = "exact"
MATCH_COMPATIBLE = "compatible"
MATCH_PARTIAL = "partial"
MATCH_UNCERTAIN = "uncertain"
MATCH_MISMATCH = "mismatch"
MATCH_UNAVAILABLE = "unavailable"
MATCH_CLASSIFICATIONS = [MATCH_EXACT, MATCH_COMPATIBLE, MATCH_PARTIAL, MATCH_UNCERTAIN, MATCH_MISMATCH, MATCH_UNAVAILABLE]

# ── Section 5: Image Quality Assessment ──────────────────────────────────────
IMAGE_QUALITY_EXCELLENT = "excellent"
IMAGE_QUALITY_ACCEPTABLE = "acceptable"
IMAGE_QUALITY_LIMITED = "limited"
IMAGE_QUALITY_INSUFFICIENT = "insufficient"
IMAGE_QUALITY_STATUSES = [IMAGE_QUALITY_EXCELLENT, IMAGE_QUALITY_ACCEPTABLE, IMAGE_QUALITY_LIMITED, IMAGE_QUALITY_INSUFFICIENT]

# ── Section 6: Inspection Coverage Assurance ─────────────────────────────────
COVERAGE_COMPLETE = "complete"
COVERAGE_ACCEPTABLE = "acceptable"
COVERAGE_INCOMPLETE = "incomplete"
COVERAGE_INSUFFICIENT = "insufficient"
COVERAGE_NOT_ASSESSED = "not_assessed"
COVERAGE_STATUSES = [COVERAGE_COMPLETE, COVERAGE_ACCEPTABLE, COVERAGE_INCOMPLETE, COVERAGE_INSUFFICIENT, COVERAGE_NOT_ASSESSED]

# ── Section 7: Evidence Provenance Ledger ────────────────────────────────────
EVIDENCE_TYPE_INSPECTION_IMAGE = "inspection_image"
EVIDENCE_TYPE_MANUFACTURER_BASELINE = "manufacturer_baseline"
EVIDENCE_TYPE_VENDOR_BASELINE = "vendor_baseline"
EVIDENCE_TYPE_ORGANIZATION_BASELINE = "organization_baseline"
EVIDENCE_TYPE_SUPERVISOR_ANNOTATION = "supervisor_annotation"
EVIDENCE_TYPE_REPAIR_RECORD = "repair_record"
EVIDENCE_TYPE_IFU_REFERENCE = "ifu_reference"
EVIDENCE_TYPE_KNOWLEDGE_ARTICLE = "knowledge_article"
EVIDENCE_TYPE_MODEL_PREDICTION = "model_prediction"
EVIDENCE_TYPE_FINAL_DISPOSITION = "final_disposition"
EVIDENCE_TYPES = [
    EVIDENCE_TYPE_INSPECTION_IMAGE, EVIDENCE_TYPE_MANUFACTURER_BASELINE, EVIDENCE_TYPE_VENDOR_BASELINE,
    EVIDENCE_TYPE_ORGANIZATION_BASELINE, EVIDENCE_TYPE_SUPERVISOR_ANNOTATION, EVIDENCE_TYPE_REPAIR_RECORD,
    EVIDENCE_TYPE_IFU_REFERENCE, EVIDENCE_TYPE_KNOWLEDGE_ARTICLE, EVIDENCE_TYPE_MODEL_PREDICTION,
    EVIDENCE_TYPE_FINAL_DISPOSITION,
]

# ── Section 8: Evidence Readiness Score bands ────────────────────────────────
READINESS_STRONG = "strong_evidence"
READINESS_MODERATE = "moderate_evidence"
READINESS_LIMITED = "limited_evidence"
READINESS_INSUFFICIENT = "insufficient_evidence"


def readiness_category(score: float) -> str:
    if score >= 90:
        return READINESS_STRONG
    if score >= 75:
        return READINESS_MODERATE
    if score >= 50:
        return READINESS_LIMITED
    return READINESS_INSUFFICIENT


# ── Section 9: Conflict types ─────────────────────────────────────────────────
CONFLICT_INSTRUMENT_FAMILY_DIFFERS = "instrument_family_differs_from_baseline"
CONFLICT_IMAGE_TAG_DIFFERS = "image_tag_differs_from_predicted_zone"
CONFLICT_MANUFACTURER_DIFFERS = "manufacturer_differs_from_baseline_owner"
CONFLICT_MULTIPLE_ACTIVE_BASELINES = "multiple_active_approved_baselines"
CONFLICT_SUPERVISOR_LABEL_CONFLICT = "supervisor_label_conflicts_with_ai_label"
CONFLICT_MODEL_NOT_APPROVED = "model_not_approved_for_instrument_family"
CONFLICT_BASELINE_SUPERSEDED_AFTER_INSPECTION = "baseline_superseded_after_inspection"
CONFLICT_DUPLICATE_IMAGE_DIFFERENT_ZONES = "duplicate_image_different_zones"
CONFLICT_EVIDENCE_TIMESTAMP_INCONSISTENCY = "evidence_timestamp_inconsistency"
CONFLICT_TYPES = [
    CONFLICT_INSTRUMENT_FAMILY_DIFFERS, CONFLICT_IMAGE_TAG_DIFFERS, CONFLICT_MANUFACTURER_DIFFERS,
    CONFLICT_MULTIPLE_ACTIVE_BASELINES, CONFLICT_SUPERVISOR_LABEL_CONFLICT, CONFLICT_MODEL_NOT_APPROVED,
    CONFLICT_BASELINE_SUPERSEDED_AFTER_INSPECTION, CONFLICT_DUPLICATE_IMAGE_DIFFERENT_ZONES,
    CONFLICT_EVIDENCE_TIMESTAMP_INCONSISTENCY,
]

# ── Section 10: Evidence Gate outcomes ───────────────────────────────────────
GATE_PROCEED_WITH_ANALYSIS = "PROCEED_WITH_ANALYSIS"
GATE_PROCEED_WITH_LIMITATIONS = "PROCEED_WITH_LIMITATIONS"
GATE_ADDITIONAL_IMAGE_REQUIRED = "ADDITIONAL_IMAGE_REQUIRED"
GATE_BASELINE_REVIEW_REQUIRED = "BASELINE_REVIEW_REQUIRED"
GATE_SUPERVISOR_REVIEW_REQUIRED = "SUPERVISOR_REVIEW_REQUIRED"
GATE_EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
GATE_ANALYSIS_BLOCKED = "ANALYSIS_BLOCKED"
GATE_OUTCOMES = [
    GATE_PROCEED_WITH_ANALYSIS, GATE_PROCEED_WITH_LIMITATIONS, GATE_ADDITIONAL_IMAGE_REQUIRED,
    GATE_BASELINE_REVIEW_REQUIRED, GATE_SUPERVISOR_REVIEW_REQUIRED, GATE_EVIDENCE_CONFLICT, GATE_ANALYSIS_BLOCKED,
]

# ── Section 15: Training dataset statuses ────────────────────────────────────
DATASET_CANDIDATE = "candidate"
DATASET_PENDING_VALIDATION = "pending_validation"
DATASET_APPROVED_FOR_TRAINING = "approved_for_training"
DATASET_EXCLUDED = "excluded"
DATASET_QUARANTINED = "quarantined"
DATASET_STATUSES = [DATASET_CANDIDATE, DATASET_PENDING_VALIDATION, DATASET_APPROVED_FOR_TRAINING, DATASET_EXCLUDED, DATASET_QUARANTINED]

# ── Section 17 feedback actions (includes the Section 10 gate override) ─────
FEEDBACK_ACTION_OVERRIDE_EVIDENCE_GATE = "override_evidence_gate"

VERITAS_AGENT_VERSION = "1.0.0"

DISCLAIMER = (
    "Veritas evaluates whether an inspection has sufficient, reliable, and governed evidence to "
    "support an AI recommendation. Veritas does not independently approve an instrument -- it "
    "determines whether the evidence is trustworthy enough for the inspection workflow to proceed "
    "and identifies what additional evidence is required. Every evidence decision remains versioned, "
    "explainable, auditable, tenant-isolated, and human-governed."
)


class VeritasBaselineResolution(Base):
    """One point-in-time baseline resolution (Section 2) -- a persisted audit
    row every time resolution runs, built on top of the real
    `baseline_comparison_scoring_service.resolve_baseline`, never a
    silent substitution of an unapproved baseline."""

    __tablename__ = "veritas_baseline_resolutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    instrument_identity: Mapped[str] = mapped_column(String(300), default="", nullable=False, index=True)
    instrument_type: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)

    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    baseline_source_type: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    baseline_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    baseline_tier: Mapped[str] = mapped_column(String(40), default=BASELINE_TIER_NONE, nullable=False, index=True)
    baseline_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    image_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    resolution_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class VeritasBaselineGovernanceAction(Base):
    """An append-only governance action on a real baseline (Section 3, 13).
    The baseline's effective canonical status is the status of the latest
    action for its (source_type, source_id) -- this table is never mutated
    or deleted, so every action is its own audit event."""

    __tablename__ = "veritas_baseline_governance_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    baseline_source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    baseline_source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resulting_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)

    owner: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    known_limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    usage_rights: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    performed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    performed_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)


class VeritasEvidenceProvenanceRecord(Base):
    """One evidence-object provenance record (Section 7) -- references
    existing evidence (RetainedImage/baseline/etc.) by ID, never a
    duplicate of the underlying bytes or table."""

    __tablename__ = "veritas_evidence_provenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    organization: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    facility: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    creator: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    instrument_id: Mapped[str] = mapped_column(String(300), default="", nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    baseline_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    file_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    storage_location: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    approval_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    version: Mapped[str] = mapped_column(String(40), default="1.0.0", nullable=False)
    modification_history_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    usage_scope: Mapped[str] = mapped_column(String(100), default="internal", nullable=False)


class VeritasEvidenceReadinessAssessment(Base):
    """The central Veritas assessment (Sections 1, 8, 10, 12) -- one row per
    evidence-assurance run for an inspection. Mirrors
    `VulcanReliabilityAssessment`'s role for Vulcan. `recommended_gate` is
    Veritas's own advisory output; `final_disposition`/override fields are
    only ever set via a supervisor-gated `VeritasFeedback` action."""

    __tablename__ = "veritas_evidence_readiness_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    instrument_identity: Mapped[str] = mapped_column(String(300), default="", nullable=False, index=True)
    baseline_resolution_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    match_classification: Mapped[str] = mapped_column(String(20), default=MATCH_UNAVAILABLE, nullable=False, index=True)
    image_quality_status: Mapped[str] = mapped_column(String(20), default=IMAGE_QUALITY_INSUFFICIENT, nullable=False, index=True)
    coverage_status: Mapped[str] = mapped_column(String(20), default=COVERAGE_NOT_ASSESSED, nullable=False, index=True)
    coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    missing_zones_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    readiness_category: Mapped[str] = mapped_column(String(30), default=READINESS_INSUFFICIENT, nullable=False, index=True)
    score_breakdown_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    limitations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    recommended_gate: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    next_action: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reasoning_narrative: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)

    model_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    agent_version: Mapped[str] = mapped_column(String(20), default=VERITAS_AGENT_VERSION, nullable=False)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    final_gate_override: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    overridden_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disclaimer: Mapped[str] = mapped_column(Text, default=DISCLAIMER, nullable=False)


class VeritasEvidenceConflict(Base):
    """One detected conflict (Section 9), linked to the assessment it was
    found under."""

    __tablename__ = "veritas_evidence_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    assessment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    conflict_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="moderate", nullable=False)
    affected_evidence_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    recommended_resolution: Mapped[str] = mapped_column(Text, default="", nullable=False)
    responsible_reviewer_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class VeritasTrainingDatasetEntry(Base):
    """Training Dataset Assurance (Section 15) -- gates a real
    `RetainedImage`/`ImageLabel` pair into a training-dataset status.
    Mirrors Sage's `SageEducationImageEntry` reference-by-ID pattern."""

    __tablename__ = "veritas_training_dataset_entries"

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
    image_quality_threshold_met: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usage_rights: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    phi_review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provenance_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    dataset_status: Mapped[str] = mapped_column(String(30), default=DATASET_CANDIDATE, nullable=False, index=True)
    status_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)


class VeritasFeedback(Base):
    """Supervisor/reviewer feedback on Veritas findings (Section 17) --
    also the ONLY place an evidence-gate override is recorded (action
    `override_evidence_gate`, `override_reason` required)."""

    __tablename__ = "veritas_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    assessment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    baseline_match_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    image_quality_assessment_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    anatomy_zone_tag_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    coverage_determination_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    evidence_conflict_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    corrected_baseline: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    corrected_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    final_evidence_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    reviewer_rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)

    override_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    limitations_acknowledged: Mapped[str] = mapped_column(Text, default="", nullable=False)
    final_disposition: Mapped[str] = mapped_column(String(50), default="", nullable=False)

    submitted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    submitted_role: Mapped[str] = mapped_column(String(50), default="", nullable=False)
