"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-20

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Auto-generated from P0-P11 models
    # Run: alembic revision --autogenerate -m "initial_schema" in your environment
    # with DATABASE_URL pointing to a fresh PostgreSQL instance
    pass


def downgrade() -> None:
    pass
