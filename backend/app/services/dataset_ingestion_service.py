"""Project Canvas — Sections 2 & 4: Image Ingestion (single + bulk).

Composes two already-governed services rather than duplicating either:
`app.services.image_retention_service.retain_image` (EXIF-stripped,
consent-gated byte storage + row-level dedup) and
`app.services.ml.dataset_registry.register_image` (LCID assignment,
metadata validation, Digital Twin/baseline resolution). This module only
adds the ingestion-specific orchestration (accepted-type/size checks,
duplicate-vs-registered distinction, bulk partial-success reporting, CSV
metadata import) that neither of those services is responsible for.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.services.image_retention_service import retain_image, retention_enabled
from app.services.ml import dataset_registry

# Reuses the exact accepted-type/size policy already enforced by the
# pre-existing `/ml/images` upload route — never a second, looser policy.
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class IngestionDisabledError(ValueError):
    pass


class EmptyFileError(ValueError):
    pass


class UnsupportedFileTypeError(ValueError):
    pass


class FileTooLargeError(ValueError):
    pass


class ConsentRequiredError(ValueError):
    pass


class UsageRightsRequiredError(ValueError):
    pass


def ingest_image(
    db: Session,
    *,
    tenant_id: str,
    data: bytes,
    content_type: str,
    actor: str,
    consent: bool,
    dataset_version_id: int,
    usage_rights: str,
    **metadata_fields: Any,
) -> dict[str, Any]:
    """Ingest one image. Returns `{"duplicate": bool, "entry"/"existing_entry": ...}`
    — never silently overwrites an existing registration; a duplicate content
    hash that is already dataset-registered comes back as a clear warning,
    not a fabricated new registration."""
    if not retention_enabled():
        raise IngestionDisabledError(
            "Image retention is disabled for this deployment (RETAIN_INSPECTION_IMAGES). "
            "Dataset ingestion requires it to be enabled.",
        )
    if not data:
        raise EmptyFileError("The uploaded file is empty.")
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise UnsupportedFileTypeError(f"Unsupported file type '{content_type}'.")
    if len(data) > MAX_IMAGE_BYTES:
        raise FileTooLargeError(f"File exceeds the {MAX_IMAGE_BYTES} byte limit.")
    if not usage_rights.strip():
        raise UsageRightsRequiredError("A usage-rights status is required for every registered image.")

    retained = retain_image(
        db, data=data, tenant_id=tenant_id,
        instrument_type=metadata_fields.get("instrument_family", "unknown"),
        content_type=content_type, source="dataset_ingestion", uploaded_by=actor, consent=consent,
    )
    if retained is None:
        raise ConsentRequiredError("Consent is required to ingest a dataset image (pass consent=true).")

    already_registered = dataset_registry.find_duplicate(db, tenant_id=tenant_id, image_sha256=retained.sha256)
    if already_registered is not None:
        return {"duplicate": True, "existing_entry": already_registered, "retained_image_id": retained.id}

    entry = dataset_registry.register_image(
        db, tenant_id=tenant_id, dataset_version_id=dataset_version_id,
        retained_image_id=retained.id, image_sha256=retained.sha256,
        usage_rights=usage_rights, **metadata_fields,
    )
    return {"duplicate": False, "entry": entry, "retained_image_id": retained.id}


@dataclass
class BulkIngestRow:
    filename: str
    success: bool
    duplicate: bool = False
    error: str | None = None
    lcid: str | None = None
    entry_id: int | None = None


@dataclass
class BulkIngestResult:
    rows: list[BulkIngestRow] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.rows if r.success)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.rows if not r.success)

    @property
    def duplicate_count(self) -> int:
        return sum(1 for r in self.rows if r.duplicate)


def bulk_ingest(
    db: Session,
    *,
    tenant_id: str,
    actor: str,
    consent: bool,
    dataset_version_id: int,
    files: list[dict[str, Any]],
    shared_metadata: dict[str, Any] | None = None,
) -> BulkIngestResult:
    """Section 4 — batch registration. Each `files` entry is
    `{"filename": str, "data": bytes, "content_type": str, "metadata": {...}}`
    (per-image overrides merged over `shared_metadata`). A failure on one row
    is reported and the batch continues — partial success is the norm, never
    an all-or-nothing failure when safe partial completion is possible."""
    shared = shared_metadata or {}
    result = BulkIngestResult()

    for file_entry in files:
        filename = file_entry.get("filename", "unknown")
        merged_metadata = {**shared, **file_entry.get("metadata", {})}
        usage_rights = merged_metadata.pop("usage_rights", "")
        try:
            outcome = ingest_image(
                db, tenant_id=tenant_id, data=file_entry.get("data", b""),
                content_type=file_entry.get("content_type", ""), actor=actor, consent=consent,
                dataset_version_id=dataset_version_id, usage_rights=usage_rights, **merged_metadata,
            )
        except (
            IngestionDisabledError, EmptyFileError, UnsupportedFileTypeError, FileTooLargeError,
            ConsentRequiredError, UsageRightsRequiredError,
            dataset_registry.MetadataValidationError, dataset_registry.DuplicateImageError,
            dataset_registry.DatasetVersionNotFound, dataset_registry.DatasetVersionFrozenError,
        ) as exc:
            result.rows.append(BulkIngestRow(filename=filename, success=False, error=str(exc)))
            continue

        if outcome["duplicate"]:
            result.rows.append(BulkIngestRow(
                filename=filename, success=False, duplicate=True,
                error=f"Duplicate of dataset entry {outcome['existing_entry'].id} (LCID {outcome['existing_entry'].lcid}).",
                lcid=outcome["existing_entry"].lcid, entry_id=outcome["existing_entry"].id,
            ))
        else:
            entry = outcome["entry"]
            result.rows.append(BulkIngestRow(
                filename=filename, success=True, lcid=entry.lcid, entry_id=entry.id,
            ))

    return result


def parse_csv_metadata(csv_text: str) -> dict[str, dict[str, Any]]:
    """Section 4 — CSV metadata import. Expects a `filename` column plus any
    subset of the registration-form fields; returns a dict keyed by filename
    so the caller can merge each row as that file's metadata override.
    Unknown columns are preserved as-is (validated later by
    `dataset_registry.register_image`'s own required-field check) — never
    silently dropped."""
    reader = csv.DictReader(io.StringIO(csv_text))
    by_filename: dict[str, dict[str, Any]] = {}
    for row in reader:
        filename = row.get("filename", "").strip()
        if not filename:
            continue
        by_filename[filename] = {k: v for k, v in row.items() if k != "filename" and v}
    return by_filename
