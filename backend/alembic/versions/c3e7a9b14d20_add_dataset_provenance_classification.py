"""Add structured data-provenance classification to dataset_registry_entries.

Stage 4 — Data Provenance Enforcement. Clinical model promotion requires
VERIFIED, APPROVED ``real_clinical`` provenance recorded on the governed
``DatasetRegistryEntry`` rather than being inferred from facility-name strings.

Backfill is conservative and FAIL-CLOSED: the new columns' server-defaults make
every existing row ``data_provenance_class = 'legacy_unverified'`` and
``provenance_approval_status = 'pending'`` — so no historical row is silently
relabelled as clinical. An explicit, authorized governance review is required to
reclassify any legitimately-sourced clinical data (see
``provenance_governance.set_provenance_classification``). The downgrade drops the
columns only (no data is destroyed in upgrade).

Note: ``dataset_registry_entries`` is created at runtime by
``Base.metadata.create_all`` (+ ``column_migrator.ensure_all_columns``), not by
the Alembic chain. The pure-``alembic upgrade head`` CI step therefore runs
without that table present, and the pytest step creates it (with these columns
already on the model) via create_all. This migration is accordingly GUARDED: it
is a no-op when the table is absent, and otherwise adds only the columns/indexes
that are still missing — so it is correct and idempotent whether the table is
built by Alembic or by create_all, in either order.

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

_COLUMNS = [
    ("data_provenance_class", sa.String(length=40), "legacy_unverified"),
    ("provenance_source_id", sa.String(length=100), ""),
    ("provenance_source_version", sa.String(length=60), ""),
    ("provenance_source_institution", sa.String(length=255), ""),
    ("provenance_rights_evidence_ref", sa.String(length=255), ""),
    ("provenance_specimen_id", sa.String(length=255), ""),
    ("provenance_approval_status", sa.String(length=20), "pending"),
    ("provenance_approved_by", sa.String(length=255), ""),
]
_INDEXES = [
    ("ix_dataset_registry_entries_data_provenance_class", "data_provenance_class"),
    ("ix_dataset_registry_entries_provenance_approval_status", "provenance_approval_status"),
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(_TABLE):
        # Table is created by create_all with these columns already on the model.
        return
    existing_cols = {c["name"] for c in insp.get_columns(_TABLE)}
    for name, type_, default in _COLUMNS:
        if name not in existing_cols:
            op.add_column(_TABLE, sa.Column(name, type_, nullable=False, server_default=default))
    if "provenance_approved_at" not in existing_cols:
        op.add_column(_TABLE, sa.Column("provenance_approved_at", sa.DateTime(timezone=True), nullable=True))

    existing_idx = {ix["name"] for ix in insp.get_indexes(_TABLE)}
    for idx_name, column in _INDEXES:
        if idx_name not in existing_idx:
            op.create_index(idx_name, _TABLE, [column])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(_TABLE):
        return
    existing_idx = {ix["name"] for ix in insp.get_indexes(_TABLE)}
    for idx_name, _column in _INDEXES:
        if idx_name in existing_idx:
            op.drop_index(idx_name, table_name=_TABLE)
    existing_cols = {c["name"] for c in insp.get_columns(_TABLE)}
    for name in (
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
        if name in existing_cols:
            op.drop_column(_TABLE, name)
