"""Retained inspection-image store + labeling models.

Foundation for training a real image-based inspection model. The platform
otherwise stores **only SHA-256 hashes** — training and baseline-diff require
the actual image bytes, which is a deliberate, access-controlled, opt-in
capability (env-gated, OFF by default) with EXIF stripped on ingest.

Security/governance:
- Retention is OFF unless ``RETAIN_INSPECTION_IMAGES`` is enabled AND consent is
  recorded — a prerequisite, not a default.
- EXIF/metadata is stripped before bytes are persisted (no GPS, no device, no
  embedded thumbnails) — PHI-avoidance.
- De-identified filename ``{instrument_type}_{seq}`` — never patient/facility
  identifiers.
- Every label change is audit-logged by the routes that mutate these rows.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetainedImage(Base):
    """An inspection/baseline image retained (opt-in) for model training.

    Stores EXIF-stripped bytes plus de-identified metadata. No patient
    identifiers, MRNs, faces, or documents are permitted in frame.
    """

    __tablename__ = "retained_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    # De-identified handle — never a patient/facility identifier.
    deident_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    instrument_type: Mapped[str] = mapped_column(
        String(100), default="unknown", nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # SHA-256 of the EXIF-stripped bytes actually stored (integrity + dedupe).
    sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    exif_stripped: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Provenance — in-workflow capture, baseline reference, or curated demo set.
    source: Mapped[str] = mapped_column(String(50), default="inspection", nullable=False)
    consent_recorded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # The EXIF-stripped bytes. Nullable so metadata can outlive purged bytes.
    image_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Labeling lifecycle: unlabeled -> labeled -> in_review -> gold | rejected.
    label_status: Mapped[str] = mapped_column(
        String(30), default="unlabeled", nullable=False, index=True
    )


class ImageLabel(Base):
    """A single (multi-label) annotation applied to a retained image.

    One image may carry several labels (e.g. rust + debris). Critical classes
    (blood, crack, missing_component) require two reviewers + adjudication before
    a label is promoted to ``gold``.
    """

    __tablename__ = "image_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    image_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), default="default-tenant", nullable=False, index=True
    )

    # The finding class, e.g. blood / rust / crack / clean.
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Per-finding severity using published scales (e.g. none/surface/moderate/heavy).
    severity: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    # Optional region for localizable findings: JSON [x,y,w,h] (normalized 0..1).
    region_json: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    reviewer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    # adjudication state for critical-class two-reviewer rule.
    adjudicated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_gold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
