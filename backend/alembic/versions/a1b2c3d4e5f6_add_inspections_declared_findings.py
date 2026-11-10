"""Add inspections.declared_findings (durable technician-declared observations).

Technician-declared finding categories are a HUMAN observation, never an AI
detection. Previously they existed only in the transient analysis response, so
on the AI-unavailable path (no AI finding persisted) the human's own declaration
disappeared from the durable clinical record. This JSON-encoded column preserves
them with explicit human provenance so history and reports can surface them,
kept distinct from AI findings.

The SQLite CI job builds its schema with create_all (which picks up the new
model column automatically); the PostgreSQL job builds from the Alembic chain,
so the column needs this migration or every inspections query fails with
"column inspections.declared_findings does not exist".

Revision ID: a1b2c3d4e5f6
Revises: f4a7c2e91b08
Create Date: 2026-11-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f4a7c2e91b08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inspections",
        sa.Column(
            "declared_findings",
            sa.String(length=500),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("inspections", "declared_findings")
