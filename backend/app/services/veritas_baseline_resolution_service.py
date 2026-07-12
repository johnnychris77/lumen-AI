"""Project Veritas, Section 2: Baseline Resolution Hierarchy.

Wraps the real, already-built `baseline_comparison_scoring_service.
resolve_baseline` (manufacturer -> vendor -> hospital priority across
`BaselineLibraryEntry` and `EnterpriseVendorBaselineSubscription`) rather
than re-implementing resolution. Neither real baseline table tracks
anatomy_zone -- `anatomy_zone` here is the caller's requested zone, carried
through for display/audit only, never used as a fabricated filter the real
tables can't actually support.

Never silently substitutes an unapproved baseline: `resolve_baseline`
already only returns approved entries; when nothing approved is found this
returns `SUPERVISOR_REVIEW_REQUIRED` with the brief's exact message.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.veritas_evidence import (
    BASELINE_TIER_MANUFACTURER,
    BASELINE_TIER_NONE,
    BASELINE_TIER_ORGANIZATION,
    BASELINE_TIER_VENDOR,
    NO_APPROVED_BASELINE_MESSAGE,
    RESOLUTION_STATUS_RESOLVED,
    RESOLUTION_STATUS_SUPERVISOR_REVIEW_REQUIRED,
    VeritasBaselineResolution,
)
from app.services.baseline_comparison_scoring_service import _resolve_from_library, _resolve_from_uploaded
from app.services.instrument_anatomy import resolve_family

_SOURCE_TO_TIER = {
    "manufacturer": BASELINE_TIER_MANUFACTURER,
    "vendor": BASELINE_TIER_VENDOR,
    "hospital": BASELINE_TIER_ORGANIZATION,
}


def _enrich_from_library(db: Session, entry_id: int) -> dict:
    from app.models.baseline_library import BaselineLibraryEntry
    row = db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.id == entry_id).first()
    if row is None:
        return {}
    return {
        "manufacturer": row.manufacturer_name or "", "model": row.model_name or "",
        "approval_status": row.approval_status or "", "reviewer": row.approved_by or "",
        "image_count": row.contributing_facilities or 0,
    }


def _enrich_from_uploaded(db: Session, entry_id: int) -> dict:
    from app.models.enterprise_quality import EnterpriseVendorBaselineSubscription as Sub
    row = db.query(Sub).filter(Sub.id == entry_id).first()
    if row is None:
        return {}
    return {
        "manufacturer": row.vendor_name or "", "model": row.model_number or "",
        "approval_status": row.approval_status or row.baseline_status or "", "reviewer": row.approved_by or "",
        "image_count": 0,
    }


def resolve_governed_baseline(
    db: Session, tenant_id: str, instrument_type: str, *, instrument_identity: str = "", anatomy_zone: str = "",
) -> VeritasBaselineResolution:
    """Section 2: resolve, enrich, and persist an audit row for one baseline
    resolution. Tries the network library first, then uploaded/approved
    vendor subscriptions -- mirrors `resolve_baseline`'s own order, but keeps
    track of *which* real table matched (that function doesn't expose it)."""
    instrument_family = resolve_family(instrument_type) if instrument_type else ""

    library_hit = _resolve_from_library(db, instrument_type) if instrument_type else None
    if library_hit is not None:
        enrichment = _enrich_from_library(db, library_hit["baseline_entry_id"])
        source_type = "baseline_library"
        hit = library_hit
    else:
        uploaded_hit = _resolve_from_uploaded(db, instrument_type) if instrument_type else None
        if uploaded_hit is not None:
            enrichment = _enrich_from_uploaded(db, uploaded_hit["baseline_entry_id"])
            source_type = "enterprise_vendor_subscription"
            hit = uploaded_hit
        else:
            hit = None
            enrichment = {}
            source_type = ""

    if hit is None:
        row = VeritasBaselineResolution(
            tenant_id=tenant_id, instrument_identity=instrument_identity, instrument_type=instrument_type,
            instrument_family=instrument_family, anatomy_zone=anatomy_zone,
            resolution_status=RESOLUTION_STATUS_SUPERVISOR_REVIEW_REQUIRED,
            baseline_tier=BASELINE_TIER_NONE, confidence="low",
            resolution_reason="No approved baseline matched this instrument type in either real baseline source.",
            message=NO_APPROVED_BASELINE_MESSAGE,
        )
    else:
        tier = _SOURCE_TO_TIER.get(hit["baseline_source"], BASELINE_TIER_NONE)
        row = VeritasBaselineResolution(
            tenant_id=tenant_id, instrument_identity=instrument_identity, instrument_type=instrument_type,
            instrument_family=instrument_family, anatomy_zone=anatomy_zone,
            resolution_status=RESOLUTION_STATUS_RESOLVED,
            baseline_source_type=source_type, baseline_source_id=hit["baseline_entry_id"], baseline_tier=tier,
            baseline_version=hit.get("baseline_version") or "", approval_status=enrichment.get("approval_status", ""),
            manufacturer=enrichment.get("manufacturer", ""), model=enrichment.get("model", ""),
            image_count=enrichment.get("image_count", 0), reviewer=enrichment.get("reviewer", ""),
            confidence="high" if tier == BASELINE_TIER_MANUFACTURER else "moderate",
            resolution_reason=f"Resolved from {source_type} at tier '{tier}'.",
            message="",
        )

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: VeritasBaselineResolution) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "instrument_identity": row.instrument_identity,
        "instrument_type": row.instrument_type,
        "instrument_family": row.instrument_family,
        "anatomy_zone": row.anatomy_zone,
        "resolution_status": row.resolution_status,
        "baseline_source_type": row.baseline_source_type,
        "baseline_source_id": row.baseline_source_id,
        "baseline_tier": row.baseline_tier,
        "baseline_version": row.baseline_version,
        "approval_status": row.approval_status,
        "manufacturer": row.manufacturer,
        "model": row.model,
        "image_count": row.image_count,
        "reviewer": row.reviewer,
        "confidence": row.confidence,
        "resolution_reason": row.resolution_reason,
        "message": row.message,
        "human_review_required": row.human_review_required,
    }
