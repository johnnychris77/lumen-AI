"""Project Atlas Sprint 1 — Baseline Image Library service layer.

Links an existing LCID-registered image (`DatasetRegistryEntry`) to a
`BaselineLibraryEntry`, and governs that link through review, activation,
suspension, and supersession. Reuses, rather than re-derives:

  * `app.models.dataset_governance.DatasetRegistryEntry` for every piece of
    image/instrument/governance metadata that entry already owns.
  * `app.models.retained_image.RetainedImage` for the actual bytes.
  * `app.services.ml.lcid_service.is_untracked_twin` for identity honesty.
  * `app.services.enterprise_audit_service.record_enterprise_audit_event`
    for the hash-chained audit trail (this service never writes its own
    audit table).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.annotation_database import (
    ROLE_ADMINISTRATOR,
    ROLE_CLINICAL_REVIEWER,
    ROLE_REVIEWER,
)
from app.models.baseline_image_library import (
    BASELINE_IMAGE_STATES,
    IMAGE_EVIDENCE_MISSING,
    SOURCE_TYPES_REQUIRING_PROVENANCE,
    STATE_ACTIVE,
    STATE_APPROVED,
    STATE_ARCHIVED,
    STATE_DRAFT,
    STATE_PENDING_REVIEW,
    STATE_REJECTED,
    STATE_SUPERSEDED,
    STATE_SUSPENDED,
    VALID_BASELINE_IMAGE_TRANSITIONS,
    BaselineComparisonAccessLog,
    BaselineImageLink,
    BaselineImageReview,
)
from app.models.baseline_library import BaselineLibraryEntry
from app.models.dataset_governance import QUALITY_POOR, QUALITY_REJECT, DatasetRegistryEntry
from app.models.retained_image import RetainedImage
from app.services.ml.lcid_service import is_untracked_twin
from app.services.enterprise_audit_service import record_enterprise_audit_event

ROLES_MAY_REVIEW_BASELINE_IMAGE = {ROLE_ADMINISTRATOR, ROLE_CLINICAL_REVIEWER, ROLE_REVIEWER}
ROLES_MAY_ACTIVATE_BASELINE_IMAGE = {ROLE_ADMINISTRATOR, ROLE_CLINICAL_REVIEWER, ROLE_REVIEWER}


class BaselineLibraryEntryNotFound(ValueError):
    pass


class LcidImageNotFound(ValueError):
    pass


class TenantMismatchError(ValueError):
    pass


class ProvenanceRequiredError(ValueError):
    pass


class InvalidTransitionError(ValueError):
    pass


class PermissionDeniedError(ValueError):
    pass


class ActivationGateError(ValueError):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Baseline image cannot be activated — missing: {', '.join(missing)}")


class ImageIdentityMismatchError(ValueError):
    """The retained bytes no longer hash to the value registered at link
    time — never silently used for comparison (mirrors the same
    reload/recompute/reject pattern added to
    app.routes.inspections.create_inspection() in the false-PASS
    remediation sprint)."""


def _require_transition(current: str, target: str) -> None:
    allowed = VALID_BASELINE_IMAGE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(f"Cannot move a baseline image from {current} to {target}.")


def linked_lcid_entry(db: Session, *, tenant_id: str, lcid_image_id: int) -> DatasetRegistryEntry:
    entry = (
        db.query(DatasetRegistryEntry)
        .filter(DatasetRegistryEntry.id == lcid_image_id, DatasetRegistryEntry.tenant_id == tenant_id)
        .first()
    )
    if entry is None:
        raise LcidImageNotFound(f"No LCID-registered image {lcid_image_id} found for this tenant.")
    return entry


def link_lcid_image_to_baseline(
    db: Session, *, tenant_id: str, facility_id: str = "",
    baseline_library_entry_id: int, lcid_image_id: int,
    anatomy_zone: str, inspection_view: str, orientation: str = "",
    image_type: str, source_type: str,
    source_organization: str = "", source_reference: str = "",
    baseline_version: str = "1.0", created_by: str = "",
) -> BaselineImageLink:
    """Section 1/10 — register the proposed baseline-image relationship in
    DRAFT. Never duplicates the image itself: every instrument/quality/
    rights/identity field is snapshotted FROM the linked LCID entry, not
    re-entered by the caller."""
    baseline_entry = db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.id == baseline_library_entry_id).first()
    if baseline_entry is None:
        raise BaselineLibraryEntryNotFound(f"No BaselineLibraryEntry {baseline_library_entry_id} found.")

    lcid_entry = linked_lcid_entry(db, tenant_id=tenant_id, lcid_image_id=lcid_image_id)

    if source_type in SOURCE_TYPES_REQUIRING_PROVENANCE and not (source_organization.strip() and source_reference.strip()):
        # Section 5 — "do not permit a user to mark an image
        # manufacturer-approved merely by selecting a dropdown value."
        raise ProvenanceRequiredError(
            "manufacturer_reference source requires both source_organization and a real source_reference "
            "(document id, PO/correspondence reference, or vendor-portal submission id)."
        )

    link = BaselineImageLink(
        tenant_id=tenant_id, facility_id=facility_id,
        baseline_library_entry_id=baseline_library_entry_id, lcid_image_id=lcid_image_id,
        instrument_family=lcid_entry.instrument_family, manufacturer=lcid_entry.manufacturer,
        model_name=lcid_entry.instrument_model, catalog_number=lcid_entry.catalog_number,
        anatomy_zone=anatomy_zone, inspection_view=inspection_view, orientation=orientation,
        image_type=image_type, source_type=source_type,
        source_organization=source_organization, source_reference=source_reference,
        baseline_version=baseline_version, lifecycle_status=STATE_DRAFT,
        usage_rights_status=lcid_entry.usage_rights, image_quality_status=lcid_entry.image_quality,
        digital_twin_id=lcid_entry.digital_twin_id, image_sha256=lcid_entry.image_sha256,
        retained_image_id=lcid_entry.retained_image_id, created_by=created_by,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    record_enterprise_audit_event(
        db, action_type="baseline_image_proposed", resource_type="baseline_image_link",
        resource_id=str(link.id), tenant_id=tenant_id, actor_email=created_by,
        baseline_id=baseline_library_entry_id,
        details={"lcid_image_id": lcid_image_id, "lcid": lcid_entry.lcid, "source_type": source_type},
    )
    return link


def submit_for_review(db: Session, *, link: BaselineImageLink, actor: str) -> BaselineImageLink:
    _require_transition(link.lifecycle_status, STATE_PENDING_REVIEW)
    link.lifecycle_status = STATE_PENDING_REVIEW
    db.commit()
    db.refresh(link)
    record_enterprise_audit_event(
        db, action_type="baseline_image_submitted_for_review", resource_type="baseline_image_link",
        resource_id=str(link.id), tenant_id=link.tenant_id, actor_email=actor,
        baseline_id=link.baseline_library_entry_id,
    )
    return link


def review_baseline_image(
    db: Session, *, link: BaselineImageLink, reviewer: str, reviewer_role: str,
    decision: str, rationale: str, limitations: str = "",
    source_verification: str = "", anatomy_compatibility_confirmed: bool = False,
    image_quality_assessment: str = "", next_review_date: datetime | None = None,
) -> BaselineImageReview:
    """Section 5 — a real review record, always required before ACTIVE.
    `decision` is "approve" or "reject"."""
    if reviewer_role not in ROLES_MAY_REVIEW_BASELINE_IMAGE:
        raise PermissionDeniedError(f"Role '{reviewer_role}' may not review a baseline image.")
    if link.lifecycle_status != STATE_PENDING_REVIEW:
        raise InvalidTransitionError("Baseline image is not currently PENDING_REVIEW.")

    target_state = STATE_APPROVED if decision == "approve" else STATE_REJECTED
    _require_transition(link.lifecycle_status, target_state)

    review = BaselineImageReview(
        tenant_id=link.tenant_id, baseline_image_link_id=link.id,
        reviewer=reviewer, reviewer_role=reviewer_role, decision=decision, rationale=rationale,
        limitations=limitations, source_verification=source_verification,
        anatomy_compatibility_confirmed=anatomy_compatibility_confirmed,
        image_quality_assessment=image_quality_assessment, next_review_date=next_review_date,
    )
    db.add(review)

    link.lifecycle_status = target_state
    if decision == "approve":
        link.approved_by = reviewer
        link.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)

    record_enterprise_audit_event(
        db, action_type=f"baseline_image_{decision}d" if decision == "reject" else "baseline_image_approved",
        resource_type="baseline_image_link", resource_id=str(link.id), tenant_id=link.tenant_id,
        actor_email=reviewer, actor_role=reviewer_role, baseline_id=link.baseline_library_entry_id,
        details={"rationale": rationale, "limitations": limitations},
    )
    return review


def activation_gate_failures(db: Session, *, link: BaselineImageLink) -> list[str]:
    """Section 4 — every condition an ACTIVE baseline image must satisfy.
    Returns the list of failures (empty list = eligible)."""
    missing: list[str] = []

    lcid_entry = (
        db.query(DatasetRegistryEntry)
        .filter(DatasetRegistryEntry.id == link.lcid_image_id, DatasetRegistryEntry.tenant_id == link.tenant_id)
        .first()
    )
    if lcid_entry is None:
        missing.append("image registration is no longer resolvable (LCID entry missing)")
        return missing  # nothing else below can be honestly checked without it

    if not lcid_entry.retained_image_id:
        missing.append("image registration is incomplete (no retained image bytes reference)")
    if not (lcid_entry.usage_rights or "").strip():
        missing.append("usage rights are not documented")
    if lcid_entry.phi_verification != "verified":
        missing.append("PHI review is not complete")
    if lcid_entry.image_quality in (QUALITY_REJECT, QUALITY_POOR, ""):
        missing.append("image quality is not acceptable")
    if is_untracked_twin(lcid_entry.digital_twin_id) and not (link.manufacturer and link.model_name):
        missing.append("instrument identity is not sufficiently resolved")
    if not link.anatomy_zone.strip():
        missing.append("anatomy zone is not documented")
    if not link.inspection_view.strip():
        missing.append("inspection view is not documented")

    has_approving_review = (
        db.query(BaselineImageReview)
        .filter(BaselineImageReview.baseline_image_link_id == link.id, BaselineImageReview.decision == "approve")
        .first()
    )
    if has_approving_review is None:
        missing.append("required clinical review is not complete")
    if not link.image_sha256.strip():
        missing.append("image hash is not stored")
    if not link.baseline_version.strip():
        missing.append("baseline version is not assigned")

    return missing


def activate_baseline_image(db: Session, *, link: BaselineImageLink, actor: str, actor_role: str) -> BaselineImageLink:
    if actor_role not in ROLES_MAY_ACTIVATE_BASELINE_IMAGE:
        raise PermissionDeniedError(f"Role '{actor_role}' may not activate a baseline image.")
    _require_transition(link.lifecycle_status, STATE_ACTIVE)

    missing = activation_gate_failures(db, link=link)
    if missing:
        raise ActivationGateError(missing)

    link.lifecycle_status = STATE_ACTIVE
    db.commit()
    db.refresh(link)

    record_enterprise_audit_event(
        db, action_type="baseline_image_activated", resource_type="baseline_image_link",
        resource_id=str(link.id), tenant_id=link.tenant_id, actor_email=actor, actor_role=actor_role,
        baseline_id=link.baseline_library_entry_id,
    )
    return link


def suspend_baseline_image(db: Session, *, link: BaselineImageLink, actor: str, actor_role: str, reason: str) -> BaselineImageLink:
    if actor_role not in ROLES_MAY_ACTIVATE_BASELINE_IMAGE:
        raise PermissionDeniedError(f"Role '{actor_role}' may not suspend a baseline image.")
    _require_transition(link.lifecycle_status, STATE_SUSPENDED)
    link.lifecycle_status = STATE_SUSPENDED
    db.commit()
    db.refresh(link)
    record_enterprise_audit_event(
        db, action_type="baseline_image_suspended", resource_type="baseline_image_link",
        resource_id=str(link.id), tenant_id=link.tenant_id, actor_email=actor, actor_role=actor_role,
        baseline_id=link.baseline_library_entry_id, details={"reason": reason},
    )
    return link


def archive_baseline_image(db: Session, *, link: BaselineImageLink, actor: str, actor_role: str) -> BaselineImageLink:
    if actor_role not in ROLES_MAY_ACTIVATE_BASELINE_IMAGE:
        raise PermissionDeniedError(f"Role '{actor_role}' may not archive a baseline image.")
    _require_transition(link.lifecycle_status, STATE_ARCHIVED)
    link.lifecycle_status = STATE_ARCHIVED
    db.commit()
    db.refresh(link)
    record_enterprise_audit_event(
        db, action_type="baseline_image_archived", resource_type="baseline_image_link",
        resource_id=str(link.id), tenant_id=link.tenant_id, actor_email=actor, actor_role=actor_role,
        baseline_id=link.baseline_library_entry_id,
    )
    return link


def supersede_baseline_image(
    db: Session, *, old_link: BaselineImageLink, new_link: BaselineImageLink, actor: str, actor_role: str,
) -> tuple[BaselineImageLink, BaselineImageLink]:
    """Section 4/6 — a version change is a NEW row activated + the old row
    marked SUPERSEDED; the old row's data is never edited or deleted, so
    "superseded baseline remains historically visible" (Section 16) holds
    structurally."""
    if actor_role not in ROLES_MAY_ACTIVATE_BASELINE_IMAGE:
        raise PermissionDeniedError(f"Role '{actor_role}' may not supersede a baseline image.")
    if old_link.tenant_id != new_link.tenant_id:
        raise TenantMismatchError("Cannot supersede a baseline image across tenants.")

    _require_transition(old_link.lifecycle_status, STATE_SUPERSEDED)
    if new_link.lifecycle_status != STATE_APPROVED:
        raise InvalidTransitionError("The replacement baseline image must be APPROVED before it can take over.")
    _require_transition(new_link.lifecycle_status, STATE_ACTIVE)

    old_link.lifecycle_status = STATE_SUPERSEDED
    old_link.superseded_at = datetime.now(timezone.utc)
    old_link.superseded_by = actor
    new_link.lifecycle_status = STATE_ACTIVE
    new_link.supersedes_link_id = old_link.id
    db.commit()
    db.refresh(old_link)
    db.refresh(new_link)

    record_enterprise_audit_event(
        db, action_type="baseline_image_superseded", resource_type="baseline_image_link",
        resource_id=str(old_link.id), tenant_id=old_link.tenant_id, actor_email=actor, actor_role=actor_role,
        baseline_id=old_link.baseline_library_entry_id, details={"superseded_by_link_id": new_link.id},
    )
    return old_link, new_link


def load_and_verify_baseline_bytes(db: Session, *, link: BaselineImageLink, accessed_by: str = "") -> bytes:
    """Section 9 — reload the stored bytes, recompute SHA-256, verify
    against the registered hash, reject on mismatch. Never overwrites the
    image in place; a mismatch is logged and raised, not silently
    tolerated."""
    row = None
    if link.retained_image_id:
        row = db.query(RetainedImage).filter(RetainedImage.id == link.retained_image_id).first()

    outcome = "not_found"
    try:
        if row is None or row.image_bytes is None:
            raise ImageIdentityMismatchError(f"No retained image bytes found for baseline image link {link.id}.")
        recomputed = hashlib.sha256(row.image_bytes).hexdigest()
        if recomputed != row.sha256 or recomputed != link.image_sha256:
            outcome = "hash_mismatch"
            record_enterprise_audit_event(
                db, action_type="baseline_image_hash_verification_failed", resource_type="baseline_image_link",
                resource_id=str(link.id), tenant_id=link.tenant_id, actor_email=accessed_by,
                baseline_id=link.baseline_library_entry_id, status="failure",
                details={"registered_sha256": link.image_sha256, "recomputed_sha256": recomputed},
            )
            raise ImageIdentityMismatchError(
                f"Baseline image {link.id}: stored bytes no longer hash to the registered identity — rejecting."
            )
        outcome = "verified"
        return row.image_bytes
    finally:
        db.add(BaselineComparisonAccessLog(
            tenant_id=link.tenant_id, baseline_image_link_id=link.id,
            accessed_by=accessed_by, outcome=outcome,
        ))
        db.commit()


def legacy_baseline_report(db: Session, *, tenant_id: str) -> dict:
    """Section 15 — every BaselineLibraryEntry in this tenant's scope,
    classified by whether it has an ACTIVE image link. Note:
    BaselineLibraryEntry itself carries no tenant_id column (see
    BASELINE_CURRENT_STATE_TRACE.md Section 3) — this report is scoped by
    joining through this tenant's own BaselineImageLink rows plus every
    BaselineLibraryEntry with zero links at all (visible to every tenant,
    matching the pre-existing global-registry behavior)."""
    all_entries = db.query(BaselineLibraryEntry).all()
    active_ids_this_tenant = {
        row.baseline_library_entry_id
        for row in db.query(BaselineImageLink).filter(
            BaselineImageLink.tenant_id == tenant_id, BaselineImageLink.lifecycle_status == STATE_ACTIVE,
        ).all()
    }

    with_active_image: list[int] = []
    missing_image: list[int] = []
    missing_anatomy_zone: list[int] = []
    missing_usage_rights: list[int] = []
    needing_review: list[int] = []

    for entry in all_entries:
        if entry.id in active_ids_this_tenant:
            with_active_image.append(entry.id)
        else:
            missing_image.append(entry.id)
        links = [
            row for row in db.query(BaselineImageLink).filter(
                BaselineImageLink.tenant_id == tenant_id, BaselineImageLink.baseline_library_entry_id == entry.id,
            ).all()
        ]
        if not any(link.anatomy_zone.strip() for link in links):
            missing_anatomy_zone.append(entry.id)
        if not any(link.usage_rights_status.strip() for link in links):
            missing_usage_rights.append(entry.id)
        if any(link.lifecycle_status in (STATE_DRAFT, STATE_PENDING_REVIEW) for link in links):
            needing_review.append(entry.id)

    return {
        "total_baseline_entries": len(all_entries),
        "with_active_image": with_active_image,
        "missing_image_evidence": missing_image,
        "missing_image_evidence_marker": IMAGE_EVIDENCE_MISSING,
        "missing_anatomy_zone": missing_anatomy_zone,
        "missing_usage_rights": missing_usage_rights,
        "needing_review": needing_review,
    }


__all__ = [
    "BASELINE_IMAGE_STATES",
    "BaselineLibraryEntryNotFound", "LcidImageNotFound", "TenantMismatchError",
    "ProvenanceRequiredError", "InvalidTransitionError", "PermissionDeniedError",
    "ActivationGateError", "ImageIdentityMismatchError",
    "linked_lcid_entry", "link_lcid_image_to_baseline", "submit_for_review",
    "review_baseline_image", "activation_gate_failures", "activate_baseline_image",
    "suspend_baseline_image", "archive_baseline_image", "supersede_baseline_image",
    "load_and_verify_baseline_bytes", "legacy_baseline_report",
]
