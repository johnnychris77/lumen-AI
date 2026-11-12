"""Add structured data-provenance classification to dataset_registry_entries.

Stage 4 — Data Provenance Enforcement. Clinical model promotion requires
VERIFIED, APPROVED ``real_clinical`` provenance recorded on the governed
``DatasetRegistryEntry`` rather than being inferred from facility-name strings.

Backfill is conservative and FAIL-CLOSED: every existing row takes the column
server-defaults ``data_provenance_class = 'legacy_unverified'`` and
``provenance_approval_status = 'pending'`` — so no historical row is silently
relabelled as clinical. An explicit, authorized governance review is required to
reclassify any legitimately-sourced clinical data (see
``provenance_governance.set_provenance_classification``). The downgrade drops the
columns only (no data is destroyed in upgrade).

The SQLite CI job builds its schema with create_all (which picks up the new model
columns automatically); the PostgreSQL job builds from this Alembic chain.

Revision ID: c3e7a9b14d20
Revises: b5d9e3a71c42
Create Date: 2026-11-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3e7a9b14d20"
down_revision: Union[str, None] = "b5d9e3a71c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "dataset_registry_entries"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column(
            "data_provenance_class",
            sa.String(length=40),
            nullable=False,
            server_default="legacy_unverified",
        ),
    )
    op.add_column(_TABLE, sa.Column("provenance_source_id", sa.String(length=100), nullable=False, server_default=""))
    op.add_column(_TABLE, sa.Column("provenance_source_version", sa.String(length=60), nullable=False, server_default=""))
    op.add_column(
        _TABLE, sa.Column("provenance_source_institution", sa.String(length=255), nullable=False, server_default="")
    )
    op.add_column(
        _TABLE, sa.Column("provenance_rights_evidence_ref", sa.String(length=255), nullable=False, server_default="")
    )
    op.add_column(_TABLE, sa.Column("provenance_specimen_id", sa.String(length=255), nullable=False, server_default=""))
    op.add_column(
        _TABLE,
        sa.Column(
            "provenance_approval_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(_TABLE, sa.Column("provenance_approved_by", sa.String(length=255), nullable=False, server_default=""))
    op.add_column(_TABLE, sa.Column("provenance_approved_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(
        "ix_dataset_registry_entries_data_provenance_class", _TABLE, ["data_provenance_class"]
    )
    op.create_index(
        "ix_dataset_registry_entries_provenance_approval_status", _TABLE, ["provenance_approval_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_dataset_registry_entries_provenance_approval_status", table_name=_TABLE)
    op.drop_index("ix_dataset_registry_entries_data_provenance_class", table_name=_TABLE)
    for col in (
        "provenance_approved_at",
        "provenance_approved_by",
        "provenance_approval_status",
        "provenance_specimen_id",
        "provenance_rights_evidence_ref",
        "provenance_source_institution",
        "provenance_source_version",
        "provenance_source_id",
        "data_provenance_class",
    ):
        op.drop_column(_TABLE, col)
