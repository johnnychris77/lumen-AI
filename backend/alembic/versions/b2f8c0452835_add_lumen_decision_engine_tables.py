"""add_lumen_decision_engine_tables

Backfills the Lumen Decision Engine & Observation Doctrine sprint
(`app/models/lumen_decision_engine.py`) — the org-configurable Baseline
Decision Policy, the persisted, immutable per-inspection decision result
contract, and the unknown-finding learning-loop review record. As with
the annotation-database backfill, these tables have been live in the ORM
models and test suite since that sprint but never had a real Alembic
revision generated for them.

Revision ID: b2f8c0452835
Revises: 367bc3527700
Create Date: 2026-07-16 02:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2f8c0452835'
down_revision: Union[str, None] = '367bc3527700'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('baseline_decision_policies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('policy_id', sa.String(length=64), nullable=False),
    sa.Column('organization_id', sa.String(length=100), nullable=False),
    sa.Column('scope', sa.String(length=30), nullable=False),
    sa.Column('scope_value', sa.String(length=255), nullable=False),
    sa.Column('policy_name', sa.String(length=255), nullable=False),
    sa.Column('version', sa.String(length=20), nullable=False),
    sa.Column('baseline_source_requirement', sa.String(length=100), nullable=False),
    sa.Column('pass_threshold', sa.Float(), nullable=False),
    sa.Column('technician_review_threshold', sa.Float(), nullable=False),
    sa.Column('supervisor_attention_threshold', sa.Float(), nullable=False),
    sa.Column('supervisor_approval_threshold', sa.Float(), nullable=False),
    sa.Column('contamination_override_rule', sa.Text(), nullable=False),
    sa.Column('structural_damage_rule', sa.Text(), nullable=False),
    sa.Column('unknown_finding_rule', sa.Text(), nullable=False),
    sa.Column('author', sa.String(length=255), nullable=False),
    sa.Column('approving_role', sa.String(length=50), nullable=False),
    sa.Column('approved_by', sa.String(length=255), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=False),
    sa.Column('supporting_reference', sa.String(length=500), nullable=False),
    sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('previous_version_id', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_baseline_decision_policies_id'), 'baseline_decision_policies', ['id'], unique=False)
    op.create_index(op.f('ix_baseline_decision_policies_organization_id'), 'baseline_decision_policies', ['organization_id'], unique=False)
    op.create_index(op.f('ix_baseline_decision_policies_policy_id'), 'baseline_decision_policies', ['policy_id'], unique=True)
    op.create_index(op.f('ix_baseline_decision_policies_status'), 'baseline_decision_policies', ['status'], unique=False)
    op.create_table('lumen_decision_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('inspection_id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('facility_name', sa.String(length=255), nullable=False),
    sa.Column('observation_category', sa.String(length=60), nullable=True),
    sa.Column('observation_display_label', sa.String(length=120), nullable=True),
    sa.Column('observation_confidence', sa.Float(), nullable=True),
    sa.Column('observation_status', sa.String(length=40), nullable=False),
    sa.Column('model_version', sa.String(length=50), nullable=False),
    sa.Column('image_quality', sa.String(length=30), nullable=False),
    sa.Column('instrument_family', sa.String(length=100), nullable=False),
    sa.Column('anatomy_zone', sa.String(length=100), nullable=False),
    sa.Column('anatomy_zone_risk', sa.String(length=20), nullable=False),
    sa.Column('baseline_similarity', sa.Float(), nullable=True),
    sa.Column('baseline_deviation', sa.Float(), nullable=True),
    sa.Column('baseline_source', sa.String(length=100), nullable=True),
    sa.Column('baseline_version', sa.String(length=50), nullable=True),
    sa.Column('digital_twin_trend', sa.String(length=30), nullable=False),
    sa.Column('policy_id', sa.String(length=64), nullable=False),
    sa.Column('policy_version', sa.String(length=20), nullable=False),
    sa.Column('policy_scope', sa.String(length=30), nullable=False),
    sa.Column('threshold_used', sa.Float(), nullable=True),
    sa.Column('recommended_action', sa.String(length=60), nullable=False),
    sa.Column('supervisor_required', sa.Boolean(), nullable=False),
    sa.Column('recommendation_reason', sa.Text(), nullable=False),
    sa.Column('escalation_condition', sa.Text(), nullable=False),
    sa.Column('limitations_json', sa.Text(), nullable=False),
    sa.Column('human_review_required', sa.Boolean(), nullable=False),
    sa.Column('technician_action', sa.String(length=500), nullable=True),
    sa.Column('technician_actor', sa.String(length=255), nullable=True),
    sa.Column('technician_action_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('supervisor_action', sa.String(length=500), nullable=True),
    sa.Column('supervisor_actor', sa.String(length=255), nullable=True),
    sa.Column('supervisor_action_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('override_reason', sa.Text(), nullable=True),
    sa.Column('final_human_decision', sa.String(length=60), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lumen_decision_records_id'), 'lumen_decision_records', ['id'], unique=False)
    op.create_index(op.f('ix_lumen_decision_records_inspection_id'), 'lumen_decision_records', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_lumen_decision_records_tenant_id'), 'lumen_decision_records', ['tenant_id'], unique=False)
    op.create_table('unknown_finding_reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('inspection_id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.String(length=100), nullable=False),
    sa.Column('instrument_family', sa.String(length=100), nullable=False),
    sa.Column('anatomy_zone', sa.String(length=100), nullable=False),
    sa.Column('model_output', sa.Text(), nullable=False),
    sa.Column('model_confidence', sa.Float(), nullable=True),
    sa.Column('baseline_similarity', sa.Float(), nullable=True),
    sa.Column('evidence_limitations_json', sa.Text(), nullable=False),
    sa.Column('model_version', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('supervisor_classification', sa.String(length=255), nullable=True),
    sa.Column('supervisor_comments', sa.Text(), nullable=True),
    sa.Column('supervisor_actor', sa.String(length=255), nullable=True),
    sa.Column('second_review_status', sa.String(length=30), nullable=False),
    sa.Column('adjudicated_label', sa.String(length=255), nullable=True),
    sa.Column('dataset_eligible', sa.Boolean(), nullable=False),
    sa.Column('usage_rights', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unknown_finding_reviews_id'), 'unknown_finding_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_unknown_finding_reviews_inspection_id'), 'unknown_finding_reviews', ['inspection_id'], unique=False)
    op.create_index(op.f('ix_unknown_finding_reviews_status'), 'unknown_finding_reviews', ['status'], unique=False)
    op.create_index(op.f('ix_unknown_finding_reviews_tenant_id'), 'unknown_finding_reviews', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_unknown_finding_reviews_tenant_id'), table_name='unknown_finding_reviews')
    op.drop_index(op.f('ix_unknown_finding_reviews_status'), table_name='unknown_finding_reviews')
    op.drop_index(op.f('ix_unknown_finding_reviews_inspection_id'), table_name='unknown_finding_reviews')
    op.drop_index(op.f('ix_unknown_finding_reviews_id'), table_name='unknown_finding_reviews')
    op.drop_table('unknown_finding_reviews')
    op.drop_index(op.f('ix_lumen_decision_records_tenant_id'), table_name='lumen_decision_records')
    op.drop_index(op.f('ix_lumen_decision_records_inspection_id'), table_name='lumen_decision_records')
    op.drop_index(op.f('ix_lumen_decision_records_id'), table_name='lumen_decision_records')
    op.drop_table('lumen_decision_records')
    op.drop_index(op.f('ix_baseline_decision_policies_status'), table_name='baseline_decision_policies')
    op.drop_index(op.f('ix_baseline_decision_policies_policy_id'), table_name='baseline_decision_policies')
    op.drop_index(op.f('ix_baseline_decision_policies_organization_id'), table_name='baseline_decision_policies')
    op.drop_index(op.f('ix_baseline_decision_policies_id'), table_name='baseline_decision_policies')
    op.drop_table('baseline_decision_policies')
