"""Dataset Registry & AI Model Development Foundation.

This is deliberately additive to the ML governance infrastructure already
built in earlier phases — it does not duplicate:
  * ``app.models.retained_image.RetainedImage`` / ``ImageLabel`` (the actual
    stored bytes + per-finding label rows),
  * ``app.models.veritas_evidence.VeritasTrainingDatasetEntry`` (training-data
    assurance gating for one retained-image/label pair),
  * ``app.models.model_registry.ModelRegistryEntry`` (extended in this same
    pass with new columns rather than replaced — see that file),
  * ``app.services.ml.dataset_split`` (leakage-safe splitting — reused, not
    reimplemented).

What is genuinely new here: a single per-image dataset-registry row carrying
every field this program's brief requires (dataset/image/inspection linkage,
full capture metadata, review/annotation state, split assignment, usage
rights, PHI verification, training eligibility, retention status); an
explicit, immutable ``DatasetVersion`` entity (versus the existing
free-text version tag); a formal 7-state annotation lifecycle event log;
a double-blind review record (primary + independent reviewer +
adjudicator); and a real, pixel-computed image-quality assessment.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Annotation lifecycle (Section 3) ────────────────────────────────────────
UNLABELED = "UNLABELED"
LABELED = "LABELED"
SECOND_REVIEW = "SECOND_REVIEW"
DISAGREEMENT = "DISAGREEMENT"
ADJUDICATED = "ADJUDICATED"
APPROVED = "APPROVED"
ARCHIVED = "ARCHIVED"

ANNOTATION_STATES = [
    UNLABELED, LABELED, SECOND_REVIEW, DISAGREEMENT, ADJUDICATED, APPROVED, ARCHIVED,
]

# Valid forward transitions (a state machine, not a free-for-all — mirrors
# app.services.workflow_state_service's append-only, validated-transition
# pattern). ARCHIVED is reachable from any non-terminal state (a dataset
# curator may retire an entry at any point); nothing leaves ARCHIVED.
VALID_ANNOTATION_TRANSITIONS: dict[str, set[str]] = {
    UNLABELED: {LABELED, ARCHIVED},
    LABELED: {SECOND_REVIEW, ARCHIVED},
    SECOND_REVIEW: {ADJUDICATED, DISAGREEMENT, APPROVED, ARCHIVED},
    DISAGREEMENT: {ADJUDICATED, ARCHIVED},
    ADJUDICATED: {APPROVED, ARCHIVED},
    APPROVED: {ARCHIVED},
    ARCHIVED: set(),
}

# ── Image quality (Section 5) ───────────────────────────────────────────────
QUALITY_EXCELLENT = "Excellent"
QUALITY_GOOD = "Good"
QUALITY_MARGINAL = "Marginal"
QUALITY_POOR = "Poor"
QUALITY_REJECT = "Reject"

IMAGE_QUALITY_LEVELS = [
    QUALITY_EXCELLENT, QUALITY_GOOD, QUALITY_MARGINAL, QUALITY_POOR, QUALITY_REJECT,
]


class DatasetVersion(Base):
    """An immutable, named dataset snapshot (Section 2).

    Distinct from ``VeritasTrainingDatasetEntry.dataset_version`` (a free-text
    tag copied onto each row) — this is a first-class entity that can be
    explicitly frozen. Once ``frozen`` is True, no service in this module
    will attach a new ``DatasetRegistryEntry`` to it or change an existing
    one's metadata; a correction requires a NEW version (``supersedes_id``),
    never a silent edit of history.
    """

    __tablename__ = "dataset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    version_label: Mapped[str] = mapped_column(String(40), nullable=False, index=True)  # e.g. "v0.1"
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    supersedes_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    frozen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frozen_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    image_count_at_freeze: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DatasetRegistryEntry(Base):
    """One row per image admitted to the governed ML dataset registry
    (Section 1). References the real stored artifact by ID rather than
    duplicating it: ``retained_image_id`` -> ``RetainedImage``,
    ``inspection_id`` -> ``Inspection``. All 22 required metadata fields are
    tracked as real columns, not a free-form JSON blob, so validation and
    querying stay honest and enforceable.
    """

    __tablename__ = "dataset_registry_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    # Dataset ID / Image ID / Inspection ID
    dataset_version_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    retained_image_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Instrument / capture metadata
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    instrument_model: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    inspection_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capture_device: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    image_resolution: Mapped[str] = mapped_column(String(20), default="", nullable=False)  # "WxH"
    lighting_condition: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)

    # Quality + provenance
    image_quality: Mapped[str] = mapped_column(String(20), default="", nullable=False, index=True)
    facility: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # Annotation state
    current_label: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default=UNLABELED, nullable=False, index=True)
    annotation_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Dataset placement
    dataset_version_label: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    split_assignment: Mapped[str] = mapped_column(String(20), default="", nullable=False, index=True)

    # Governance
    usage_rights: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    phi_verification: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    training_eligibility: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    retention_status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)

    # Duplicate detection support (image identity, not row identity).
    image_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)


class AnnotationEvent(Base):
    """Append-only annotation lifecycle log (Section 3) — the current state
    of an entry is always the ``to_state`` of its latest event, mirroring
    ``app.services.workflow_state_service``'s inspection-workflow pattern so
    the full labeling history is always reconstructable, never overwritten.
    """

    __tablename__ = "annotation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    dataset_entry_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    from_state: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    to_state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    comments: Mapped[str] = mapped_column(Text, default="", nullable=False)
    changes_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class DoubleBlindReview(Base):
    """Primary + independent reviewer, plus adjudication (Section 4).

    Neither reviewer sees the other's label at submission time (enforced in
    the service layer: ``independent_label`` may only be submitted once, and
    the primary reviewer's label is never surfaced to the independent
    reviewer through this record before they submit their own).
    """

    __tablename__ = "double_blind_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    dataset_entry_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    primary_reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    primary_label: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    primary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    independent_reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    independent_label: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    independent_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    independent_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agreement: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    adjudicator: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolution: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImageQualityAssessment(Base):
    """Real, pixel-computed image-quality assessment (Section 5) — every
    score here is computed from actual image bytes (Pillow), never
    fabricated. See ``app.services.ml.image_quality`` for the computation
    and ``docs/ml-governance/DATA_GOVERNANCE.md`` for the exact thresholds.
    """

    __tablename__ = "image_quality_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    dataset_entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    retained_image_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    width: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    brightness_mean: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sharpness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    blur_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lighting_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exposure_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    focus_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cropping_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visibility_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    overall_quality: Mapped[str] = mapped_column(String(20), default=QUALITY_MARGINAL, nullable=False, index=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
