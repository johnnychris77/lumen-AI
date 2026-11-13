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


def acquire_research_cohort(
    db: Session, manifest: list[dict], *, tenant_id: str, dataset_id: str, dataset_owner_email: str,
    min_cohort_sizes: dict | None = None, statistical_reviewer_signoff: dict | None = None,
    scientific_checkpoint_approved: bool = False,
) -> dict:
    """Validate and report readiness for importing an authorized research cohort.

    Fail-closed: institutional + research-use authorization is resolved against records
    FIRST (`verify_data_authorization`); without it, nothing is imported and
    ``AcquisitionBlockedError`` is raised. With authorization, each image is validated
    against the acquisition contract and a data-quality + readiness report is returned.
    This function ingests no bytes here; it is the governed hand-off point to Canvas/LCID.
    """
    if not isinstance(manifest, list):
        raise AcquisitionBlockedError("Manifest must be a list of image records.")

    # 1) Record-backed authorization (institutional authorization + live consent).
    try:
        verify_data_authorization(db, tenant_id=tenant_id, user_email=dataset_owner_email, dataset_id=dataset_id)
        authorization = "resolved"
    except ScientificAuthorizationError as exc:
        # Report blocked rather than importing anything.
        return {
            "schema": "lumenai.stage6c.acquisition.v1",
            "status": "BLOCKED_ACQUISITION",
            "authorization": f"BLOCKED: {exc}",
            "n_images": len(manifest),
            "imported": 0,
            "note": "No images imported — institutional/research-use authorization is not resolved.",
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
    return {
        "schema": "lumenai.stage6c.acquisition.v1",
        "status": "AUTHORIZED",
        "authorization": authorization,
        "n_images": len(manifest),
        "n_contract_valid": n_ready,
        "missing_specimen_categories": missing_categories,
        "modalities_present": sorted({r["modality"] for r in per_image if r["modality"] in MODALITIES}),
        "cohort_readiness": readiness,
        "imported": 0,
        "note": "Authorization resolved; per-image contract validated. Bytes are handed to "
                "Project Canvas/LCID ingestion only for contract-valid, authorized images. "
                "Research-only specimens must never return to clinical use.",
    }
