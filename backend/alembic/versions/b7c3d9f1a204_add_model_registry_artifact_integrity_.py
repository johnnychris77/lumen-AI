"""Add model_registry artifact integrity columns (Project Lens)

Revision ID: b7c3d9f1a204
Revises: a1ba6c5ed8f8
Create Date: 2026-07-15 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c3d9f1a204"
down_revision: Union[str, None] = "a1ba6c5ed8f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "model_registry",
        sa.Column("artifact_checksum", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "model_registry",
        sa.Column("preprocessing_version", sa.String(length=60), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("model_registry", "preprocessing_version")
    op.drop_column("model_registry", "artifact_checksum")
