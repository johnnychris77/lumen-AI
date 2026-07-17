"""Widen VARCHAR columns the application overflows (GPAE Foundation).

Found by the first executed PostgreSQL verification run: SQLite ignores
VARCHAR lengths, so these columns silently held values longer than their
declared width. PostgreSQL enforces the widths and raised
StringDataRightTruncation for values the app itself writes (e.g. the
inspection disposition "AI ANALYSIS UNAVAILABLE — MANUAL INSPECTION
REQUIRED" and full-sentence AI recommendations).

Revision ID: e7b2f4a86c31
Revises: d4e8a1c93f57
Create Date: 2026-07-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7b2f4a86c31"
down_revision: Union[str, None] = "d4e8a1c93f57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHANGES = [
    # (table, column, old_len, new_len)
    ("inspections", "disposition", 30, 120),
    ("supervisor_reviews", "ai_recommendation", 50, 255),
    ("supervisor_reviews", "corrected_recommendation", 50, 255),
    ("supervisor_reviews", "final_disposition", 50, 120),
]


def upgrade() -> None:
    for table, column, old_len, new_len in _CHANGES:
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=old_len),
            type_=sa.String(length=new_len),
            existing_nullable=True if column == "disposition" else False,
        )
    # Audit evidence must never be silently truncated: real events
    # (compliance evidence bundles) exceed 4000 chars and PostgreSQL
    # rejected them outright.
    op.alter_column(
        "audit_logs",
        "details",
        existing_type=sa.String(length=4000),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Narrowing can truncate data; values longer than the old width would be
    # rejected by PostgreSQL. Downgrade is intentionally a no-op for safety —
    # the wider column accepts every value the narrower one did.
    pass
