"""Temporary inspection-image processing store.

Separates two things the pilot had wrongly coupled:

  * **Training retention** (`app.models.retained_image.RetainedImage`) — long-term
    storage of inspection pixels for model training, which REQUIRES explicit
    opt-in (`RETAIN_INSPECTION_IMAGES`) and per-submission consent.
  * **Processing** (this table) — the short-lived pixel bytes needed to actually
    run the inspection the user just requested (baseline image comparison), held
    only within a bounded, tenant-scoped lifecycle and purged when the inspection
    is processed or the row expires.

Nothing in the training / dataset pipeline reads this table, so storing a
processing image here NEVER enrolls it in a training dataset. Bytes are
EXIF-stripped before they land here (no GPS/device metadata), the row is scoped
to one tenant, and it carries an explicit ``expires_at`` so an abandoned upload
is reclaimed by the purge sweep.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InspectionProcessingImage(Base):
    __tablename__ = "inspection_processing_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True,
    )
    # Strict tenant scope — a processing image is only ever loaded for the tenant
    # that uploaded it (cross-tenant access is impossible by construction).
    tenant_id: Mapped[str] = mapped_column(String(100), default="default-tenant", nullable=False, index=True)

    # The sha256 the CLIENT computed on the original uploaded file and submits as
    # the inspection's image_sha256 — the lookup key tying the upload to the
    # inspection. Independent of stored_sha256 because EXIF-stripping re-encodes
    # the bytes to a different hash.
    image_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    # The sha256 of the actual stored (EXIF-stripped) bytes — used only to verify
    # the stored bytes still match their own registered identity on load.
    stored_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # The EXIF-stripped pixel bytes. Nulled out the moment the image is consumed
    # (processing finished) so the bytes do not linger beyond their purpose.
    image_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    uploaded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    inspection_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Bounded lifecycle. ``pending`` until consumed; ``consumed`` once the bytes
    # have been used for processing (and nulled); rows past ``expires_at`` are
    # deleted by the purge sweep whether or not they were consumed.
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
