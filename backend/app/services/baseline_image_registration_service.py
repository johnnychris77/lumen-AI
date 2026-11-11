"""Register an uploaded manufacturer/organization baseline *photograph* into the
governed Baseline Image Library so the inspection comparison engine can actually
use it.

This is the bridge that was missing: ``CreateManufacturerBaseline`` previously
called ``/api/baselines/upload-images`` which recorded only a SHA-256 — no bytes
were retained and no governed image link was created, so an "approved" baseline
had metadata but never a usable reference image.

The flow here reuses existing infrastructure end-to-end rather than duplicating
image storage:

  uploaded bytes
    -> ``image_retention_service.retain_reference_image`` (RetainedImage: the
       sole owner of bytes, EXIF-stripped, usage-rights-attested, dedup-aware)
    -> ``ml.dataset_registry.register_image`` (DatasetRegistryEntry: the
       LCID-registered governed image entity)
    -> ``baseline_image_library_service.link_lcid_image_to_baseline``
       (BaselineImageLink in DRAFT)
    -> ``submit_for_review`` (PENDING_REVIEW)

It deliberately stops at PENDING_REVIEW. Activation to ACTIVE stays a governed
human decision (review -> activate) through the existing Baseline Image Library
endpoints and its activation gate — an image is NEVER treated as ACTIVE merely
because the metadata baseline record was approved.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.baseline_image_library import (
    IMAGE_TYPE_MANUFACTURER_BASELINE,
    SOURCE_MANUFACTURER_REFERENCE,
)
from app.models.baseline_library import BaselineLibraryEntry
from app.services import baseline_image_library_service as bil
from app.services.image_retention_service import retain_reference_image
from app.services.ml import dataset_registry
from app.services.ml.image_quality import assess_image_bytes

# A manufacturer baseline reference image, when the uploader does not scope it to
# a specific anatomy zone / view, is documented as a whole-instrument overview.
# Inspections that likewise do not scope a zone/view default to the SAME tokens
# (see baseline_comparison_scoring_service), so resolution is an explicit match
# on equal documented fields — never a silent cross-zone/view match.
DEFAULT_ANATOMY_ZONE = "whole_instrument"
DEFAULT_INSPECTION_VIEW = "overview"

# Per-tenant dataset version that governed baseline reference images register
# into (kept distinct from inspection/training dataset versions).
BASELINE_DATASET_VERSION_LABEL = "baseline-reference-images"


class BaselineReferenceImageError(ValueError):
    """Raised when a baseline reference image cannot be governed-registered."""


def _nonfrozen_dataset_version(db: Session, *, tenant_id: str):
    """Return a writable (non-frozen) dataset version for baseline reference
    images. If the base version has been frozen through the governed
    dataset-registry workflow, roll onto a numbered successor so future uploads
    never fail with DatasetVersionFrozenError on a permanently frozen row."""
    label = BASELINE_DATASET_VERSION_LABEL
    for suffix in range(0, 1000):
        candidate_label = label if suffix == 0 else f"{label}-v{suffix + 1}"
        version = dataset_registry.create_dataset_version(
            db, tenant_id=tenant_id, version_label=candidate_label,
            description="Governed manufacturer/organization baseline reference images.",
        )
        if not version.frozen:
            return version
    raise BaselineReferenceImageError(
        "No writable baseline-reference dataset version is available (all are frozen)."
    )


def _entry_or_404(db: Session, baseline_library_entry_id: int) -> BaselineLibraryEntry:
    entry = (
        db.query(BaselineLibraryEntry)
        .filter(BaselineLibraryEntry.id == baseline_library_entry_id)
        .first()
    )
    if entry is None:
        raise BaselineReferenceImageError(
            f"No approved baseline record {baseline_library_entry_id} to attach a reference image to."
        )
    return entry


def register_manufacturer_reference_image(
    db: Session,
    *,
    tenant_id: str,
    baseline_library_entry_id: int,
    image_bytes: bytes,
    content_type: str,
    uploaded_by: str,
    source_organization: str,
    source_reference: str,
    usage_rights_attested: bool,
    no_phi_attested: bool,
    anatomy_zone: str = "",
    inspection_view: str = "",
    orientation: str = "",
    facility_id: str = "",
) -> dict[str, Any]:
    """Register (retain + LCID-register + link + submit-for-review) a baseline
    reference image for an existing approved baseline record. Returns a dict with
    the retained-image id, LCID entry id/lcid, and the DRAFT/PENDING link.

    The caller (route) enforces RBAC. This function enforces the governance that
    must hold regardless of caller: real usage-rights + source provenance for a
    manufacturer-reference claim, real retained bytes, a real quality grade, and
    a governed lifecycle that begins at PENDING_REVIEW (never ACTIVE)."""
    entry = _entry_or_404(db, baseline_library_entry_id)

    if not usage_rights_attested:
        raise BaselineReferenceImageError(
            "Usage rights must be attested to store a manufacturer baseline reference image."
        )
    if not no_phi_attested:
        raise BaselineReferenceImageError(
            "The uploader must attest the reference image contains no PHI (manufacturer reference instrument only)."
        )
    if not (source_organization.strip() and source_reference.strip()):
        # Mirrors the service-layer provenance gate for SOURCE_MANUFACTURER_REFERENCE —
        # fail early with a clear message before any bytes are stored.
        raise BaselineReferenceImageError(
            "A manufacturer baseline reference image requires a source organization and a real source reference "
            "(document id, PO/correspondence reference, or vendor-portal submission id)."
        )

    quality = assess_image_bytes(image_bytes)
    if not quality.get("decodable"):
        raise BaselineReferenceImageError(
            "The uploaded baseline reference image could not be decoded as an image."
        )

    # 1) Retain the actual bytes (governed by the usage-rights attestation).
    retained = retain_reference_image(
        db, data=image_bytes, tenant_id=tenant_id,
        instrument_type=entry.instrument_category, content_type=content_type,
        uploaded_by=uploaded_by, usage_rights_attested=usage_rights_attested,
    )

    zone = (anatomy_zone or "").strip() or DEFAULT_ANATOMY_ZONE
    view = (inspection_view or "").strip() or DEFAULT_INSPECTION_VIEW

    # 2) LCID-register the retained image (idempotent on the image hash: a
    #    re-upload of the same bytes reuses the existing governed entry).
    existing_lcid = dataset_registry.find_duplicate(db, tenant_id=tenant_id, image_sha256=retained.sha256)
    if existing_lcid is not None:
        # The exact bytes are already LCID-registered. Only reuse the entry when
        # its governed identity matches THIS baseline — otherwise linking it to
        # this baseline would copy a different instrument's manufacturer/model
        # and produce a mismatched governed link.
        if (
            (existing_lcid.instrument_family or "") != entry.instrument_category
            or (existing_lcid.manufacturer or "").strip().lower() != (entry.manufacturer_name or "").strip().lower()
        ):
            raise BaselineReferenceImageError(
                "These exact image bytes are already registered under a different instrument identity "
                f"(family={existing_lcid.instrument_family!r}, manufacturer={existing_lcid.manufacturer!r}); "
                "use a distinct reference image for this baseline."
            )
        lcid_entry = existing_lcid
    else:
        version = _nonfrozen_dataset_version(db, tenant_id=tenant_id)
        lcid_entry = dataset_registry.register_image(
            db, tenant_id=tenant_id, dataset_version_id=version.id,
            retained_image_id=retained.id, image_sha256=retained.sha256,
            instrument_family=entry.instrument_category,
            instrument_model=entry.model_name or entry.manufacturer_name,
            manufacturer=entry.manufacturer_name,
            anatomy_zone=zone,
            inspection_date=datetime.now(timezone.utc),
            capture_device="baseline_reference_upload",
            image_resolution=f"{quality.get('width', 0)}x{quality.get('height', 0)}",
            image_quality=quality.get("overall_quality", ""),
            facility=tenant_id, operator=uploaded_by,
            # Rights + PHI are attested by the uploader for a manufacturer
            # reference instrument (not patient-derived); recorded honestly, not
            # auto-cleared on the metadata approval.
            usage_rights="manufacturer_reference_rights_attested",
            phi_verification="verified",
            catalog_number=entry.model_name or "",
            image_type=IMAGE_TYPE_MANUFACTURER_BASELINE,
            reviewer_notes=f"Baseline reference image for baseline_library entry {entry.id}.",
            baseline_id=entry.id,
        )

    # 3) Link into the governed Baseline Image Library in DRAFT.
    link = bil.link_lcid_image_to_baseline(
        db, tenant_id=tenant_id, facility_id=facility_id,
        baseline_library_entry_id=entry.id, lcid_image_id=lcid_entry.id,
        anatomy_zone=zone, inspection_view=view, orientation=orientation,
        image_type=IMAGE_TYPE_MANUFACTURER_BASELINE, source_type=SOURCE_MANUFACTURER_REFERENCE,
        source_organization=source_organization.strip(), source_reference=source_reference.strip(),
        created_by=uploaded_by,
    )
    # 4) Enter the governed review queue (still NOT active).
    link = bil.submit_for_review(db, link=link, actor=uploaded_by)

    return {
        "retained_image_id": retained.id,
        "lcid_image_id": lcid_entry.id,
        "lcid": lcid_entry.lcid,
        "image_sha256": retained.sha256,
        "image_quality": quality.get("overall_quality", ""),
        "link": link,
        "lifecycle_status": link.lifecycle_status,
        "duplicate_bytes": bool(getattr(retained, "_lumenai_dedup_hit", False)),
    }
