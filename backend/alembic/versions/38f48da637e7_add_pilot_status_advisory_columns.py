"""add_pilot_status_advisory_columns

Backfills `pilot_status` columns added by the Advisor pilot-governance
work (`app/models/pilot.py`'s `PilotStatus`) — named stakeholder roles and
planned pilot duration — which were present in the ORM model and
exercised by the test suite but never captured in a real Alembic
revision.

Revision ID: 38f48da637e7
Revises: bd866f763e40
Create Date: 2026-07-16 02:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38f48da637e7'
down_revision: Union[str, None] = 'bd866f763e40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pilot_status', sa.Column('organization', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('department', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('clinical_lead', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('technical_lead', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('quality_lead', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('validation_coordinator', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('pilot_sponsor', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('product_owner', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('engineering_lead', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('success_criteria', sa.Text(), nullable=False, server_default=''))
    op.add_column('pilot_status', sa.Column('pilot_duration_days', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('pilot_status', 'pilot_duration_days')
    op.drop_column('pilot_status', 'success_criteria')
    op.drop_column('pilot_status', 'engineering_lead')
    op.drop_column('pilot_status', 'product_owner')
    op.drop_column('pilot_status', 'pilot_sponsor')
    op.drop_column('pilot_status', 'validation_coordinator')
    op.drop_column('pilot_status', 'quality_lead')
    op.drop_column('pilot_status', 'technical_lead')
    op.drop_column('pilot_status', 'clinical_lead')
    op.drop_column('pilot_status', 'department')
    op.drop_column('pilot_status', 'organization')
