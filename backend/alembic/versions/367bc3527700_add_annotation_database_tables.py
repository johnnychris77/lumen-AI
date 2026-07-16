"""add_annotation_database_tables

Backfills the Annotation Database & Storage System sprint
(`app/models/annotation_database.py`) — the authoritative `Annotation`
entity, its version history, multi-reviewer records, and the sequence
counter used to mint `ann_id` values. These tables have existed in the
ORM models and been exercised by the full test suite (built via
`create_all()`) since that sprint, but no Alembic revision was ever
generated for them — this migration closes that gap so `alembic upgrade
head` against a fresh database actually creates them.

Revision ID: 367bc3527700
Revises: c1d4a7f2b8e6
Create Date: 2026-07-16 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '367bc3527700'
down_revision: Union[str, None] = 'c1d4a7f2b8e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('annotation_reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('annotation_id', sa.Integer(), nullable=False),
    sa.Column('primary_reviewer', sa.String(length=255), nullable=False),
    sa.Column('primary_label', sa.String(length=80), nullable=False),
    sa.Column('primary_confidence', sa.Float(), nullable=True),
    sa.Column('primary_submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('primary_comments', sa.Text(), nullable=False),
    sa.Column('secondary_reviewer', sa.String(length=255), nullable=False),
    sa.Column('secondary_label', sa.String(length=80), nullable=False),
    sa.Column('secondary_confidence', sa.Float(), nullable=True),
    sa.Column('secondary_submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('secondary_comments', sa.Text(), nullable=False),
    sa.Column('agreement', sa.Boolean(), nullable=True),
    sa.Column('disagreement_reason', sa.Text(), nullable=False),
    sa.Column('adjudicator', sa.String(length=255), nullable=False),
    sa.Column('resolution', sa.String(length=80), nullable=False),
    sa.Column('adjudication_reason', sa.Text(), nullable=False),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_annotation_reviews_annotation_id'), 'annotation_reviews', ['annotation_id'], unique=False)
    op.create_index(op.f('ix_annotation_reviews_created_at'), 'annotation_reviews', ['created_at'], unique=False)
    op.create_index(op.f('ix_annotation_reviews_id'), 'annotation_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_annotation_reviews_tenant_id'), 'annotation_reviews', ['tenant_id'], unique=False)
    op.create_table('annotation_sequence_counters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('last_sequence', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_annotation_sequence_counters_id'), 'annotation_sequence_counters', ['id'], unique=False)
    op.create_index(op.f('ix_annotation_sequence_counters_year'), 'annotation_sequence_counters', ['year'], unique=True)
    op.create_table('annotation_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('annotation_id', sa.Integer(), nullable=False),
    sa.Column('version_number', sa.Integer(), nullable=False),
    sa.Column('editor', sa.String(length=255), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('previous_version_id', sa.Integer(), nullable=True),
    sa.Column('snapshot_json', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_annotation_versions_annotation_id'), 'annotation_versions', ['annotation_id'], unique=False)
    op.create_index(op.f('ix_annotation_versions_created_at'), 'annotation_versions', ['created_at'], unique=False)
    op.create_index(op.f('ix_annotation_versions_id'), 'annotation_versions', ['id'], unique=False)
    op.create_index(op.f('ix_annotation_versions_tenant_id'), 'annotation_versions', ['tenant_id'], unique=False)
    op.create_table('annotations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('ann_id', sa.String(length=32), nullable=False),
    sa.Column('retained_image_id', sa.Integer(), nullable=False),
    sa.Column('inspection_id', sa.Integer(), nullable=True),
    sa.Column('instrument_family', sa.String(length=100), nullable=False),
    sa.Column('instrument_model', sa.String(length=100), nullable=False),
    sa.Column('manufacturer', sa.String(length=100), nullable=False),
    sa.Column('digital_twin_id', sa.String(length=255), nullable=False),
    sa.Column('baseline_id', sa.Integer(), nullable=True),
    sa.Column('reviewer', sa.String(length=255), nullable=False),
    sa.Column('dataset_version_id', sa.Integer(), nullable=True),
    sa.Column('ground_truth_version', sa.Integer(), nullable=False),
    sa.Column('model_version', sa.String(length=50), nullable=False),
    sa.Column('primary_observation', sa.String(length=80), nullable=False),
    sa.Column('secondary_observation', sa.String(length=80), nullable=False),
    sa.Column('appearance_attributes_json', sa.Text(), nullable=False),
    sa.Column('severity', sa.String(length=20), nullable=False),
    sa.Column('location', sa.String(length=100), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('reviewer_confidence', sa.Float(), nullable=True),
    sa.Column('comments', sa.Text(), nullable=False),
    sa.Column('recommendation', sa.String(length=60), nullable=False),
    sa.Column('supervisor_required', sa.Boolean(), nullable=False),
    sa.Column('unknown_flag', sa.Boolean(), nullable=False),
    sa.Column('image_quality', sa.String(length=20), nullable=False),
    sa.Column('region_type', sa.String(length=30), nullable=False),
    sa.Column('region_coordinates_json', sa.Text(), nullable=False),
    sa.Column('review_status', sa.String(length=20), nullable=False),
    sa.Column('ground_truth_status', sa.String(length=20), nullable=False),
    sa.Column('current_version', sa.Integer(), nullable=False),
    sa.Column('baseline_type', sa.String(length=30), nullable=False),
    sa.Column('baseline_version', sa.String(length=50), nullable=False),
    sa.Column('baseline_similarity', sa.Float(), nullable=True),
    sa.Column('baseline_deviation', sa.Float(), nullable=True),
    sa.Column('supervisor_classification', sa.String(length=255), nullable=True),
    sa.Column('clinical_review_status', sa.String(length=30), nullable=False),
    sa.Column('candidate_label', sa.String(length=255), nullable=True),
    sa.Column('promotion_status', sa.String(length=30), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_annotations_ann_id'), 'annotations', ['ann_id'], unique=True)
    op.create_index(op.f('ix_annotations_baseline_id'), 'annotations', ['baseline_id'], unique=False)
    op.create_index(op.f('ix_annotations_created_at'), 'annotations', ['created_at'], unique=False)
    op.create_index(op.f('ix_annotations_dataset_version_id'), 'annotations', ['dataset_version_id'], unique=False)
    op.create_index(op.f('ix_annotations_digital_twin_id'), 'annotations', ['digital_twin_id'], unique=False)
    op.create_index(op.f('ix_annotations_ground_truth_status'), 'annotations', ['ground_truth_status'], unique=False)
    op.create_index(op.f('ix_annotations_id'), 'annotations', ['id'], unique=False)
    op.create_index(op.f('ix_annotations_inspection_id'), 'annotations', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_annotations_instrument_family'), 'annotations', ['instrument_family'], unique=False)
    op.create_index(op.f('ix_annotations_primary_observation'), 'annotations', ['primary_observation'], unique=False)
    op.create_index(op.f('ix_annotations_retained_image_id'), 'annotations', ['retained_image_id'], unique=False)
    op.create_index(op.f('ix_annotations_review_status'), 'annotations', ['review_status'], unique=False)
    op.create_index(op.f('ix_annotations_tenant_id'), 'annotations', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_annotations_unknown_flag'), 'annotations', ['unknown_flag'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_annotations_unknown_flag'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_tenant_id'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_review_status'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_retained_image_id'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_primary_observation'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_instrument_family'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_inspection_id'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_id'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_ground_truth_status'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_digital_twin_id'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_dataset_version_id'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_created_at'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_baseline_id'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_ann_id'), table_name='annotations')
    op.drop_table('annotations')
    op.drop_index(op.f('ix_annotation_versions_tenant_id'), table_name='annotation_versions')
    op.drop_index(op.f('ix_annotation_versions_id'), table_name='annotation_versions')
    op.drop_index(op.f('ix_annotation_versions_created_at'), table_name='annotation_versions')
    op.drop_index(op.f('ix_annotation_versions_annotation_id'), table_name='annotation_versions')
    op.drop_table('annotation_versions')
    op.drop_index(op.f('ix_annotation_sequence_counters_year'), table_name='annotation_sequence_counters')
    op.drop_index(op.f('ix_annotation_sequence_counters_id'), table_name='annotation_sequence_counters')
    op.drop_table('annotation_sequence_counters')
    op.drop_index(op.f('ix_annotation_reviews_tenant_id'), table_name='annotation_reviews')
    op.drop_index(op.f('ix_annotation_reviews_id'), table_name='annotation_reviews')
    op.drop_index(op.f('ix_annotation_reviews_created_at'), table_name='annotation_reviews')
    op.drop_index(op.f('ix_annotation_reviews_annotation_id'), table_name='annotation_reviews')
    op.drop_table('annotation_reviews')
