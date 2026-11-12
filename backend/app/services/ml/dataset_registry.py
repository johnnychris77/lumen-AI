"""Dataset Registry & AI Model Development Foundation — Sections 1 & 2.

Governed, per-image dataset registration and immutable dataset versioning.
References real artifacts (``RetainedImage``) by ID rather than duplicating
image bytes or metadata already tracked elsewhere (see the module docstring
in ``app.models.dataset_governance`` for the full collision-avoidance
rationale).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.dataset_governance import (
    PROVENANCE_APPROVAL_NOT_REQUIRED,
    PROVENANCE_APPROVAL_PENDING,
    RESEARCH_PROVENANCE_CLASSES,
    DatasetRegistryEntry,
    DatasetVersion,
    UNLABELED,
)
from app.models.retained_image import RetainedImage
from app.services.ml.lcid_service import generate_lcid, instrument_digital_twin_id, resolve_baseline_id
from app.services.ml.provenance_governance import normalize_provenance_class

# Required, non-empty on every registered image (Section 1's field list,
# minus the ones populated later in the lifecycle — current_label/reviewer/
# split_assignment start empty and are filled in as review/splitting happen).
REQUIRED_STRING_FIELDS = (
    "instrument_family", "manufacturer", "facility", "operator",
    "capture_device", "image_resolution",
)


class DatasetVersionNotFound(ValueError):
    pass


class DatasetVersionFrozenError(ValueError):
    pass


class MetadataValidationError(ValueError):
    def __init__(self, missing_fields: list[str]):
        self.missing_fields = missing_fields
        super().__init__(f"Missing required dataset metadata: {', '.join(missing_fields)}")


class DuplicateImageError(ValueError):
    def __init__(self, image_sha256: str, existing_entry_id: int):
        self.image_sha256 = image_sha256
        self.existing_entry_id = existing_entry_id
        super().__init__(
            f"Image with sha256={image_sha256} is already registered as dataset entry {existing_entry_id}."
        )


class RetainedImageNotFoundError(ValueError):
    """The referenced RetainedImage does not exist for this tenant."""

    def __init__(self, retained_image_id: int):
        self.retained_image_id = retained_image_id
        super().__init__(f"Retained image {retained_image_id} not found for this tenant.")


class CrossTenantImageError(ValueError):
    """The referenced RetainedImage exists but belongs to a different tenant.

    Raised instead of silently reading another tenant's image, enforcing the
    tenant-data-isolation guarantee. Callers map this to a 404 so existence
    under another tenant is never confirmed to the requester.
    """

    def __init__(self, retained_image_id: int):
        self.retained_image_id = retained_image_id
        super().__init__(f"Retained image {retained_image_id} not found for this tenant.")


class ImageIdentityMismatchError(ValueError):
    """The declared ``image_sha256`` does not match the retained image's stored
    content hash — the registration is describing different bytes than the
    retained image it points at (identity spoofing / wrong reference)."""

    def __init__(self, retained_image_id: int, expected_sha256: str, declared_sha256: str):
        self.retained_image_id = retained_image_id
        self.expected_sha256 = expected_sha256
        self.declared_sha256 = declared_sha256
        super().__init__(
            f"Declared image_sha256 does not match the retained image's recorded content hash "
            f"for retained image {retained_image_id}."
        )


def verify_retained_image_for_registration(
    db: Session, *, tenant_id: str, retained_image_id: int, image_sha256: str
) -> RetainedImage:
    """Fail-closed ownership + identity check for a dataset registration that
    references a ``RetainedImage``.

    Enforces, against the authenticated tenant context:
      * ownership — the retained image exists AND belongs to ``tenant_id`` (a
        tenant can never register another tenant's raw image into its dataset);
      * identity / SHA-256 consistency — the declared ``image_sha256`` matches
        the retained image's recorded content hash, so an entry cannot claim to
        be bytes other than the ones actually retained.

    Call this from the authenticated registration entrypoints (routes). It is
    deliberately NOT embedded in ``register_image`` itself so lower-level,
    already-trusted callers/fixtures that pass opaque identifiers are
    unaffected; the security boundary is the tenant-authenticated request.
    """
    retained = (
        db.query(RetainedImage)
        .filter(RetainedImage.id == retained_image_id)
        .first()
    )
    if retained is None:
        raise RetainedImageNotFoundError(retained_image_id)
    if retained.tenant_id != tenant_id:
        raise CrossTenantImageError(retained_image_id)
    # Identity: the declared hash must match the retained image's recorded hash
    # when the retained image carries one (fail-closed on a real mismatch).
    if retained.sha256 and retained.sha256 != image_sha256:
        raise ImageIdentityMismatchError(retained_image_id, retained.sha256, image_sha256)
    return retained


def create_dataset_version(
    db: Session, *, tenant_id: str, version_label: str, description: str = "", supersedes_id: int | None = None,
) -> DatasetVersion:
    existing = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.tenant_id == tenant_id, DatasetVersion.version_label == version_label)
        .first()
    )
    if existing is not None:
        return existing
    row = DatasetVersion(
        tenant_id=tenant_id, version_label=version_label, description=description, supersedes_id=supersedes_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def freeze_dataset_version(db: Session, *, tenant_id: str, dataset_version_id: int, frozen_by: str) -> DatasetVersion:
    """Make a dataset version immutable (Section 2). Once frozen, no image
    may be registered into it and its metadata is never edited again — a
    correction requires a new version referencing this one via
    ``supersedes_id``."""
    version = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.id == dataset_version_id, DatasetVersion.tenant_id == tenant_id)
        .first()
    )
    if version is None:
        raise DatasetVersionNotFound(f"Dataset version {dataset_version_id} not found.")
    if version.frozen:
        return version

    count = (
        db.query(DatasetRegistryEntry)
        .filter(DatasetRegistryEntry.dataset_version_id == dataset_version_id)
        .count()
    )
    version.frozen = True
    version.frozen_at = datetime.now(timezone.utc)
    version.frozen_by = frozen_by
    version.image_count_at_freeze = count
    db.commit()
    db.refresh(version)
    return version


def validate_metadata(metadata: dict) -> list[str]:
    """Returns the list of required fields that are missing/blank. Empty
    list means the metadata is complete enough to register."""
    missing = []
    for field in REQUIRED_STRING_FIELDS:
        value = metadata.get(field)
        if not value or not str(value).strip():
            missing.append(field)
    return missing


def find_duplicate(db: Session, *, tenant_id: str, image_sha256: str) -> DatasetRegistryEntry | None:
    return (
        db.query(DatasetRegistryEntry)
        .filter(DatasetRegistryEntry.tenant_id == tenant_id, DatasetRegistryEntry.image_sha256 == image_sha256)
        .first()
    )


def register_image(
    db: Session,
    *,
    tenant_id: str,
    dataset_version_id: int,
    retained_image_id: int,
    image_sha256: str,
    inspection_id: int | None = None,
    instrument_family: str = "",
    instrument_model: str = "",
    manufacturer: str = "",
    anatomy_zone: str = "",
    inspection_date: datetime | None = None,
    capture_device: str = "",
    image_resolution: str = "",
    lighting_condition: str = "unknown",
    image_quality: str = "",
    facility: str = "",
    operator: str = "",
    usage_rights: str = "",
    phi_verification: str = "pending",
    retention_status: str = "active",
    instrument_barcode: str = "",
    instrument_udi: str = "",
    digital_twin_id: str = "",
    baseline_id: int | None = None,
    instrument_id: str = "",
    catalog_number: str = "",
    inspection_region: str = "",
    image_type: str = "",
    reviewer_notes: str = "",
    data_provenance_class: str = "",
    provenance_source_id: str = "",
    provenance_source_version: str = "",
    provenance_source_institution: str = "",
    provenance_rights_evidence_ref: str = "",
    provenance_specimen_id: str = "",
) -> DatasetRegistryEntry:
    """Register one image into the governed dataset registry (Section 1).

    Enforces: the target dataset version exists and is not frozen (Section
    2's immutability), all required metadata is present (Section 1), and the
    image is not already registered for this tenant (duplicate detection,
    Section 6/14).
    """
    version = (
        db.query(DatasetVersion)
        .filter(DatasetVersion.id == dataset_version_id, DatasetVersion.tenant_id == tenant_id)
        .first()
    )
    if version is None:
        raise DatasetVersionNotFound(f"Dataset version {dataset_version_id} not found.")
    if version.frozen:
        raise DatasetVersionFrozenError(
            f"Dataset version '{version.version_label}' is frozen; register into a new version instead."
        )

    metadata = {
        "instrument_family": instrument_family, "manufacturer": manufacturer, "facility": facility,
        "operator": operator, "capture_device": capture_device, "image_resolution": image_resolution,
    }
    missing = validate_metadata(metadata)
    if missing:
        raise MetadataValidationError(missing)

    duplicate = find_duplicate(db, tenant_id=tenant_id, image_sha256=image_sha256)
    if duplicate is not None:
        raise DuplicateImageError(image_sha256, duplicate.id)

    lcid = generate_lcid(db)
    resolved_twin_id = digital_twin_id or instrument_digital_twin_id(
        instrument_barcode=instrument_barcode, instrument_udi=instrument_udi,
        instrument_type=instrument_family, inspection_id=inspection_id,
    )
    resolved_baseline_id = baseline_id if baseline_id is not None else resolve_baseline_id(
        db, instrument_type=instrument_family, manufacturer=manufacturer,
    )

    # Stage 4 — structured provenance recorded at ingestion. A declared class is
    # normalised (unknown/blank → legacy_unverified, fail-closed). Ingestion can
    # DECLARE a class but can never APPROVE it: real_clinical/unknown stay
    # "pending" and only an authorized governance role may approve them later via
    # provenance_governance.set_provenance_classification. Research classes need
    # no clinical approval and are marked "not_required" (still never clinical).
    _prov_class = normalize_provenance_class(data_provenance_class)
    _prov_approval = (
        PROVENANCE_APPROVAL_NOT_REQUIRED
        if _prov_class in RESEARCH_PROVENANCE_CLASSES
        else PROVENANCE_APPROVAL_PENDING
    )

    row = DatasetRegistryEntry(
        lcid=lcid,
        data_provenance_class=_prov_class,
        provenance_source_id=provenance_source_id,
        provenance_source_version=provenance_source_version,
        provenance_source_institution=provenance_source_institution,
        provenance_rights_evidence_ref=provenance_rights_evidence_ref,
        provenance_specimen_id=provenance_specimen_id,
        provenance_approval_status=_prov_approval,
        digital_twin_id=resolved_twin_id,
        baseline_id=resolved_baseline_id,
        tenant_id=tenant_id,
        dataset_version_id=dataset_version_id,
        dataset_version_label=version.version_label,
        retained_image_id=retained_image_id,
        inspection_id=inspection_id,
        instrument_family=instrument_family,
        instrument_model=instrument_model,
        manufacturer=manufacturer,
        anatomy_zone=anatomy_zone,
        inspection_date=inspection_date,
        capture_device=capture_device,
        image_resolution=image_resolution,
        lighting_condition=lighting_condition,
        image_quality=image_quality,
        facility=facility,
        operator=operator,
        instrument_id=instrument_id,
        catalog_number=catalog_number,
        inspection_region=inspection_region,
        image_type=image_type,
        reviewer_notes=reviewer_notes,
        review_status=UNLABELED,
        usage_rights=usage_rights,
        phi_verification=phi_verification,
        training_eligibility=False,
        retention_status=retention_status,
        image_sha256=image_sha256,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_entries(db: Session, *, tenant_id: str, dataset_version_id: int | None = None) -> list[DatasetRegistryEntry]:
    q = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.tenant_id == tenant_id)
    if dataset_version_id is not None:
        q = q.filter(DatasetRegistryEntry.dataset_version_id == dataset_version_id)
    return q.order_by(DatasetRegistryEntry.id.asc()).all()
