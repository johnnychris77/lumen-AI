"""Manufacturer-membership lifecycle columns (P472-03 Batch 5 B5.2, AW-07).

Adds nullable expiry, revocation and grant-provenance columns to
``manufacturer_memberships``:

* ``expires_at`` — when set and in the past, the membership counts as none
  (``require_manufacturer_auth`` refuses it). Fail closed.
* ``revoked_at`` / ``revoked_by`` / ``revocation_reason`` — written by
  ``manufacturer_membership_service.revoke_manufacturer_membership`` together
  with a hash-chained audit event.
* ``granted_by`` / ``grant_reference`` — written by the (gated) grant path.

No backfill: every column is NULL for existing rows, which preserves the
Batch 3 behaviour exactly (no expiry, no recorded provenance). Attributing
provenance to historical memberships is NOT done here — there is no reliable
source for it and guessing would fabricate an audit trail.

Revision ID: b5a2c7e19d40
Revises: e7c2a9f04b18
Create Date: 2026-11-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5a2c7e19d40"
down_revision: Union[str, None] = "e7c2a9f04b18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = (
    ("expires_at", sa.DateTime(timezone=True)),
    ("revoked_at", sa.DateTime(timezone=True)),
    ("revoked_by", sa.String(length=255)),
    ("revocation_reason", sa.String(length=500)),
    ("granted_by", sa.String(length=255)),
    ("grant_reference", sa.String(length=255)),
)


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("manufacturer_memberships")}
    for name, type_ in _COLUMNS:
        if name not in existing:  # idempotent if create_all already added them
            op.add_column("manufacturer_memberships", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    """Guarded: dropping ``expires_at`` would silently RE-ACTIVATE every expired
    membership (fail open), and dropping the provenance columns discards who
    revoked/granted what. Refuse while any row uses them, unless an operator
    explicitly sets ``LUMENAI_ALLOW_MANUFACTURER_LIFECYCLE_DOWNGRADE=1`` after
    disabling the affected memberships."""
    import os

    bind = op.get_bind()
    existing = {c["name"] for c in sa.inspect(bind).get_columns("manufacturer_memberships")}
    used = [name for name, _ in _COLUMNS if name in existing and bind.execute(
        sa.text(f"SELECT COUNT(*) FROM manufacturer_memberships WHERE {name} IS NOT NULL")).scalar()]
    if used and os.getenv("LUMENAI_ALLOW_MANUFACTURER_LIFECYCLE_DOWNGRADE") != "1":
        raise RuntimeError(
            "refusing to drop manufacturer-membership lifecycle columns that hold data "
            f"({', '.join(used)}): expired memberships would become active again. Disable them first and set "
            "LUMENAI_ALLOW_MANUFACTURER_LIFECYCLE_DOWNGRADE=1.")
    for name, _ in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("manufacturer_memberships", name)
