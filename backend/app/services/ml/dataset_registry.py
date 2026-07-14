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

from app.models.dataset_governance import DatasetRegistryEntry, DatasetVersion, UNLABELED

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

    row = DatasetRegistryEntry(
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
