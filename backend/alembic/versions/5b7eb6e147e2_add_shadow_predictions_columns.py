"""add_shadow_predictions_columns

Backfills `shadow_predictions` columns added by the Shadow-Mode
prospective clinical validation sprint (`app/models/shadow_prediction.py`)
— instrument/anatomy context for drift analysis, facility scoping, the
comparison-category classification, and the reveal-gate fields that keep
ground truth blind from the model during the shadow period — which were
present in the ORM model and exercised by the test suite but never
captured in a real Alembic revision. This is the final migration in the
pre-existing-drift backfill series (`367bc3527700` ->
`b2f8c0452835` -> `bd866f763e40` -> `38f48da637e7` -> here); after this,
`alembic upgrade head` against a fresh database matches every current
model with zero remaining autogenerate diff.

Revision ID: 5b7eb6e147e2
Revises: 38f48da637e7
Create Date: 2026-07-16 02:34:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b7eb6e147e2'
down_revision: Union[str, None] = '38f48da637e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shadow_predictions', sa.Column('image_quality', sa.String(length=20), nullable=False, server_default=''))
    op.add_column('shadow_predictions', sa.Column('anatomy_zone', sa.String(length=60), nullable=False, server_default=''))
    op.add_column('shadow_predictions', sa.Column('instrument_family', sa.String(length=60), nullable=False, server_default=''))
    op.add_column('shadow_predictions', sa.Column('facility_id', sa.String(length=100), nullable=False, server_default=''))
    op.add_column('shadow_predictions', sa.Column('comparison_category', sa.String(length=30), nullable=False, server_default=''))
    op.add_column('shadow_predictions', sa.Column('revealed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('shadow_predictions', sa.Column('revealed_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_shadow_predictions_comparison_category'), 'shadow_predictions', ['comparison_category'], unique=False)
    op.create_index(op.f('ix_shadow_predictions_facility_id'), 'shadow_predictions', ['facility_id'], unique=False)
    op.create_index(op.f('ix_shadow_predictions_instrument_family'), 'shadow_predictions', ['instrument_family'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_shadow_predictions_instrument_family'), table_name='shadow_predictions')
    op.drop_index(op.f('ix_shadow_predictions_facility_id'), table_name='shadow_predictions')
    op.drop_index(op.f('ix_shadow_predictions_comparison_category'), table_name='shadow_predictions')
    op.drop_column('shadow_predictions', 'revealed_at')
    op.drop_column('shadow_predictions', 'revealed')
    op.drop_column('shadow_predictions', 'comparison_category')
    op.drop_column('shadow_predictions', 'facility_id')
    op.drop_column('shadow_predictions', 'instrument_family')
    op.drop_column('shadow_predictions', 'anatomy_zone')
    op.drop_column('shadow_predictions', 'image_quality')
