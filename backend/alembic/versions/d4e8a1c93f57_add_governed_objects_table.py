"""Add governed_objects table (Project Foundation Sprint 1 — GPAE).

Registry for every object placed in governed object storage: permanent
Object ID, SHA-256, uploader, tenant, retention policy, storage URI,
version chain, and integrity bookkeeping.

Revision ID: d4e8a1c93f57
Revises: 5b7eb6e147e2
Create Date: 2026-07-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8a1c93f57"
down_revision: Union[str, None] = "5b7eb6e147e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "governed_objects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("object_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("object_category", sa.String(length=50), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploader", sa.String(length=255), nullable=False),
        sa.Column("retention_policy", sa.String(length=50), nullable=False),
        sa.Column("storage_backend", sa.String(length=20), nullable=False),
        sa.Column("storage_uri", sa.String(length=1000), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("supersedes_object_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("integrity_intact", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("tenant_id", "sha256", name="uq_governed_objects_tenant_sha256"),
    )
    op.create_index("ix_governed_objects_id", "governed_objects", ["id"])
    op.create_index("ix_governed_objects_object_id", "governed_objects", ["object_id"], unique=True)
    op.create_index("ix_governed_objects_tenant_id", "governed_objects", ["tenant_id"])
    op.create_index("ix_governed_objects_sha256", "governed_objects", ["sha256"])
    op.create_index("ix_governed_objects_object_category", "governed_objects", ["object_category"])
    op.create_index("ix_governed_objects_status", "governed_objects", ["status"])


def downgrade() -> None:
    op.drop_index("ix_governed_objects_status", table_name="governed_objects")
    op.drop_index("ix_governed_objects_object_category", table_name="governed_objects")
    op.drop_index("ix_governed_objects_sha256", table_name="governed_objects")
    op.drop_index("ix_governed_objects_tenant_id", table_name="governed_objects")
    op.drop_index("ix_governed_objects_object_id", table_name="governed_objects")
    op.drop_index("ix_governed_objects_id", table_name="governed_objects")
    op.drop_table("governed_objects")
