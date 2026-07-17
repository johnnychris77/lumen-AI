"""Project Foundation (GPAE) — governed object storage registry.

This is deliberately additive to what already exists:

  * ``app.services.object_storage`` already writes/reads raw bytes to a
    local-filesystem or S3 backend — it stays the byte-transport layer and
    is reused, not reimplemented.
  * ``app.models.retained_image.RetainedImage`` stores EXIF-stripped image
    bytes in the database for training retention — untouched.
  * ``app.models.baseline_image_library`` links LCID images to baselines
    with per-access hash verification — untouched.

What is genuinely new here: a single governance registry row for every
object placed in object storage, carrying the Foundation Sprint 1
contract — permanent Object ID, SHA-256, upload timestamp, uploader,
organization (tenant), retention policy, storage URI, version, and audit
linkage — plus content-hash deduplication so the same bytes are never
stored twice for the same tenant.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Object categories accepted by the governed store (Foundation Section 2).
OBJECT_CATEGORIES = [
    "borescope_image",
    "baseline_image",
    "report",
    "dataset_export",
    "pdf",
    "thumbnail",
    "model_artifact",
    "supporting_evidence",
]

STATUS_ACTIVE = "ACTIVE"
STATUS_SUPERSEDED = "SUPERSEDED"

# Retention policies are governance labels, not auto-delete timers: nothing
# in the governed store is deleted by code. A delete REQUEST is itself an
# audited action reviewed by a human (see docs/foundation/OBJECT_STORAGE.md).
RETENTION_POLICIES = [
    "retain_indefinitely",
    "retain_per_org_policy",
    "retain_until_review",
]


class GovernedObject(Base):
    __tablename__ = "governed_objects"
    __table_args__ = (
        # Dedup contract: identical bytes are registered once per tenant.
        UniqueConstraint("tenant_id", "sha256", name="uq_governed_objects_tenant_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Permanent identity — assigned once at registration, never reused,
    # never reassigned (mirrors the LCID permanence rule).
    object_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream", nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    object_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    uploader: Mapped[str] = mapped_column(String(255), default="system", nullable=False)

    retention_policy: Mapped[str] = mapped_column(
        String(50), default="retain_indefinitely", nullable=False
    )

    storage_backend: Mapped[str] = mapped_column(String(20), default="local", nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Version chain: registering changed bytes for the same logical object
    # creates a NEW row (new object_id, version+1) and marks the prior row
    # SUPERSEDED — rows are never edited in place.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    supersedes_object_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_ACTIVE, nullable=False, index=True)

    # Integrity bookkeeping — set by verified reads, never by trust.
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    integrity_intact: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
