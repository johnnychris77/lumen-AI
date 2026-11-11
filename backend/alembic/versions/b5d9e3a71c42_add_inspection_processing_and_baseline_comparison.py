"""Add temporary inspection-image processing store + persisted baseline comparison.

Two related additions that make a real manufacturer baseline image comparison
operational without coupling it to opt-in training retention:

  * ``inspection_processing_images`` — a bounded, tenant-scoped, EXIF-stripped
    temporary store for the inspection pixels needed to run the comparison the
    user requested. Never read by the training/dataset pipeline; purged when the
    inspection is processed or the row expires.
  * ``inspections.baseline_comparison_*`` columns — persist the comparison result
    at analysis time so the report and history show the same result the New
    Inspection page did, without re-reading the (now purged) inspection pixels.

The SQLite CI job builds its schema with create_all (picks these up from the
models automatically); the PostgreSQL job builds from the Alembic chain, so the
column/table need this migration.

Revision ID: b5d9e3a71c42
Revises: a1b2c3d4e5f6
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5d9e3a71c42"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inspection_processing_images",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("image_sha256", sa.String(length=64), nullable=False),
        sa.Column("stored_sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("uploaded_by", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("inspection_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_inspection_processing_images_tenant_id", "inspection_processing_images", ["tenant_id"])
    op.create_index("ix_inspection_processing_images_image_sha256", "inspection_processing_images", ["image_sha256"])
    op.create_index("ix_inspection_processing_images_status", "inspection_processing_images", ["status"])
    op.create_index("ix_inspection_processing_images_expires_at", "inspection_processing_images", ["expires_at"])
    op.create_index("ix_inspection_processing_images_inspection_id", "inspection_processing_images", ["inspection_id"])
    op.create_index("ix_inspection_processing_images_created_at", "inspection_processing_images", ["created_at"])

    for name, type_ in (
        ("baseline_image_link_id", sa.Integer()),
        ("baseline_comparison_status", sa.String(length=40)),
        ("baseline_comparison_similarity", sa.Float()),
        ("baseline_comparison_method", sa.String(length=60)),
        ("baseline_comparison_version", sa.String(length=60)),
        ("baseline_reference_version", sa.String(length=40)),
    ):
        op.add_column("inspections", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name in (
        "baseline_reference_version", "baseline_comparison_version", "baseline_comparison_method",
        "baseline_comparison_similarity", "baseline_comparison_status", "baseline_image_link_id",
    ):
        op.drop_column("inspections", name)
    op.drop_table("inspection_processing_images")
