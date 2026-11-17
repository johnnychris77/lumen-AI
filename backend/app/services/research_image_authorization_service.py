"""SEC-171-04: research-image authorization + retention-basis policy.

Encapsulates the per-owner association between a verified research owner and a retained
image, and the explicit policy for when shared image bytes may be deleted. Changing the DB
model alone does not enforce access control — callers MUST route image access and deletion
through these helpers.

Retention policy (explicit):
  An image's bytes are retained while EITHER
    (a) at least one ACTIVE ``ResearchImageAuthorization`` references it, OR
    (b) it has an independent lawful retention basis — its ``source`` is not
        ``trc001_research_intake`` (e.g. a baseline reference or inspection image that was
        retained for a non-research reason).
  When neither holds, the bytes/row are deleted. Deletion is verified by re-query.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.governance_approval import GovernanceApproval
from app.models.research_image_authorization import (
    STATUS_ACTIVE,
    STATUS_WITHDRAWN,
    ResearchImageAuthorization,
)
from app.models.retained_image import RetainedImage

RESEARCH_SOURCE = "trc001_research_intake"
# Governance attestation state that still authorizes access.
APPROVED_STATUS = "approved"
# Only a cryptographically verified OIDC session may hold research-owner authority.
OIDC_PROVIDER = "oidc"

logger = logging.getLogger(__name__)

# Stable, non-sensitive denial-reason categories (safe for audit evidence).
DENY_IMAGE_NOT_FOUND = "image_not_found"
DENY_CROSS_TENANT = "cross_tenant_or_missing"
DENY_NO_VERIFIED_OWNER = "no_verified_owner_session"
DENY_NO_ACTIVE_AUTHORIZATION = "no_active_attested_authorization"

# Audit action types for the research-image access decision.
AUDIT_ACCESS_GRANTED = "research_image_access_granted"
AUDIT_ACCESS_DENIED = "research_image_access_denied"


class ResearchImageAccessError(PermissionError):
    """Raised when an actor is not authorized to access a research image.

    ``reason`` is a stable, non-sensitive category (one of the ``DENY_*`` constants)
    suitable for audit evidence; it never contains image bytes, tokens, or payloads."""

    def __init__(self, message: str, *, reason: str = "denied") -> None:
        super().__init__(message)
        self.reason = reason


def upsert_active_authorization(
    db: Session, *, tenant_id: str, retained_image_id: int, research_dataset_id: str,
    owner_actor: str, owner_subject: str, attestation_id: int | None,
) -> ResearchImageAuthorization:
    """Create or reactivate THIS owner's association for an image. Does not commit.

    Two different ``owner_subject`` values yield two independent rows for the same image;
    re-attestation by the same owner reactivates their existing (possibly withdrawn) row.
    Never reassigns or mutates another owner's association."""
    row = (
        db.query(ResearchImageAuthorization)
        .filter(
            ResearchImageAuthorization.tenant_id == tenant_id,
            ResearchImageAuthorization.retained_image_id == retained_image_id,
            ResearchImageAuthorization.research_dataset_id == research_dataset_id,
            ResearchImageAuthorization.owner_subject == owner_subject,
        )
        .with_for_update()
        .first()
    )
    if row is None:
        row = ResearchImageAuthorization(
            tenant_id=tenant_id, retained_image_id=retained_image_id,
            research_dataset_id=research_dataset_id, owner_actor=owner_actor,
            owner_subject=owner_subject, attestation_id=attestation_id, status=STATUS_ACTIVE)
        db.add(row)
    else:
        row.status = STATUS_ACTIVE
        row.withdrawn_at = None
        row.owner_actor = owner_actor
        row.attestation_id = attestation_id
    db.flush()
    return row


def withdraw_owner_authorizations(
    db: Session, *, tenant_id: str, research_dataset_id: str, owner_actor: str, owner_subject: str,
) -> list[int]:
    """Withdraw ONLY the requesting owner's active associations (actor + subject bound).

    Returns the distinct ``retained_image_id`` values affected. Does not commit. Rows are
    locked FOR UPDATE (PostgreSQL) to serialize against concurrent intake/withdrawal."""
    rows = (
        db.query(ResearchImageAuthorization)
        .filter(
            ResearchImageAuthorization.tenant_id == tenant_id,
            ResearchImageAuthorization.research_dataset_id == research_dataset_id,
            ResearchImageAuthorization.owner_actor == owner_actor,
            ResearchImageAuthorization.owner_subject == owner_subject,
            ResearchImageAuthorization.status == STATUS_ACTIVE,
        )
        .with_for_update()
        .all()
    )
    affected: list[int] = []
    now = datetime.now(timezone.utc)
    for row in rows:
        row.status = STATUS_WITHDRAWN
        row.withdrawn_at = now
        if row.retained_image_id not in affected:
            affected.append(row.retained_image_id)
    db.flush()
    return affected


def image_has_active_authorization(db: Session, retained_image_id: int, *, tenant_id: str) -> bool:
    return (
        db.query(ResearchImageAuthorization)
        .filter(
            ResearchImageAuthorization.tenant_id == tenant_id,
            ResearchImageAuthorization.retained_image_id == retained_image_id,
            ResearchImageAuthorization.status == STATUS_ACTIVE,
        )
        .first()
        is not None
    )


def _has_independent_basis(image: RetainedImage) -> bool:
    """True when the image is retained for a non-research reason (its own lawful basis)."""
    return str(image.source or "") != RESEARCH_SOURCE


def _other_owner_legacy_claim(db: Session, image: RetainedImage, *, owner_subject: str) -> bool:
    """A pre-association (legacy) row stamped for a DIFFERENT owner who never received an
    association is still that owner's claim — never delete it on this owner's withdrawal."""
    stamped = str(image.research_owner_subject or "")
    if not stamped or stamped == owner_subject:
        return False
    stamped_has_assoc = (
        db.query(ResearchImageAuthorization)
        .filter(
            ResearchImageAuthorization.tenant_id == image.tenant_id,
            ResearchImageAuthorization.retained_image_id == image.id,
            ResearchImageAuthorization.owner_subject == stamped,
        )
        .first()
        is not None
    )
    return not stamped_has_assoc


def _has_unknown_ownership_provenance(image: RetainedImage) -> bool:
    """SEC-176-A: True for a research-source image whose owner provenance is UNKNOWN —
    ``source == RESEARCH_SOURCE`` with a blank ``research_owner_subject``.

    Such a row cannot be attributed solely to the withdrawing owner (its lawful owner is
    unestablished), so deleting it on that owner's withdrawal would destroy data of
    indeterminate provenance. Fail-safe is to PRESERVE it. This is a pure retention
    decision: it grants NO access — retrieval still requires an active, attested
    ``ResearchImageAuthorization`` for the caller, and an unknown-ownership row has none,
    so it stays unreadable. It only prevents silent data loss, never widening access."""
    if str(getattr(image, "source", "") or "") != RESEARCH_SOURCE:
        return False
    return not str(getattr(image, "research_owner_subject", "") or "").strip()


def delete_images_without_basis(
    db: Session, image_ids: list[int], *, tenant_id: str, owner_subject: str,
) -> dict[str, list[int]]:
    """Delete bytes/rows only for images attributable SOLELY to the withdrawing owner.

    An image is deleted iff ALL hold (does not commit; verify by re-query):
      * no ACTIVE authorization by ANY owner remains, AND
      * no independent lawful retention basis (``source != trc001_research_intake``), AND
      * no other owner's legacy (pre-association) claim stamped on the row, AND
      * the row's owner provenance is not UNKNOWN (SEC-176-A: a research row with a blank
        ``research_owner_subject`` is preserved, never attributed solely to the withdrawer).
    Otherwise the bytes are retained (and flagged for governed review) — never deleting
    another owner's data, or data of indeterminate ownership, merely because this owner
    withdrew."""
    deleted: list[int] = []
    retained: list[int] = []
    for image_id in image_ids:
        image = (
            db.query(RetainedImage)
            .filter(RetainedImage.tenant_id == tenant_id, RetainedImage.id == image_id)
            .with_for_update()
            .first()
        )
        if image is None:
            continue
        if (
            image_has_active_authorization(db, image_id, tenant_id=tenant_id)
            or _has_independent_basis(image)
            or _other_owner_legacy_claim(db, image, owner_subject=owner_subject)
            or _has_unknown_ownership_provenance(image)
        ):
            retained.append(image_id)
            continue
        db.delete(image)
        deleted.append(image_id)
    db.flush()
    return {"deleted": deleted, "retained": retained}


def is_research_image(image: RetainedImage) -> bool:
    """True iff the image's lawful basis is research intake (``source == RESEARCH_SOURCE``).

    A non-research source (baseline reference, inspection image, etc.) has its own
    independent retention basis and is NOT gated as research — even when a research
    association also references the shared bytes. This mirrors ``_has_independent_basis``
    so access control and the retention policy agree on what "research bytes" means."""
    return str(getattr(image, "source", "") or "") == RESEARCH_SOURCE


def _attestation_still_valid(db: Session, attestation_id: int | None) -> bool:
    """Fail-closed: the association's governance attestation must still exist and be approved.

    A missing attestation reference, a deleted approval, or any non-approved status
    (withdrawn / revoked / pending) revokes access — governance data missing or invalid
    denies, never grants (SEC-173-01 requirements 4 and 8)."""
    if attestation_id is None:
        return False
    approval = (
        db.query(GovernanceApproval)
        .filter(GovernanceApproval.id == attestation_id)
        .first()
    )
    return approval is not None and str(approval.status or "") == APPROVED_STATUS


def _active_attested_authorization(
    db: Session, *, tenant_id: str, retained_image_id: int, owner_subject: str,
) -> ResearchImageAuthorization | None:
    """The caller's ACTIVE authorization for the image IFF its attestation is still valid.

    Returns ``None`` (deny) when no active row exists for this tenant+image+subject, or
    when the associated attestation is no longer valid."""
    assoc = (
        db.query(ResearchImageAuthorization)
        .filter(
            ResearchImageAuthorization.tenant_id == tenant_id,
            ResearchImageAuthorization.retained_image_id == retained_image_id,
            ResearchImageAuthorization.owner_subject == owner_subject,
            ResearchImageAuthorization.status == STATUS_ACTIVE,
        )
        .first()
    )
    if assoc is None:
        return None
    if not _attestation_still_valid(db, assoc.attestation_id):
        return None
    return assoc


def principal_identity(principal: object) -> tuple[str, str]:
    """Normalize any caller object (``AuthContext`` or ``AuthenticatedPrincipal``) to
    ``(subject, auth_provider)``.

    Fail-closed: a principal without an explicit ``auth_provider == "oidc"`` yields a
    non-OIDC marker, so research-image bytes are denied to dev/app-local callers whose
    "subject" is an application email rather than a verified IdP ``sub``."""
    subject = str(getattr(principal, "subject", "") or "")
    provider = str(getattr(principal, "auth_provider", "") or "")
    return subject, provider


def assert_image_bytes_readable(
    db: Session, image: RetainedImage | None, *, tenant_id: str,
    caller_subject: str, caller_auth_provider: str,
) -> None:
    """Centralized, fail-closed authorization gate for returning ``RetainedImage`` bytes.

    This is the SINGLE policy every byte-returning path must call before releasing bytes
    (binary responses, JSON-embedded bytes, downloadable artifacts, access URLs, and
    internal byte loads). Routes must not re-implement the policy.

    Decision:
      * ``image is None``            -> deny (no cross-tenant existence leak).
      * tenant mismatch             -> deny.
      * non-research image          -> permit (the route's own tenant/role authz governs it;
                                        behavior for baseline/inspection images is unchanged).
      * research image              -> require ALL of: an OIDC-verified caller with a non-empty
                                        subject, an ACTIVE ``ResearchImageAuthorization`` for
                                        (tenant, image, subject), and a still-valid attestation.

    Raises ``ResearchImageAccessError`` on any denial."""
    if image is None:
        raise ResearchImageAccessError("No such image for this tenant.", reason=DENY_IMAGE_NOT_FOUND)
    if str(getattr(image, "tenant_id", "") or "") != str(tenant_id or ""):
        raise ResearchImageAccessError(
            "Image does not belong to the caller's tenant.", reason=DENY_CROSS_TENANT)
    if not is_research_image(image):
        return  # non-research bytes: existing route authorization applies
    if str(caller_auth_provider or "") != OIDC_PROVIDER or not str(caller_subject or "").strip():
        raise ResearchImageAccessError(
            "Research image bytes require a verified research-owner (OIDC) session.",
            reason=DENY_NO_VERIFIED_OWNER)
    if _active_attested_authorization(
        db, tenant_id=tenant_id, retained_image_id=image.id, owner_subject=caller_subject,
    ) is None:
        raise ResearchImageAccessError(
            "The caller holds no active, attested authorization for this research image.",
            reason=DENY_NO_ACTIVE_AUTHORIZATION)


def may_read_image_bytes(
    db: Session, image: RetainedImage | None, *, tenant_id: str,
    caller_subject: str, caller_auth_provider: str,
) -> bool:
    """Non-raising form of :func:`assert_image_bytes_readable` for call sites that degrade
    gracefully (omit an image from a PDF or a re-analysis) rather than returning an error."""
    try:
        assert_image_bytes_readable(
            db, image, tenant_id=tenant_id,
            caller_subject=caller_subject, caller_auth_provider=caller_auth_provider)
        return True
    except ResearchImageAccessError:
        return False


def authorize_image_access(
    db: Session, *, tenant_id: str, owner_subject: str, retained_image_id: int,
) -> RetainedImage:
    """Return the image IFF the verified owner (tenant + session subject) holds an ACTIVE
    authorization for it WITH a still-valid attestation. Tenant-scoped and per-owner —
    matching bytes grant nothing. Used by the research retrieval API (callers are always
    OIDC-verified via ``require_verified_oidc_context``); it enforces per-owner access for
    every row it serves, independent of ``source``.

    Raises ``ResearchImageAccessError`` otherwise (never leaks existence across tenants)."""
    image = (
        db.query(RetainedImage)
        .filter(RetainedImage.tenant_id == tenant_id, RetainedImage.id == retained_image_id)
        .first()
    )
    if image is None:
        raise ResearchImageAccessError(
            "No such research image for this tenant.", reason=DENY_CROSS_TENANT)
    if _active_attested_authorization(
        db, tenant_id=tenant_id, retained_image_id=retained_image_id, owner_subject=owner_subject,
    ) is None:
        raise ResearchImageAccessError(
            "The authenticated owner holds no active authorization for this research image.",
            reason=DENY_NO_ACTIVE_AUTHORIZATION)
    return image


def authorized_dataset_ids_for_owner(
    db: Session, *, tenant_id: str, retained_image_id: int, owner_subject: str,
) -> list[str]:
    """SEC-176-C: the research dataset id(s) THIS caller is actually authorized for on this
    image, derived from the caller's own ACTIVE associations whose attestation is still valid.

    Retrieval must disclose the caller's authorized dataset scope, not the image's stored
    ``research_dataset_id`` provenance stamp (which is a denormalized hint that can differ
    from what the caller's association grants). Returns a sorted, de-duplicated list; empty
    when the caller holds no valid authorization (callers are gated upstream by
    ``authorize_image_access``, so a non-empty result is the normal path)."""
    rows = (
        db.query(ResearchImageAuthorization)
        .filter(
            ResearchImageAuthorization.tenant_id == tenant_id,
            ResearchImageAuthorization.retained_image_id == retained_image_id,
            ResearchImageAuthorization.owner_subject == owner_subject,
            ResearchImageAuthorization.status == STATUS_ACTIVE,
        )
        .all()
    )
    datasets = {
        str(r.research_dataset_id or "")
        for r in rows
        if str(r.research_dataset_id or "") and _attestation_still_valid(db, r.attestation_id)
    }
    return sorted(datasets)


def audit_research_access_decision(
    db: Session, *, decision: str, reason: str, tenant_id: str, actor: str, actor_role: str,
    subject: str, retained_image_id: int | None, endpoint: str, request=None, auth_context=None,
) -> bool:
    """Durably record a research-image byte-access decision (``"granted"``/``"denied"``).

    Writes through the single append-only, hash-chained enterprise audit writer and COMMITS,
    so the event survives an authorization exception and the request's transaction teardown
    (SEC-174-01 property 7). The event records only non-sensitive fields — tenant, actor,
    verified subject, resource id, decision, reason category, endpoint, and (when a request is
    supplied) method/path — and NEVER image bytes, tokens, or JWTs (property 10).

    Never raises into the caller: on an audit-write failure it logs and returns ``False`` so the
    caller stays fail-closed (the access is already being denied / not served) — property 8."""
    from app.services.enterprise_audit_service import (  # noqa: PLC0415
        record_enterprise_audit_event,
    )

    action = AUDIT_ACCESS_GRANTED if decision == "granted" else AUDIT_ACCESS_DENIED
    try:
        record_enterprise_audit_event(
            db,
            action_type=action,
            resource_type="retained_image",
            resource_id=str(retained_image_id if retained_image_id is not None else ""),
            actor=actor or "unknown",
            actor_role=actor_role or "",
            tenant_id=tenant_id,
            status=("success" if decision == "granted" else "denied"),
            details={
                "decision": decision,
                "reason": reason,
                "endpoint": endpoint,
                "subject": subject or "",
                "retained_image_id": retained_image_id,
            },
            auth_context=auth_context,
            request=request,
            commit=True,
        )
        return True
    except Exception:  # pragma: no cover - audit infra failure path
        logger.exception(
            "research-image access audit write failed (decision=%s reason=%s endpoint=%s)",
            decision, reason, endpoint,
        )
        try:
            db.rollback()
        except Exception:
            logger.exception("rollback after audit failure also failed")
        return False
