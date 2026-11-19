"""Add manufacturer_memberships table (P472-03 AW-07 manufacturer identity).

AW-07: ``require_manufacturer_auth`` returned the client-supplied
``X-Manufacturer-ID`` header with no binding between the authenticated principal
and the claimed manufacturer, so any authenticated hospital user could assume any
manufacturer / repair-partner identity.

This table binds a user to the external organizations they are a verified member
of, exactly as ``tenant_memberships`` binds a user to tenants. The manufacturer /
repair-partner identity a request acts under is resolved from an enabled
membership; a header naming any other organization is refused (fail closed).

There is no backfill: with no membership rows, every manufacturer-portal request
is refused until an authorized manufacturer-onboarding workflow attributes
memberships. This is a documented deployment precondition (fail closed), and is
intentional — guessing a manufacturer relationship would re-open AW-07.

The SQLite CI job builds its schema with create_all (which picks up the new
model automatically); the PostgreSQL job builds from the Alembic chain, so the
table needs this migration.

Revision ID: e7c2a9f04b18
Revises: d8f3a6b914c7
Create Date: 2026-11-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7c2a9f04b18"
down_revision: Union[str, None] = "d8f3a6b914c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "manufacturer_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("manufacturer_id", sa.String(length=255), nullable=False),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False, server_default="manufacturer_viewer"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_email", "manufacturer_id", name="uq_manufacturer_membership_user_org"),
    )
    op.create_index(
        "ix_manufacturer_memberships_manufacturer_id",
        "manufacturer_memberships",
        ["manufacturer_id"],
    )
    op.create_index(
        "ix_manufacturer_memberships_user_email",
        "manufacturer_memberships",
        ["user_email"],
    )


def downgrade() -> None:
    op.drop_index("ix_manufacturer_memberships_user_email", table_name="manufacturer_memberships")
    op.drop_index("ix_manufacturer_memberships_manufacturer_id", table_name="manufacturer_memberships")
    op.drop_table("manufacturer_memberships")
