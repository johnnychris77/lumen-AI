"""Project Atlas Sprint 1 — compatibility contract + resolution hierarchy.

Never computes or returns a numeric similarity itself (Section 7: "do not
generate numeric similarity when compatibility fails") — this module only
decides WHETHER a candidate inspection image and a baseline image are
comparable at all, and WHICH baseline image best resolves for a given
instrument context. The actual pixel comparison, once compatibility is
established, is `app.services.ml.image_similarity_service` (Project
Lens) — unchanged, reused as-is, never reimplemented here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.baseline_image_library import (
    BASELINE_NOT_ACTIVE,
    COMPATIBLE,
    INCOMPATIBLE_ANATOMY_ZONE,
    INCOMPATIBLE_INSTRUMENT,
    INCOMPATIBLE_ORIENTATION,
    INCOMPATIBLE_VIEW,
    INSUFFICIENT_IMAGE_QUALITY,
    NO_APPROVED_BASELINE,
    RESOLUTION_DIGITAL_TWIN_EXACT,
    RESOLUTION_GOVERNED_CONSENSUS,
    RESOLUTION_MANUFACTURER_MODEL_ZONE,
    RESOLUTION_NONE,
    RESOLUTION_ORGANIZATION_FAMILY_ZONE,
    SOURCE_GOVERNED_CONSENSUS_REFERENCE,
    SOURCE_NEW_INSTRUMENT_REFERENCE,
    SOURCE_ORGANIZATION_KNOWN_GOOD,
    SOURCE_POST_REPAIR_REFERENCE,
    STATE_ACTIVE,
    BaselineImageLink,
)
from app.models.dataset_governance import QUALITY_POOR, QUALITY_REJECT
from app.services.ml.lcid_service import is_untracked_twin

_ORGANIZATION_SOURCE_TYPES = {
    SOURCE_ORGANIZATION_KNOWN_GOOD, SOURCE_NEW_INSTRUMENT_REFERENCE, SOURCE_POST_REPAIR_REFERENCE,
}


@dataclass
class CandidateContext:
    tenant_id: str
    instrument_family: str = ""
    manufacturer: str = ""
    model_name: str = ""
    anatomy_zone: str = ""
    inspection_view: str = ""
    orientation: str = ""
    image_quality_status: str = ""
    digital_twin_id: str = ""


def check_compatibility(*, candidate: CandidateContext, baseline_link: BaselineImageLink | None) -> str:
    """Section 7 — the compatibility contract. Evaluated in the order the
    mission lists (organization scope, instrument, anatomy zone, view,
    orientation, image quality, active status)."""
    if baseline_link is None:
        return NO_APPROVED_BASELINE
    if candidate.tenant_id != baseline_link.tenant_id:
        # Different organization scope with no authorized shared source —
        # treated the same as "nothing approved for you," never as a
        # different, cross-tenant-specific code (tenant isolation must
        # never leak a "this exists but isn't yours" signal).
        return NO_APPROVED_BASELINE
    if baseline_link.lifecycle_status != STATE_ACTIVE:
        return BASELINE_NOT_ACTIVE
    if candidate.manufacturer and baseline_link.manufacturer and candidate.manufacturer != baseline_link.manufacturer:
        return INCOMPATIBLE_INSTRUMENT
    if candidate.instrument_family and baseline_link.instrument_family and candidate.instrument_family != baseline_link.instrument_family:
        return INCOMPATIBLE_INSTRUMENT
    if candidate.anatomy_zone and baseline_link.anatomy_zone and candidate.anatomy_zone != baseline_link.anatomy_zone:
        return INCOMPATIBLE_ANATOMY_ZONE
    if candidate.inspection_view and baseline_link.inspection_view and candidate.inspection_view != baseline_link.inspection_view:
        return INCOMPATIBLE_VIEW
    if candidate.orientation and baseline_link.orientation and candidate.orientation != baseline_link.orientation:
        return INCOMPATIBLE_ORIENTATION
    if candidate.image_quality_status in (QUALITY_REJECT, QUALITY_POOR):
        return INSUFFICIENT_IMAGE_QUALITY
    return COMPATIBLE


@dataclass
class ResolutionResult:
    baseline_image_link_id: int | None
    baseline_set_id: int | None
    resolution_scope: str
    resolution_reason: str
    version: str | None = None
    limitations: list[str] = field(default_factory=list)


def _active_links_query(db: Session, tenant_id: str):
    return db.query(BaselineImageLink).filter(
        BaselineImageLink.tenant_id == tenant_id, BaselineImageLink.lifecycle_status == STATE_ACTIVE,
    )


def resolve_baseline_image(
    db: Session, *, candidate: CandidateContext, require_exact: bool = False,
) -> ResolutionResult:
    """Section 8 — resolve the best ACTIVE baseline image for one
    candidate inspection context, following the mandated hierarchy.
    ``require_exact=True`` mirrors an organization policy that forbids
    falling back to a broader baseline: only level 1 is attempted, and a
    miss returns NO_APPROVED_BASELINE with an honest reason rather than
    silently widening scope."""

    # 1. Exact physical-instrument Digital Twin baseline.
    if candidate.digital_twin_id and not is_untracked_twin(candidate.digital_twin_id):
        row = (
            _active_links_query(db, candidate.tenant_id)
            .filter(BaselineImageLink.digital_twin_id == candidate.digital_twin_id)
            .order_by(BaselineImageLink.approved_at.desc())
            .first()
        )
        if row is not None:
            return ResolutionResult(
                baseline_image_link_id=row.id, baseline_set_id=None,
                resolution_scope=RESOLUTION_DIGITAL_TWIN_EXACT,
                resolution_reason="Exact approved baseline image exists for this physical instrument's Digital Twin identity.",
                version=row.baseline_version,
            )

    if require_exact:
        return ResolutionResult(
            baseline_image_link_id=None, baseline_set_id=None, resolution_scope=RESOLUTION_NONE,
            resolution_reason=(
                "Organization policy requires an exact Digital Twin baseline and none is approved — "
                "not falling back to a broader baseline."
            ),
            limitations=["Exact-match policy in effect; broader baselines were not considered."],
        )

    # 2. Exact manufacturer/model/anatomy-zone approved baseline.
    if candidate.manufacturer and candidate.model_name and candidate.anatomy_zone:
        row = (
            _active_links_query(db, candidate.tenant_id)
            .filter(
                BaselineImageLink.manufacturer == candidate.manufacturer,
                BaselineImageLink.model_name == candidate.model_name,
                BaselineImageLink.anatomy_zone == candidate.anatomy_zone,
            )
            .order_by(BaselineImageLink.approved_at.desc())
            .first()
        )
        if row is not None:
            return ResolutionResult(
                baseline_image_link_id=row.id, baseline_set_id=None,
                resolution_scope=RESOLUTION_MANUFACTURER_MODEL_ZONE,
                resolution_reason="Exact manufacturer/model/anatomy-zone approved baseline image found.",
                version=row.baseline_version,
            )

    # 3. Organization-approved instrument-family/anatomy-zone baseline.
    if candidate.instrument_family and candidate.anatomy_zone:
        row = (
            _active_links_query(db, candidate.tenant_id)
            .filter(
                BaselineImageLink.instrument_family == candidate.instrument_family,
                BaselineImageLink.anatomy_zone == candidate.anatomy_zone,
                BaselineImageLink.source_type.in_(_ORGANIZATION_SOURCE_TYPES),
            )
            .order_by(BaselineImageLink.approved_at.desc())
            .first()
        )
        if row is not None:
            return ResolutionResult(
                baseline_image_link_id=row.id, baseline_set_id=None,
                resolution_scope=RESOLUTION_ORGANIZATION_FAMILY_ZONE,
                resolution_reason="Organization-approved instrument-family/anatomy-zone baseline image found.",
                version=row.baseline_version,
                limitations=["Not manufacturer/model-specific — broader organization-level reference."],
            )

    # 4. Authorized governed consensus baseline.
    if candidate.instrument_family:
        row = (
            _active_links_query(db, candidate.tenant_id)
            .filter(
                BaselineImageLink.instrument_family == candidate.instrument_family,
                BaselineImageLink.source_type == SOURCE_GOVERNED_CONSENSUS_REFERENCE,
            )
            .order_by(BaselineImageLink.approved_at.desc())
            .first()
        )
        if row is not None:
            return ResolutionResult(
                baseline_image_link_id=row.id, baseline_set_id=None,
                resolution_scope=RESOLUTION_GOVERNED_CONSENSUS,
                resolution_reason="Governed consensus baseline image found for this instrument family.",
                version=row.baseline_version,
                limitations=["Consensus reference — not manufacturer, model, or anatomy-zone specific."],
            )

    # 5. Nothing approved.
    return ResolutionResult(
        baseline_image_link_id=None, baseline_set_id=None, resolution_scope=RESOLUTION_NONE,
        resolution_reason="No approved, ACTIVE baseline image resolves for this instrument context.",
    )


__all__ = ["CandidateContext", "ResolutionResult", "check_compatibility", "resolve_baseline_image"]
