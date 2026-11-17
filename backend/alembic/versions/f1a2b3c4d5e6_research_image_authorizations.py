"""SEC-171-04: per-owner research-image authorization association table.

Revision ID: f1a2b3c4d5e6
Revises: e8b2c6d49f10

Creates ``research_image_authorizations`` so ownership of a retained research image is an
explicit, per-owner association rather than an inference from matching bytes. Fails loudly
when prerequisites are missing, verifies its own post-conditions, is non-destructive, and
refuses a downgrade that would drop active authorizations (logic in
``app.db.migration_guards``).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.migration_guards import (
    MigrationSchemaError,
    assert_association_downgrade_allowed,
    require_table,
)

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e8b2c6d49f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "research_image_authorizations"
_PREREQ = ("retained_images", "governance_approvals")
_UQ = "uq_research_image_auth_owner"
_EXPECTED_COLS = {
    "id", "created_at", "withdrawn_at", "tenant_id", "retained_image_id",
    "research_dataset_id", "owner_actor", "owner_subject", "attestation_id", "status",
}
_INDEXES = (
    ("ix_research_image_authorizations_tenant_id", ["tenant_id"]),
    ("ix_research_image_authorizations_retained_image_id", ["retained_image_id"]),
    ("ix_research_image_authorizations_research_dataset_id", ["research_dataset_id"]),
    ("ix_research_image_authorizations_status", ["status"]),
    ("ix_research_image_auth_image_status", ["retained_image_id", "status"]),
    ("ix_research_image_auth_tenant_owner", ["tenant_id", "owner_subject"]),
)


def upgrade() -> None:
    bind = op.get_bind()
    # Validate prerequisite (FK target) tables BEFORE creating anything.
    for table in _PREREQ:
        require_table(bind, table, revision=revision)

    insp = sa.inspect(bind)
    if not insp.has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("tenant_id", sa.String(length=100), nullable=False),
            sa.Column("retained_image_id", sa.Integer(), nullable=False),
            sa.Column("research_dataset_id", sa.String(length=255), nullable=False),
            sa.Column("owner_actor", sa.String(length=255), nullable=False),
            sa.Column("owner_subject", sa.String(length=255), nullable=False),
            sa.Column("attestation_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.ForeignKeyConstraint(["retained_image_id"], ["retained_images.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["attestation_id"], ["governance_approvals.id"]),
            sa.UniqueConstraint("tenant_id", "retained_image_id", "research_dataset_id",
                                "owner_subject", name=_UQ),
        )
        existing_idx: set = set()
    else:
        existing_idx = {i["name"] for i in insp.get_indexes(_TABLE)}

    for name, cols in _INDEXES:
        if name not in existing_idx:
            op.create_index(name, _TABLE, cols)

    # Verify post-conditions; raise (never silently succeed) if anything is missing.
    insp = sa.inspect(bind)
    if not insp.has_table(_TABLE):
        raise MigrationSchemaError(f"Migration {revision}: table '{_TABLE}' missing after upgrade.")
    present = {c["name"] for c in insp.get_columns(_TABLE)}
    missing = _EXPECTED_COLS - present
    if missing:
        raise MigrationSchemaError(
            f"Migration {revision}: expected columns missing after upgrade: {sorted(missing)}.")
    uqs = {u["name"] for u in insp.get_unique_constraints(_TABLE)}
    idxs = {i["name"] for i in insp.get_indexes(_TABLE)}
    if _UQ not in uqs and _UQ not in idxs:
        raise MigrationSchemaError(
            f"Migration {revision}: expected unique constraint '{_UQ}' missing after upgrade.")


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(_TABLE):
        return
    assert_association_downgrade_allowed(bind, _TABLE, revision=revision)
    op.drop_table(_TABLE)
