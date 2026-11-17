"""Add scoped research provenance to retained_images (no ownership inference).

Revision ID: e8b2c6d49f10
Revises: c3e7a9b14d20

SEC-171-03 hardening (logic in ``app.db.migration_guards``, which is unit-testable): fails
LOUDLY when the prerequisite table is missing, verifies its own post-conditions so a failed
upgrade can never look successful, is non-destructive to existing records, and refuses a
downgrade that would silently drop research provenance.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# NOTE: ``app.db.migration_guards`` is imported lazily inside upgrade()/downgrade()
# rather than at module top. Importing it here pulls in the ``app`` package, which
# breaks ``alembic history``/``alembic heads`` (offline revision introspection that
# only parses revision metadata and never runs a migration) in any environment where
# ``app`` is not importable. The guards are only needed when a migration actually runs.

revision: str = "e8b2c6d49f10"
down_revision: Union[str, None] = "c3e7a9b14d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.migration_guards import (
        RETAINED_INDEX,
        RETAINED_TABLE,
        require_table,
        verify_retained_provenance_columns,
    )

    bind = op.get_bind()
    # 1-2) Validate the prerequisite table exists BEFORE modifying anything.
    require_table(bind, RETAINED_TABLE, revision=revision)

    # 3) Non-destructive, idempotent column adds (NOT NULL + safe server default so existing
    #    rows are preserved and backfilled, never rewritten/dropped).
    cols = {c["name"] for c in sa.inspect(bind).get_columns(RETAINED_TABLE)}
    if "research_dataset_id" not in cols:
        op.add_column(RETAINED_TABLE, sa.Column(
            "research_dataset_id", sa.String(length=255), nullable=False, server_default=""))
    if "research_owner_subject" not in cols:
        op.add_column(RETAINED_TABLE, sa.Column(
            "research_owner_subject", sa.String(length=255), nullable=False, server_default=""))
    if "research_attestation_id" not in cols:
        op.add_column(RETAINED_TABLE, sa.Column("research_attestation_id", sa.Integer(), nullable=True))
    if RETAINED_INDEX not in {i["name"] for i in sa.inspect(bind).get_indexes(RETAINED_TABLE)}:
        op.create_index(RETAINED_INDEX, RETAINED_TABLE, ["research_dataset_id"])

    # 4-5) Verify columns/nullability/index AFTER the change; a failure raises so a partial
    #      upgrade cannot be mistaken for success.
    verify_retained_provenance_columns(bind, revision=revision)


def downgrade() -> None:
    from app.db.migration_guards import (
        RETAINED_INDEX,
        RETAINED_TABLE,
        assert_retained_downgrade_allowed,
        require_table,
    )

    bind = op.get_bind()
    require_table(bind, RETAINED_TABLE, revision=revision)
    # 6) Prevent accidental loss of research provenance.
    assert_retained_downgrade_allowed(bind, revision=revision)

    if RETAINED_INDEX in {i["name"] for i in sa.inspect(bind).get_indexes(RETAINED_TABLE)}:
        op.drop_index(RETAINED_INDEX, table_name=RETAINED_TABLE)
    cols = {c["name"] for c in sa.inspect(bind).get_columns(RETAINED_TABLE)}
    for name in ("research_attestation_id", "research_owner_subject", "research_dataset_id"):
        if name in cols:
            op.drop_column(RETAINED_TABLE, name)
