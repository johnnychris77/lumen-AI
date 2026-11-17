"""Stage 6C — governed real-image acquisition workflow (research-only).

A controlled entry point for importing ALREADY-AUTHORIZED research images through the
existing Project Canvas / LCID governance. It does not create a new dataset registry;
it gates on record-backed authorization (Stage 6C `scientific_authorization`) and the
per-image acquisition contract (`cohort_readiness`), then produces a data-quality
report. It never ingests unauthorized data, never fabricates or relabels images, and
research-only specimens never return to clinical use.

In this environment no authorized real cohort exists, so acquisition is reported
BLOCKED; the function is the ready integration point for when authorized data arrives.
"""
from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from research.lens_vision.cohort_readiness import (
    MODALITIES,
    generate_cohort_readiness_report,
    validate_image_readiness,
)
from research.lens_vision.scientific_authorization import (
    ScientificAuthorizationError,
    verify_data_authorization,
)

# Required specimen categories for the feasibility cohort (research mapping).
REQUIRED_CATEGORIES = (
    "verified_clean", "documented_corrosion", "measured_pitting",
    "confirmed_or_simulant_residue", "benign_confounder", "borescope_lumen",
)


class AcquisitionBlockedError(PermissionError):
    """Acquisition cannot proceed — authorization or required evidence is missing."""


def _ingest_one(db, img: dict, *, tenant_id: str) -> dict:
    """Smallest authorized hand-off of ONE image's bytes to the existing
    image-retention ingestion service. Verifies the bytes' SHA-256 against the
    registered hash before handing off; never creates a new store or bypasses access
    controls. Returns a per-image ingestion result."""
    from app.services.image_retention_service import retain_image  # noqa: PLC0415

    data = img.get("image_bytes")
    registered = str(img.get("image_sha256") or "").strip()
    if not isinstance(data, (bytes, bytearray)) or not data:
        return {"image_id": img.get("image_id"), "imported": False, "reason": "no_bytes_present"}
    actual = hashlib.sha256(bytes(data)).hexdigest()
    if not registered or actual != registered:
        return {"image_id": img.get("image_id"), "imported": False, "reason": "hash_mismatch"}
    retained = retain_image(
        db, data=bytes(data), tenant_id=tenant_id,
        instrument_type=str(img.get("instrument_id") or "research_instrument"),
        content_type=str(img.get("content_type") or ""), source="research_acquisition",
        uploaded_by="research-system", consent=True,
    )
    if retained is None:
        return {"image_id": img.get("image_id"), "imported": False, "reason": "retention_disabled_or_no_consent"}
    return {"image_id": img.get("image_id"), "imported": True,
            "retained_image_id": getattr(retained, "id", None),
            "stored_sha256": getattr(retained, "sha256", None)}


def acquire_research_cohort(
    db: Session, manifest: list[dict], *, tenant_id: str, dataset_id: str,
    auth=None, import_images: bool = False, min_cohort_sizes: dict | None = None,
    statistical_reviewer_signoff: dict | None = None, scientific_checkpoint_approved: bool = False,
) -> dict:
    """Validate, authorize and (optionally) INGEST an authorized research cohort.

    Fail-closed: dataset-specific institutional + research-use authorization is resolved
    against records FIRST (`verify_data_authorization`); without it nothing is imported
    and ``BLOCKED_ACQUISITION`` is returned. With authorization and ``import_images``,
    each contract-valid image whose supplied bytes match its registered SHA-256 is
    handed to the existing ``image_retention_service`` (no new store, no bypass), and the
    ACTUAL imported count + resolved ``RetainedImage`` storage ids are recorded. Images
    with no bytes are reported ``imported=0`` honestly.
    """
    if not isinstance(manifest, list):
        raise AcquisitionBlockedError("Manifest must be a list of image records.")

    # 1) Record-backed, dataset-specific authorization.
    try:
        verify_data_authorization(db, tenant_id=tenant_id, dataset_id=dataset_id, auth=auth)
        authorization = "resolved"
    except ScientificAuthorizationError as exc:
        return {
            "schema": "lumenai.stage6d.acquisition.v2",
            "status": "BLOCKED_ACQUISITION",
            "authorization": f"BLOCKED: {exc}",
            "n_images": len(manifest),
            "imported": 0,
            "note": "No images imported — dataset-specific institutional/research-use authorization is not resolved.",
        }

    # 2) Per-image acquisition-contract validation + data quality.
    per_image = [validate_image_readiness(img) for img in manifest]
    categories_present = {str(i.get("specimen_category") or "").strip() for i in manifest}
    missing_categories = [c for c in REQUIRED_CATEGORIES if c not in categories_present]
    readiness = generate_cohort_readiness_report(
        manifest, min_cohort_sizes=min_cohort_sizes,
        scientific_checkpoint_approved=scientific_checkpoint_approved,
        statistical_reviewer_signoff=statistical_reviewer_signoff,
    )
    n_ready = sum(1 for r in per_image if r["ready"])

    # 3) Optional smallest authorized ingestion hand-off (contract-valid images only).
    ingestion: list[dict] = []
    if import_images:
        for img, r in zip(manifest, per_image):
            if r["ready"]:
                ingestion.append(_ingest_one(db, img, tenant_id=tenant_id))
    imported = sum(1 for x in ingestion if x.get("imported"))
    storage_ids = [x["retained_image_id"] for x in ingestion if x.get("imported")]

    return {
        "schema": "lumenai.stage6d.acquisition.v2",
        "status": "AUTHORIZED",
        "authorization": authorization,
        "n_images": len(manifest),
        "n_contract_valid": n_ready,
        "missing_specimen_categories": missing_categories,
        "modalities_present": sorted({r["modality"] for r in per_image if r["modality"] in MODALITIES}),
        "cohort_readiness": readiness,
        "imported": imported,
        "resolved_storage_identities": storage_ids,
        "ingestion": ingestion,
        "note": "Authorization resolved; contract-valid, authorized, hash-verified images are handed "
                "to the existing image-retention ingestion (no new store). Research-only specimens "
                "must never return to clinical use.",
    }
