"""Add scoped research provenance to retained_images (no ownership inference).

Revision ID: e8b2c6d49f10
Revises: c3e7a9b14d20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8b2c6d49f10"
down_revision: Union[str, None] = "c3e7a9b14d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "retained_images"
_INDEX = "ix_retained_images_research_dataset_id"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(_TABLE):
        return
    cols = {col["name"] for col in insp.get_columns(_TABLE)}
    if "research_dataset_id" not in cols:
        op.add_column(_TABLE, sa.Column(
            "research_dataset_id", sa.String(length=255),
            nullable=False, server_default="",
        ))
    if "research_owner_subject" not in cols:
        op.add_column(_TABLE, sa.Column(
            "research_owner_subject", sa.String(length=255),
            nullable=False, server_default="",
        ))
    if "research_attestation_id" not in cols:
        op.add_column(_TABLE, sa.Column("research_attestation_id", sa.Integer(), nullable=True))
    if _INDEX not in {i["name"] for i in sa.inspect(bind).get_indexes(_TABLE)}:
        op.create_index(_INDEX, _TABLE, ["research_dataset_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(_TABLE):
        return
    if _INDEX in {i["name"] for i in insp.get_indexes(_TABLE)}:
        op.drop_index(_INDEX, table_name=_TABLE)
    cols = {col["name"] for col in insp.get_columns(_TABLE)}
    for name in ("research_attestation_id", "research_owner_subject", "research_dataset_id"):
        if name in cols:
            op.drop_column(_TABLE, name)
