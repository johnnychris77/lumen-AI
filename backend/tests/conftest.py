import importlib

import pytest
from sqlalchemy import text


def _load_database_objects():
    candidates = [
        "app.database",
        "app.db",
        "app.core.database",
        "app.core.db",
        "app.config.database",
    ]

    last_error = None

    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            last_error = exc
            continue

        base = getattr(module, "Base", None)
        engine = getattr(module, "engine", None)

        if base is not None and engine is not None:
            return base, engine

    raise RuntimeError(
        f"Could not locate SQLAlchemy Base and engine. Last error: {last_error}"
    )


def _create_audit_logs_fallback(engine):
    """
    Fallback for CI SQLite when audit log models are not imported before tests.
    This table matches the enterprise audit fields used by compliance evidence tests.
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id VARCHAR,
        tenant_name VARCHAR,
        actor_email VARCHAR,
        actor_role VARCHAR,
        action_type VARCHAR,
        resource_type VARCHAR,
        resource_id VARCHAR,
        status VARCHAR,
        request_method VARCHAR,
        request_path VARCHAR,
        client_ip VARCHAR,
        details TEXT,
        compliance_flag BOOLEAN,
        request_id VARCHAR,
        correlation_id VARCHAR,
        previous_event_hash VARCHAR,
        event_hash VARCHAR,
        created_at DATETIME
    )
    """

    with engine.begin() as connection:
        connection.execute(text(create_sql))


@pytest.fixture(autouse=True)
def ensure_test_database_tables():
    base, engine = _load_database_objects()
    base.metadata.create_all(bind=engine)
    _create_audit_logs_fallback(engine)
    yield
