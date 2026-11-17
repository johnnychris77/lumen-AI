"""SEC-171-04: per-owner research-image authorization association.

Ownership of a retained research image is NOT inferred from matching image bytes. Instead,
each authorized owner holds an explicit association row linking a verified owner (actor +
session subject) + governance attestation to a ``retained_images`` row for a specific
research dataset and tenant.

This lets two independently authorized owners reference identical image bytes within the
same tenant (two association rows, one shared ``retained_images`` row), makes withdrawal
revoke only the requesting owner's association, and lets the retention/deletion policy keep
shared bytes while ANY valid authorization (or an independent lawful retention basis) still
exists. It never transfers ownership merely because hashes match.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

STATUS_ACTIVE = "active"
STATUS_WITHDRAWN = "withdrawn"


class ResearchImageAuthorization(Base):
    """One verified owner's authorization to retain/access a specific research image."""

    __tablename__ = "research_image_authorizations"
    __table_args__ = (
        # At most one association per (tenant, image, dataset, owner subject): a given
        # verified owner has a single association for an image in a dataset (reactivated on
        # re-attestation), while a DIFFERENT owner_subject gets its own row for the same image.
        UniqueConstraint(
            "tenant_id", "retained_image_id", "research_dataset_id", "owner_subject",
            name="uq_research_image_auth_owner",
        ),
        Index("ix_research_image_auth_image_status", "retained_image_id", "status"),
        Index("ix_research_image_auth_tenant_owner", "tenant_id", "owner_subject"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    retained_image_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("retained_images.id", ondelete="CASCADE"), nullable=False, index=True)
    research_dataset_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    owner_actor: Mapped[str] = mapped_column(String(255), nullable=False)
    # The verified OIDC session subject ('sub') of the owner — identity, not just username.
    owner_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    attestation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("governance_approvals.id"), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), default=STATUS_ACTIVE, nullable=False, index=True)
