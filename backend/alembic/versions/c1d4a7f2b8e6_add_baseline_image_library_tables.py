"""add_baseline_image_library_tables

Project Atlas Sprint 1 — the reverse link from an existing
BaselineLibraryEntry to an existing LCID-registered image
(DatasetRegistryEntry), its governed review/lifecycle, multi-image
baseline sets, and the storage-integrity access log. See
docs/baseline-library/BASELINE_IMAGE_SCHEMA.md.

Revision ID: c1d4a7f2b8e6
Revises: b7c3d9f1a204
Create Date: 2026-07-16 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d4a7f2b8e6'
down_revision: Union[str, None] = 'b7c3d9f1a204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('baseline_image_links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('facility_id', sa.String(length=100), nullable=False),
    sa.Column('baseline_library_entry_id', sa.Integer(), nullable=False),
    sa.Column('lcid_image_id', sa.Integer(), nullable=False),
    sa.Column('instrument_family', sa.String(length=100), nullable=False),
    sa.Column('manufacturer', sa.String(length=100), nullable=False),
    sa.Column('model_name', sa.String(length=100), nullable=False),
    sa.Column('catalog_number', sa.String(length=100), nullable=False),
    sa.Column('anatomy_zone', sa.String(length=60), nullable=False),
    sa.Column('inspection_view', sa.String(length=60), nullable=False),
    sa.Column('orientation', sa.String(length=60), nullable=False),
    sa.Column('image_type', sa.String(length=30), nullable=False),
    sa.Column('source_type', sa.String(length=40), nullable=False),
    sa.Column('source_organization', sa.String(length=255), nullable=False),
    sa.Column('source_reference', sa.String(length=500), nullable=False),
    sa.Column('baseline_version', sa.String(length=40), nullable=False),
    sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lifecycle_status', sa.String(length=20), nullable=False),
    sa.Column('approved_by', sa.String(length=255), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('usage_rights_status', sa.String(length=100), nullable=False),
    sa.Column('image_quality_status', sa.String(length=20), nullable=False),
    sa.Column('annotation_ref', sa.String(length=40), nullable=False),
    sa.Column('digital_twin_id', sa.String(length=255), nullable=False),
    sa.Column('image_sha256', sa.String(length=64), nullable=False),
    sa.Column('retained_image_id', sa.Integer(), nullable=True),
    sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('supersedes_link_id', sa.Integer(), nullable=True),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('superseded_by', sa.String(length=255), nullable=False),
    sa.Column('limitations', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_baseline_image_links_anatomy_zone'), 'baseline_image_links', ['anatomy_zone'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_baseline_library_entry_id'), 'baseline_image_links', ['baseline_library_entry_id'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_created_at'), 'baseline_image_links', ['created_at'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_digital_twin_id'), 'baseline_image_links', ['digital_twin_id'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_facility_id'), 'baseline_image_links', ['facility_id'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_id'), 'baseline_image_links', ['id'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_image_sha256'), 'baseline_image_links', ['image_sha256'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_image_type'), 'baseline_image_links', ['image_type'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_inspection_view'), 'baseline_image_links', ['inspection_view'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_instrument_family'), 'baseline_image_links', ['instrument_family'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_lcid_image_id'), 'baseline_image_links', ['lcid_image_id'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_lifecycle_status'), 'baseline_image_links', ['lifecycle_status'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_manufacturer'), 'baseline_image_links', ['manufacturer'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_source_type'), 'baseline_image_links', ['source_type'], unique=False)
    op.create_index(op.f('ix_baseline_image_links_tenant_id'), 'baseline_image_links', ['tenant_id'], unique=False)

    op.create_table('baseline_image_reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('baseline_image_link_id', sa.Integer(), nullable=False),
    sa.Column('reviewer', sa.String(length=255), nullable=False),
    sa.Column('reviewer_role', sa.String(length=40), nullable=False),
    sa.Column('decision', sa.String(length=20), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=False),
    sa.Column('limitations', sa.Text(), nullable=False),
    sa.Column('source_verification', sa.Text(), nullable=False),
    sa.Column('anatomy_compatibility_confirmed', sa.Boolean(), nullable=False),
    sa.Column('image_quality_assessment', sa.String(length=20), nullable=False),
    sa.Column('review_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('next_review_date', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_baseline_image_reviews_baseline_image_link_id'), 'baseline_image_reviews', ['baseline_image_link_id'], unique=False)
    op.create_index(op.f('ix_baseline_image_reviews_created_at'), 'baseline_image_reviews', ['created_at'], unique=False)
    op.create_index(op.f('ix_baseline_image_reviews_decision'), 'baseline_image_reviews', ['decision'], unique=False)
    op.create_index(op.f('ix_baseline_image_reviews_id'), 'baseline_image_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_baseline_image_reviews_tenant_id'), 'baseline_image_reviews', ['tenant_id'], unique=False)

    op.create_table('baseline_sets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('manufacturer', sa.String(length=100), nullable=False),
    sa.Column('model_name', sa.String(length=100), nullable=False),
    sa.Column('instrument_family', sa.String(length=100), nullable=False),
    sa.Column('anatomy_zone', sa.String(length=60), nullable=False),
    sa.Column('view_protocol', sa.String(length=60), nullable=False),
    sa.Column('orientation_protocol', sa.String(length=60), nullable=False),
    sa.Column('version', sa.String(length=40), nullable=False),
    sa.Column('lifecycle_status', sa.String(length=20), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('limitations', sa.Text(), nullable=False),
    sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('supersedes_set_id', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_baseline_sets_active'), 'baseline_sets', ['active'], unique=False)
    op.create_index(op.f('ix_baseline_sets_anatomy_zone'), 'baseline_sets', ['anatomy_zone'], unique=False)
    op.create_index(op.f('ix_baseline_sets_created_at'), 'baseline_sets', ['created_at'], unique=False)
    op.create_index(op.f('ix_baseline_sets_id'), 'baseline_sets', ['id'], unique=False)
    op.create_index(op.f('ix_baseline_sets_instrument_family'), 'baseline_sets', ['instrument_family'], unique=False)
    op.create_index(op.f('ix_baseline_sets_lifecycle_status'), 'baseline_sets', ['lifecycle_status'], unique=False)
    op.create_index(op.f('ix_baseline_sets_manufacturer'), 'baseline_sets', ['manufacturer'], unique=False)
    op.create_index(op.f('ix_baseline_sets_tenant_id'), 'baseline_sets', ['tenant_id'], unique=False)

    op.create_table('baseline_set_members',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('baseline_set_id', sa.Integer(), nullable=False),
    sa.Column('baseline_image_link_id', sa.Integer(), nullable=False),
    sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_baseline_set_members_baseline_image_link_id'), 'baseline_set_members', ['baseline_image_link_id'], unique=False)
    op.create_index(op.f('ix_baseline_set_members_baseline_set_id'), 'baseline_set_members', ['baseline_set_id'], unique=False)
    op.create_index(op.f('ix_baseline_set_members_id'), 'baseline_set_members', ['id'], unique=False)

    op.create_table('baseline_comparison_access_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('baseline_image_link_id', sa.Integer(), nullable=False),
    sa.Column('accessed_by', sa.String(length=255), nullable=False),
    sa.Column('outcome', sa.String(length=30), nullable=False),
    sa.Column('similarity', sa.Float(), nullable=True),
    sa.Column('compatibility_status', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_baseline_comparison_access_log_baseline_image_link_id'), 'baseline_comparison_access_log', ['baseline_image_link_id'], unique=False)
    op.create_index(op.f('ix_baseline_comparison_access_log_created_at'), 'baseline_comparison_access_log', ['created_at'], unique=False)
    op.create_index(op.f('ix_baseline_comparison_access_log_id'), 'baseline_comparison_access_log', ['id'], unique=False)
    op.create_index(op.f('ix_baseline_comparison_access_log_outcome'), 'baseline_comparison_access_log', ['outcome'], unique=False)
    op.create_index(op.f('ix_baseline_comparison_access_log_tenant_id'), 'baseline_comparison_access_log', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_table('baseline_comparison_access_log')
    op.drop_table('baseline_set_members')
    op.drop_table('baseline_sets')
    op.drop_table('baseline_image_reviews')
    op.drop_table('baseline_image_links')
