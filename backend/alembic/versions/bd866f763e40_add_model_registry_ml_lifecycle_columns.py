"""add_model_registry_ml_lifecycle_columns

Backfills `model_registry` columns added by the ML governance / Genesis /
Project Lens lifecycle work (training reproducibility fields, the 5-stage
candidate promotion ladder, clinical/documentation/governance review
flags, and customer-approval fields) that were present in
`app/models/ml_governance.py`'s `ModelRegistryEntry` and exercised by the
test suite but never captured in a real Alembic revision. Distinct from
`b7c3d9f1a204` ("Add model_registry artifact integrity columns (Project
Lens)"), which already covers the artifact-checksum/preprocessing-version
fields — this migration only adds what that one did not.

Revision ID: bd866f763e40
Revises: b2f8c0452835
Create Date: 2026-07-16 02:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd866f763e40'
down_revision: Union[str, None] = 'b2f8c0452835'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('model_registry', sa.Column('architecture', sa.String(length=100), nullable=False, server_default=''))
    op.add_column('model_registry', sa.Column('framework', sa.String(length=60), nullable=False, server_default=''))
    op.add_column('model_registry', sa.Column('hyperparameters', sa.Text(), nullable=False, server_default='{}'))
    op.add_column('model_registry', sa.Column('git_commit', sa.String(length=64), nullable=False, server_default=''))
    op.add_column('model_registry', sa.Column('dataset_version_id', sa.Integer(), nullable=True))
    op.add_column('model_registry', sa.Column('training_metrics', sa.Text(), nullable=False, server_default='{}'))
    op.add_column('model_registry', sa.Column('documentation_complete', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('model_registry', sa.Column('clinical_review_complete', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('model_registry', sa.Column('metrics_approved', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('model_registry', sa.Column('model_card_markdown', sa.Text(), nullable=False, server_default=''))
    op.add_column('model_registry', sa.Column('training_run_id', sa.String(length=64), nullable=False, server_default=''))
    op.add_column('model_registry', sa.Column('reviewer', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('model_registry', sa.Column('clinical_review_status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('model_registry', sa.Column('deployment_status', sa.String(length=20), nullable=False, server_default='not_deployed'))
    op.add_column('model_registry', sa.Column('candidate_stage', sa.String(length=30), nullable=False, server_default='Experimental'))
    op.add_column('model_registry', sa.Column('error_analysis_reviewed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('model_registry', sa.Column('reproducible_training_confirmed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('model_registry', sa.Column('governance_review_completed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('model_registry', sa.Column('calibration_report', sa.Text(), nullable=False, server_default='{}'))
    op.add_column('model_registry', sa.Column('error_analysis_report', sa.Text(), nullable=False, server_default='{}'))
    op.add_column('model_registry', sa.Column('artifact_path', sa.String(length=500), nullable=False, server_default=''))
    op.add_column('model_registry', sa.Column('customer_approved', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('model_registry', sa.Column('customer_approved_by', sa.String(length=255), nullable=False, server_default=''))
    op.create_index(op.f('ix_model_registry_candidate_stage'), 'model_registry', ['candidate_stage'], unique=False)
    op.create_index(op.f('ix_model_registry_dataset_version_id'), 'model_registry', ['dataset_version_id'], unique=False)
    op.create_index(op.f('ix_model_registry_training_run_id'), 'model_registry', ['training_run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_registry_training_run_id'), table_name='model_registry')
    op.drop_index(op.f('ix_model_registry_dataset_version_id'), table_name='model_registry')
    op.drop_index(op.f('ix_model_registry_candidate_stage'), table_name='model_registry')
    op.drop_column('model_registry', 'customer_approved_by')
    op.drop_column('model_registry', 'customer_approved')
    op.drop_column('model_registry', 'artifact_path')
    op.drop_column('model_registry', 'error_analysis_report')
    op.drop_column('model_registry', 'calibration_report')
    op.drop_column('model_registry', 'governance_review_completed')
    op.drop_column('model_registry', 'reproducible_training_confirmed')
    op.drop_column('model_registry', 'error_analysis_reviewed')
    op.drop_column('model_registry', 'candidate_stage')
    op.drop_column('model_registry', 'deployment_status')
    op.drop_column('model_registry', 'clinical_review_status')
    op.drop_column('model_registry', 'reviewer')
    op.drop_column('model_registry', 'training_run_id')
    op.drop_column('model_registry', 'model_card_markdown')
    op.drop_column('model_registry', 'metrics_approved')
    op.drop_column('model_registry', 'clinical_review_complete')
    op.drop_column('model_registry', 'documentation_complete')
    op.drop_column('model_registry', 'training_metrics')
    op.drop_column('model_registry', 'dataset_version_id')
    op.drop_column('model_registry', 'git_commit')
    op.drop_column('model_registry', 'hyperparameters')
    op.drop_column('model_registry', 'framework')
    op.drop_column('model_registry', 'architecture')
