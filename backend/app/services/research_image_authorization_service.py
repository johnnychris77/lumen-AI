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

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.research_image_authorization import (
    STATUS_ACTIVE,
    STATUS_WITHDRAWN,
    ResearchImageAuthorization,
)
from app.models.retained_image import RetainedImage

RESEARCH_SOURCE = "trc001_research_intake"


class ResearchImageAccessError(PermissionError):
    """Raised when an actor is not authorized to access a research image."""


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


def delete_images_without_basis(
    db: Session, image_ids: list[int], *, tenant_id: str, owner_subject: str,
) -> dict[str, list[int]]:
    """Delete bytes/rows only for images attributable SOLELY to the withdrawing owner.

    An image is deleted iff ALL hold (does not commit; verify by re-query):
      * no ACTIVE authorization by ANY owner remains, AND
      * no independent lawful retention basis (``source != trc001_research_intake``), AND
      * no other owner's legacy (pre-association) claim stamped on the row.
    Otherwise the bytes are retained (and flagged for governed review) — never deleting
    another owner's data merely because this owner withdrew."""
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
        ):
            retained.append(image_id)
            continue
        db.delete(image)
        deleted.append(image_id)
    db.flush()
    return {"deleted": deleted, "retained": retained}


def authorize_image_access(
    db: Session, *, tenant_id: str, owner_subject: str, retained_image_id: int,
) -> RetainedImage:
    """Return the image IFF the verified owner (tenant + session subject) holds an ACTIVE
    authorization for it. Tenant-scoped and per-owner — matching bytes grant nothing.

    Raises ``ResearchImageAccessError`` otherwise (never leaks existence across tenants)."""
    image = (
        db.query(RetainedImage)
        .filter(RetainedImage.tenant_id == tenant_id, RetainedImage.id == retained_image_id)
        .first()
    )
    if image is None:
        raise ResearchImageAccessError("No such research image for this tenant.")
    authorized = (
        db.query(ResearchImageAuthorization)
        .filter(
            ResearchImageAuthorization.tenant_id == tenant_id,
            ResearchImageAuthorization.retained_image_id == retained_image_id,
            ResearchImageAuthorization.owner_subject == owner_subject,
            ResearchImageAuthorization.status == STATUS_ACTIVE,
        )
        .first()
    )
    if authorized is None:
        raise ResearchImageAccessError(
            "The authenticated owner holds no active authorization for this research image.")
    return image
