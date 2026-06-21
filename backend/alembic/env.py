"""Alembic environment configuration for LumenAI.

Reads DATABASE_URL from environment — never uses hardcoded credentials.
Imports all models so autogenerate can detect schema changes.
"""
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Load alembic.ini logging config
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from DATABASE_URL environment variable
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Import all models so Alembic autogenerate can detect them
# These imports register models against Base.metadata
from app.db import Base  # noqa: E402

import app.db.models  # noqa: E402, F401
import app.models.cv_inference  # noqa: E402, F401
import app.models.benchmarking  # noqa: E402, F401
import app.models.vendor_intelligence  # noqa: E402, F401
import app.models.payment_event  # noqa: E402, F401
import app.models.tenant_plan  # noqa: E402, F401
import app.models.predictions  # noqa: E402, F401
import app.models.regulatory  # noqa: E402, F401
import app.models.copilot  # noqa: E402, F401
import app.models.digital_twin  # noqa: E402, F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection required, emit SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
