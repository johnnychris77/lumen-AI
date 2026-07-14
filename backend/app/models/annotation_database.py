"""LumenAI Annotation Database & Storage System.

The authoritative source of truth for every AI observation, expert
annotation, adjudication, and ground truth label — additive to, and
composed with, the infrastructure already built in prior sprints rather
than a competing system:

  * Reuses `app.models.dataset_governance.ANNOTATION_STATES` /
    `VALID_ANNOTATION_TRANSITIONS` for the review-state vocabulary instead
    of defining a third copy (Sprint 4's `DoubleBlindReview`/
    `AnnotationEvent` remain unchanged and cover the dataset-registry-entry
    level workflow; this module's `Annotation` is a richer, image-level
    finding record that a single `DatasetRegistryEntry` may have several
    of).
  * Reuses `app.services.ml.lcid_service` for Digital Twin identity
    (barcode/UDI-based, never fabricated) and baseline resolution.
  * Reuses `app.models.lumen_decision_engine.UnknownFindingReview`'s
    workflow vocabulary for the unknown-finding fields on `Annotation`
    (a lighter-weight, denormalized mirror — an `Annotation` can exist
    without a full `UnknownFindingReview` row when it originates directly
    from human annotation rather than an AI observation).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Region annotation types (Section 4) ─────────────────────────────────────
REGION_BOUNDING_BOX = "bounding_box"
REGION_POLYGON = "polygon"
REGION_SEGMENTATION_MASK = "segmentation_mask"
REGION_POINT = "point"
REGION_WHOLE_IMAGE = "whole_image_classification"
REGION_3D = "future_3d"  # reserved, not yet implemented — never fabricated

REGION_TYPES = [
    REGION_BOUNDING_BOX, REGION_POLYGON, REGION_SEGMENTATION_MASK,
    REGION_POINT, REGION_WHOLE_IMAGE, REGION_3D,
]

# ── Ground Truth status (Section 6) ─────────────────────────────────────────
GROUND_TRUTH_DRAFT = "DRAFT"
GROUND_TRUTH_ACTIVE = "ACTIVE"
GROUND_TRUTH_STATUSES = [GROUND_TRUTH_DRAFT, GROUND_TRUTH_ACTIVE]

# ── Baseline types (Section 8) ───────────────────────────────────────────────
BASELINE_TYPE_MANUFACTURER = "manufacturer"
BASELINE_TYPE_HOSPITAL = "hospital"
BASELINE_TYPE_DIGITAL_TWIN = "digital_twin"
BASELINE_TYPE_RESEARCH = "research"
BASELINE_TYPES = [
    BASELINE_TYPE_MANUFACTURER, BASELINE_TYPE_HOSPITAL,
    BASELINE_TYPE_DIGITAL_TWIN, BASELINE_TYPE_RESEARCH,
]

# ── Roles (Section 14) ───────────────────────────────────────────────────────
# `role` columns across this codebase (app.models.user.User,
# app.db.models.TenantMembership) are free-form String columns, not an
# enum — these two role strings are additive and require no change to core
# auth infrastructure. The other four map onto pre-existing roles.
ROLE_ADMINISTRATOR = "admin"
ROLE_CLINICAL_REVIEWER = "clinical_reviewer"
ROLE_REVIEWER = "spd_manager"
ROLE_ANNOTATOR = "operator"
ROLE_AI_RESEARCHER = "ai_researcher"
ROLE_VIEWER = "viewer"

ROLES_MAY_FINALIZE_GROUND_TRUTH = {ROLE_ADMINISTRATOR, ROLE_CLINICAL_REVIEWER}
ROLES_MAY_REVIEW = {ROLE_ADMINISTRATOR, ROLE_CLINICAL_REVIEWER, ROLE_REVIEWER}
ROLES_MAY_ANNOTATE = {ROLE_ADMINISTRATOR, ROLE_CLINICAL_REVIEWER, ROLE_REVIEWER, ROLE_ANNOTATOR}
ROLES_MAY_EXPORT = {ROLE_ADMINISTRATOR, ROLE_AI_RESEARCHER}
ROLES_MAY_VIEW = {
    ROLE_ADMINISTRATOR, ROLE_CLINICAL_REVIEWER, ROLE_REVIEWER,
    ROLE_ANNOTATOR, ROLE_AI_RESEARCHER, ROLE_VIEWER,
}


class AnnotationSequenceCounter(Base):
    """Per-year atomic counter backing `ANN-YYYY-NNNNNNNNN` generation —
    mirrors `app.models.dataset_governance.LcidSequenceCounter`."""

    __tablename__ = "annotation_sequence_counters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Annotation(Base):
    """Section 1-10 — the authoritative annotation record. The row always
    reflects current state; every change is additionally captured as an
    immutable `AnnotationVersion` snapshot (Section 7) — history is never
    overwritten."""

    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    # Section 1 — permanent, immutable ID.
    ann_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    # Section 2 — relationships.
    retained_image_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    instrument_model: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    digital_twin_id: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    baseline_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    dataset_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ground_truth_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)  # blank = not AI-assisted

    # Section 3 — observation storage.
    primary_observation: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    secondary_observation: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    appearance_attributes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewer_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    comments: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommendation: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    supervisor_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unknown_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    image_quality: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    # Section 4 — region annotation (normalized coordinates, 0.0-1.0).
    region_type: Mapped[str] = mapped_column(String(30), default=REGION_WHOLE_IMAGE, nullable=False)
    region_coordinates_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Review workflow status — reuses dataset_governance.ANNOTATION_STATES.
    review_status: Mapped[str] = mapped_column(String(20), default="UNLABELED", nullable=False, index=True)

    # Section 6 — Ground Truth.
    ground_truth_status: Mapped[str] = mapped_column(String(20), default=GROUND_TRUTH_DRAFT, nullable=False, index=True)

    # Section 7 — versioning (the row is always "current"; see AnnotationVersion).
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Section 8 — baseline linkage.
    baseline_type: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    baseline_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    baseline_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_deviation: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Section 10 — unknown findings.
    supervisor_classification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clinical_review_status: Mapped[str] = mapped_column(String(30), default="not_started", nullable=False)
    candidate_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    promotion_status: Mapped[str] = mapped_column(String(30), default="not_promoted", nullable=False)


class AnnotationVersion(Base):
    """Section 7 — append-only version history. Never overwritten; a new
    row is added for every change to the parent `Annotation`."""

    __tablename__ = "annotation_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    annotation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    editor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    previous_version_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)


class AnnotationReview(Base):
    """Section 5 — multi-reviewer workflow scoped to one `Annotation`.
    Structurally mirrors `app.models.dataset_governance.DoubleBlindReview`
    (primary + independent + adjudicator) but keyed to `annotation_id`
    since a single dataset image may carry several distinct annotations,
    each needing its own independent review record."""

    __tablename__ = "annotation_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    annotation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    primary_reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    primary_label: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    primary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    primary_comments: Mapped[str] = mapped_column(Text, default="", nullable=False)

    secondary_reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    secondary_label: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    secondary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    secondary_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    secondary_comments: Mapped[str] = mapped_column(Text, default="", nullable=False)

    agreement: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    disagreement_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    adjudicator: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    resolution: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    adjudication_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
