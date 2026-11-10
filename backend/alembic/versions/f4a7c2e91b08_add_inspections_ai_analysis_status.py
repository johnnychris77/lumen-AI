"""Add inspections.ai_analysis_status (placeholder-score integrity).

The clinical outcome is governed by the authoritative live-model surface
(ai_analysis.status), persisted on each inspection as ai_analysis_status
("COMPLETED" | "AI_UNAVAILABLE" | ""). History/exports/PDF gate presentation on
this so a deterministic-placeholder score is never shown as a verified AI result.

The SQLite CI job builds its schema with create_all (which picked up the new
model column automatically); the PostgreSQL job builds from the Alembic chain,
so the column needs this migration or every inspections query fails with
"column inspections.ai_analysis_status does not exist".

Revision ID: f4a7c2e91b08
Revises: e7b2f4a86c31
Create Date: 2026-11-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4a7c2e91b08"
down_revision: Union[str, None] = "e7b2f4a86c31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inspections",
        sa.Column(
            "ai_analysis_status",
            sa.String(length=30),
            nullable=False,
            server_default="",
        ),
    )
    op.create_index(
        "ix_inspections_ai_analysis_status",
        "inspections",
        ["ai_analysis_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_inspections_ai_analysis_status", table_name="inspections")
    op.drop_column("inspections", "ai_analysis_status")
