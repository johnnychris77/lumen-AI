"""Add tenant_id to vendor baseline tables (GD-3 tenant privacy).

Governance decision GD-3: vendor baselines are tenant-private. The owning
tenant is stamped from the verified tenant of the submitting request and every
read/approval/scoring/audit lookup is scoped to the caller's tenant.

Both columns are nullable with no server default: rows written before GD-3 keep
tenant_id = NULL. An unattributed (NULL) row is deliberately visible to no
tenant — tenant-scoped reads filter on an explicit tenant value, so NULL never
matches. This is fail-closed and is a documented deployment precondition:
existing baselines are unreachable (and therefore cannot drive clinical scoring)
until the baseline workflow owner attributes them to a tenant. We do NOT invent
a tenant here, because guessing an owner would re-expose exactly the cross-tenant
data GD-3 closes.

The SQLite CI job builds its schema with create_all (which picks up the new
model columns automatically); the PostgreSQL job builds from the Alembic chain,
so the columns need this migration or every vendor-baseline query that filters on
tenant_id fails with "column ... does not exist".

Revision ID: d8f3a6b914c7
Revises: c9d1f7a3e5b2
Create Date: 2026-11-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8f3a6b914c7"
down_revision: Union[str, None] = "c9d1f7a3e5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "enterprise_vendor_baseline_subscriptions",
        sa.Column("tenant_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_enterprise_vendor_baseline_subscriptions_tenant_id",
        "enterprise_vendor_baseline_subscriptions",
        ["tenant_id"],
    )

    op.add_column(
        "vendor_baseline_audit_events",
        sa.Column("tenant_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_vendor_baseline_audit_events_tenant_id",
        "vendor_baseline_audit_events",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_vendor_baseline_audit_events_tenant_id",
        table_name="vendor_baseline_audit_events",
    )
    op.drop_column("vendor_baseline_audit_events", "tenant_id")

    op.drop_index(
        "ix_enterprise_vendor_baseline_subscriptions_tenant_id",
        table_name="enterprise_vendor_baseline_subscriptions",
    )
    op.drop_column("enterprise_vendor_baseline_subscriptions", "tenant_id")
