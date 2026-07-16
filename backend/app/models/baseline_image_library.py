"""Project Atlas Sprint 1 — Baseline Image Library.

Converts `app.models.baseline_library.BaselineLibraryEntry` (metadata-only
today — see `docs/baseline-library/BASELINE_CURRENT_STATE_TRACE.md`) into a
true, governed, image-backed baseline capability. This module is
deliberately additive and does NOT duplicate:

  * `app.models.dataset_governance.DatasetRegistryEntry` — the existing
    LCID-registered image entity. A `BaselineImageLink` row REFERENCES one
    of these by id; it never copies or re-registers image metadata that
    entry already owns (instrument_family, manufacturer, anatomy_zone,
    image_quality, usage_rights, phi_verification, digital_twin_id are all
    read from the linked entry, not re-entered here — see
    `baseline_image_library_service.linked_lcid_entry()`).
  * `app.models.retained_image.RetainedImage` — the sole owner of actual
    image bytes. No table in this module has a `LargeBinary`/bytes column.
  * `app.models.annotation_database.Annotation` /
    `annotation_ground_truth_service` — Ground Truth eligibility is read
    from there, never re-derived here.
  * `app.services.ml.lcid_service` — Digital Twin identity
    (`instrument_digital_twin_id`) is reused as-is.
  * Any of the other eight pre-existing "baseline" concepts enumerated in
    the trace doc (`EnterpriseBaseline`, `EnterpriseInstrumentBaseline`,
    `EnterpriseVendorBaselineSubscription`, `BaselineDecisionPolicy`,
    `BaselineGovernanceRecord`, `VendorBaselineExternalRecord`,
    `VendorBaselineAuditEvent`, `ManufacturerBaselineQuality`) — this sprint
    extends `BaselineLibraryEntry` specifically, the one already wired into
    the LCID pipeline and the live scoring path.

What is genuinely new: the reverse link `BaselineLibraryEntry` ->
LCID-registered image (`BaselineImageLink`), a governed lifecycle for that
link (`BASELINE_IMAGE_STATES`), a review record
(`BaselineImageReview`), and a multi-image grouping entity (`BaselineSet`
+ `BaselineSetMember`) for "multiple known-good images instead of one
perfect reference image."
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# ── Governed lifecycle (Section 4) ──────────────────────────────────────────
STATE_DRAFT = "DRAFT"
STATE_PENDING_REVIEW = "PENDING_REVIEW"
STATE_APPROVED = "APPROVED"
STATE_ACTIVE = "ACTIVE"
STATE_SUSPENDED = "SUSPENDED"
STATE_SUPERSEDED = "SUPERSEDED"
STATE_REJECTED = "REJECTED"
STATE_ARCHIVED = "ARCHIVED"

BASELINE_IMAGE_STATES = [
    STATE_DRAFT, STATE_PENDING_REVIEW, STATE_APPROVED, STATE_ACTIVE,
    STATE_SUSPENDED, STATE_SUPERSEDED, STATE_REJECTED, STATE_ARCHIVED,
]

# Valid forward transitions — mirrors the append-only, validated-transition
# pattern already used by dataset_governance.VALID_ANNOTATION_TRANSITIONS.
# ACTIVE is reachable only from APPROVED (never directly from DRAFT/PENDING),
# so "only ACTIVE approved baseline images may influence live comparison"
# (Section 4) is a structural guarantee, not just a convention.
VALID_BASELINE_IMAGE_TRANSITIONS: dict[str, set[str]] = {
    STATE_DRAFT: {STATE_PENDING_REVIEW, STATE_ARCHIVED},
    STATE_PENDING_REVIEW: {STATE_APPROVED, STATE_REJECTED, STATE_ARCHIVED},
    STATE_APPROVED: {STATE_ACTIVE, STATE_ARCHIVED},
    STATE_ACTIVE: {STATE_SUSPENDED, STATE_SUPERSEDED, STATE_ARCHIVED},
    STATE_SUSPENDED: {STATE_ACTIVE, STATE_SUPERSEDED, STATE_ARCHIVED},
    STATE_SUPERSEDED: {STATE_ARCHIVED},
    STATE_REJECTED: {STATE_ARCHIVED},
    STATE_ARCHIVED: set(),
}

# ── Baseline source types (Section 2) ───────────────────────────────────────
SOURCE_MANUFACTURER_REFERENCE = "manufacturer_reference"
SOURCE_ORGANIZATION_KNOWN_GOOD = "organization_known_good"
SOURCE_NEW_INSTRUMENT_REFERENCE = "new_instrument_reference"
SOURCE_POST_REPAIR_REFERENCE = "post_repair_reference"
SOURCE_DIGITAL_TWIN_INITIAL_REFERENCE = "digital_twin_initial_reference"
SOURCE_GOVERNED_CONSENSUS_REFERENCE = "governed_consensus_reference"
SOURCE_RESEARCH_REFERENCE = "research_reference"

BASELINE_SOURCE_TYPES = [
    SOURCE_MANUFACTURER_REFERENCE, SOURCE_ORGANIZATION_KNOWN_GOOD,
    SOURCE_NEW_INSTRUMENT_REFERENCE, SOURCE_POST_REPAIR_REFERENCE,
    SOURCE_DIGITAL_TWIN_INITIAL_REFERENCE, SOURCE_GOVERNED_CONSENSUS_REFERENCE,
    SOURCE_RESEARCH_REFERENCE,
]

# Source types that assert manufacturer provenance — these require real
# supporting evidence (source_organization + source_reference), never a
# bare dropdown selection (Section 5).
SOURCE_TYPES_REQUIRING_PROVENANCE = {SOURCE_MANUFACTURER_REFERENCE}

# ── Baseline image types (Section 3) ────────────────────────────────────────
IMAGE_TYPE_MANUFACTURER_BASELINE = "manufacturer_baseline"
IMAGE_TYPE_ORGANIZATION_BASELINE = "organization_baseline"
IMAGE_TYPE_DIGITAL_TWIN_BASELINE = "digital_twin_baseline"
IMAGE_TYPE_ANATOMY_ZONE_REFERENCE = "anatomy_zone_reference"
IMAGE_TYPE_POST_REPAIR_REFERENCE = "post_repair_reference"
IMAGE_TYPE_CANDIDATE_BASELINE = "candidate_baseline"

BASELINE_IMAGE_TYPES = [
    IMAGE_TYPE_MANUFACTURER_BASELINE, IMAGE_TYPE_ORGANIZATION_BASELINE,
    IMAGE_TYPE_DIGITAL_TWIN_BASELINE, IMAGE_TYPE_ANATOMY_ZONE_REFERENCE,
    IMAGE_TYPE_POST_REPAIR_REFERENCE, IMAGE_TYPE_CANDIDATE_BASELINE,
]

# ── Compatibility contract outcomes (Section 7) ─────────────────────────────
COMPATIBLE = "COMPATIBLE"
INCOMPATIBLE_INSTRUMENT = "INCOMPATIBLE_INSTRUMENT"
INCOMPATIBLE_ANATOMY_ZONE = "INCOMPATIBLE_ANATOMY_ZONE"
INCOMPATIBLE_VIEW = "INCOMPATIBLE_VIEW"
INCOMPATIBLE_ORIENTATION = "INCOMPATIBLE_ORIENTATION"
INSUFFICIENT_IMAGE_QUALITY = "INSUFFICIENT_IMAGE_QUALITY"
BASELINE_NOT_ACTIVE = "BASELINE_NOT_ACTIVE"
NO_APPROVED_BASELINE = "NO_APPROVED_BASELINE"

# ── Resolution scopes (Section 8), most specific first ──────────────────────
RESOLUTION_DIGITAL_TWIN_EXACT = "digital_twin_exact"
RESOLUTION_MANUFACTURER_MODEL_ZONE = "manufacturer_model_zone"
RESOLUTION_ORGANIZATION_FAMILY_ZONE = "organization_family_zone"
RESOLUTION_GOVERNED_CONSENSUS = "governed_consensus"
RESOLUTION_NONE = "none"

RESOLUTION_HIERARCHY = [
    RESOLUTION_DIGITAL_TWIN_EXACT, RESOLUTION_MANUFACTURER_MODEL_ZONE,
    RESOLUTION_ORGANIZATION_FAMILY_ZONE, RESOLUTION_GOVERNED_CONSENSUS, RESOLUTION_NONE,
]

# Legacy-migration marker (Section 15) — a pre-existing BaselineLibraryEntry
# with no linked, ACTIVE BaselineImageLink is reported (never silently
# treated as image-comparable) under this label.
IMAGE_EVIDENCE_MISSING = "IMAGE_EVIDENCE_MISSING"


class BaselineImageLink(Base):
    """The reverse link this sprint adds: which LCID-registered image
    (`DatasetRegistryEntry`) represents a given `BaselineLibraryEntry`, for
    which anatomy zone/view/orientation, under what governance.

    `lcid_image_id` is a soft reference to `dataset_registry_entries.id`
    (mirroring `DatasetRegistryEntry.baseline_id`'s own soft-FK convention
    to `baseline_library.id` — the two modules were migrated separately)
    validated for orphans by this module's service layer, not a DB-level FK.
    Image bytes are never duplicated: to display or compare this baseline's
    image, callers must load the linked `DatasetRegistryEntry` ->
    `RetainedImage.image_bytes`.
    """

    __tablename__ = "baseline_image_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)
    facility_id: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)

    baseline_library_entry_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lcid_image_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Denormalized/cached from the linked DatasetRegistryEntry at link time
    # for fast listing/search without a join — always re-validated against
    # the live entry before any activation or comparison decision (never
    # trusted as the source of truth on its own).
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    manufacturer: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    catalog_number: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    inspection_view: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    orientation: Mapped[str] = mapped_column(String(60), default="", nullable=False)

    image_type: Mapped[str] = mapped_column(String(30), default="", nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(40), default="", nullable=False, index=True)
    source_organization: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    # Real supporting evidence for the claimed source (a document id, PO/
    # correspondence reference, vendor portal submission id, ...) — required
    # for SOURCE_TYPES_REQUIRING_PROVENANCE, enforced in the service layer.
    source_reference: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    baseline_version: Mapped[str] = mapped_column(String(40), default="1.0", nullable=False)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lifecycle_status: Mapped[str] = mapped_column(String(20), default=STATE_DRAFT, nullable=False, index=True)
    approved_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Cached governance snapshot from the linked LCID entry (Section 4
    # activation gate reads these; re-verified live at activation time).
    usage_rights_status: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    image_quality_status: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    # Real evidence links — never fabricated. annotation_ref points at
    # Annotation.ann_id when a clinical annotation/Ground Truth record backs
    # this image; digital_twin_id reuses lcid_service's identity string.
    annotation_ref: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    digital_twin_id: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)

    # Cached storage-integrity fields (Section 9). Re-verified, not merely
    # trusted, at every comparison access — see
    # baseline_image_library_service.load_and_verify_baseline_bytes().
    image_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    retained_image_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_link_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    superseded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)


class BaselineImageReview(Base):
    """A single authorized review decision on a `BaselineImageLink`
    (Section 5). Multiple reviews may exist per link (resubmission after
    rejection); the link's own `lifecycle_status` always reflects the
    latest decision, mirroring the annotation-lifecycle pattern of
    "current state on the row, full history in a companion table."
    """

    __tablename__ = "baseline_image_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    baseline_image_link_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    decision: Mapped[str] = mapped_column(String(20), default="", nullable=False, index=True)  # approve/reject
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)

    source_verification: Mapped[str] = mapped_column(Text, default="", nullable=False)
    anatomy_compatibility_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_quality_assessment: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    review_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BaselineSet(Base):
    """A governed grouping of compatible `BaselineImageLink` rows for one
    manufacturer/model + anatomy zone + view/orientation protocol +
    version (Section 6) — "multiple known-good images instead of relying
    on one perfect reference image."
    """

    __tablename__ = "baseline_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    manufacturer: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    instrument_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    anatomy_zone: Mapped[str] = mapped_column(String(60), default="", nullable=False, index=True)
    view_protocol: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    orientation_protocol: Mapped[str] = mapped_column(String(60), default="", nullable=False)

    version: Mapped[str] = mapped_column(String(40), default="1.0", nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(20), default=STATE_DRAFT, nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    limitations: Mapped[str] = mapped_column(Text, default="", nullable=False)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_set_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BaselineSetMember(Base):
    """Association row: one `BaselineImageLink` belongs to one `BaselineSet`.
    A real relational join table rather than a JSON id-list column, so
    membership can be queried/indexed like any other governed relationship.
    """

    __tablename__ = "baseline_set_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    baseline_set_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    baseline_image_link_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )


class BaselineComparisonAccessLog(Base):
    """Section 9/14 — every time a baseline image's bytes are loaded for a
    comparison (or the load fails hash verification), a real, queryable row
    is written here in addition to the hash-chained
    `record_enterprise_audit_event` call, so "comparison access" and "hash
    verification failure" can be reported without parsing audit-log
    `details` JSON. Complements, does not replace, the audit trail.
    """

    __tablename__ = "baseline_comparison_access_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    baseline_image_link_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    accessed_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    outcome: Mapped[str] = mapped_column(String(30), default="", nullable=False, index=True)  # verified / hash_mismatch / not_found
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    compatibility_status: Mapped[str] = mapped_column(String(40), default="", nullable=False)
