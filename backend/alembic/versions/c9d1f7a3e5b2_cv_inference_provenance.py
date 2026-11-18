"""P4.7.2: server-issued provenance for trusted CV inference runs.

Adds ``cv_inference_provenance``. A ``cv_inference_records`` row counts as
verified model inference only while one row here refers to it, is in the
``trusted`` state, and carries a seal that verifies under the server's
provenance key (see ``app.cv.provenance``).

No backfill, by design: this migration writes NO provenance rows. Every record
that exists before it runs therefore has no independently verifiable provenance
and classifies as ``legacy_unverified``. Sealing historic records would be
fabricating an approval nobody gave.

Idempotent: the application's startup ``create_all`` may already have created
the table (SQLite test databases and deployments that do not run Alembic get it
that way), so an existing table is left in place.

Downgrade refuses to drop provenance rows unless
``LUMENAI_ALLOW_PROVENANCE_DOWNGRADE`` is set: dropping the table silently turns
every verified record into ``legacy_unverified`` and discards the revocation
record.

Revision ID: c9d1f7a3e5b2
Revises: b5d9e3a71c42
Create Date: 2026-11-18
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d1f7a3e5b2"
down_revision: Union[str, None] = "b5d9e3a71c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "cv_inference_provenance"
_INDEXES = (
    ("ix_cv_inference_provenance_id", ["id"]),
    ("ix_cv_inference_provenance_record_id", ["record_id"]),
    ("ix_cv_inference_provenance_inference_id", ["inference_id"]),
    ("ix_cv_inference_provenance_tenant_id", ["tenant_id"]),
    ("ix_cv_inference_provenance_state", ["state"]),
)
_TRUTHY = {"1", "true", "yes", "on", "enabled"}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("record_id", sa.Integer(), nullable=False),
            sa.Column("inference_id", sa.String(length=100), nullable=False),
            sa.Column("tenant_id", sa.String(length=100), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("execution_status", sa.String(length=20), nullable=False),
            sa.Column("model_versions_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("artifact_digests_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("record_digest", sa.String(length=64), nullable=False),
            sa.Column("state", sa.String(length=20), nullable=False, server_default="trusted"),
            sa.Column("key_id", sa.String(length=64), nullable=False),
            sa.Column("attestation", sa.String(length=64), nullable=False),
            sa.Column("issued_at", sa.String(length=40), nullable=False),
            sa.Column("revoked_at", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("revoked_by", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("revoked_reason", sa.String(length=255), nullable=False, server_default=""),
            sa.ForeignKeyConstraint(
                ["record_id"], ["cv_inference_records.id"], ondelete="CASCADE",
            ),
            sa.UniqueConstraint("record_id", name="uq_cv_inference_provenance_record"),
            sa.UniqueConstraint("inference_id", name="uq_cv_inference_provenance_inference"),
        )
        existing_indexes: set[str] = set()
    else:
        existing_indexes = {i["name"] for i in inspector.get_indexes(_TABLE)}
    for name, columns in _INDEXES:
        if name not in existing_indexes:
            op.create_index(name, _TABLE, columns)


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(_TABLE):
        return
    has_rows = bind.execute(sa.text(f"SELECT 1 FROM {_TABLE} LIMIT 1")).first() is not None
    override = os.getenv("LUMENAI_ALLOW_PROVENANCE_DOWNGRADE", "").strip().lower() in _TRUTHY
    if has_rows and not override:
        raise RuntimeError(
            f"Downgrade of {revision} refused: '{_TABLE}' holds inference provenance. Dropping "
            "it would turn every verified record into legacy_unverified and discard the "
            "revocation record. Set LUMENAI_ALLOW_PROVENANCE_DOWNGRADE=1 to override after "
            "confirming the data is archived."
        )
    op.drop_table(_TABLE)
