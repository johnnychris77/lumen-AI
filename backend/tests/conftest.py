import importlib
import os
from pathlib import Path

import pytest

# Ensure data/ directory exists before any module-level code in capa_service.py runs
Path(os.path.join(os.path.dirname(__file__), "..", "data")).mkdir(exist_ok=True)
from sqlalchemy import text


def _load_database_objects():
    # Force-import enterprise models so they register in Base.metadata before create_all().
    # Without this, tables like audit_logs are skipped by create_all() and get created
    # by the raw-SQL fallback, which causes SQLAlchemy's RETURNING id to fail on PostgreSQL.
    _force_import_models()

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


def _force_import_models():
    """Import all ORM models so they register in Base.metadata before create_all() runs."""
    for model_path in [
        "app.models.audit_log",
        "app.models.enterprise_quality",
        "app.models.cv_inference",
        "app.models.alert_event",
        "app.models.inspection",
        "app.models.review",
        "app.models.user",
        "app.models.benchmarking",
        "app.models.vendor_intelligence",
        "app.models.tenant_plan",
        "app.models.payment_event",
        "app.models.predictions",
        "app.models.regulatory",
        "app.models.copilot",
        "app.models.digital_twin",
        "app.models.validation",
        "app.models.pilot",
        "app.models.tenant_health",
        "app.models.tenant_subscription_p14",
        "app.models.manufacturer_reg",
        "app.models.usage",
        "app.models.sso_config",
        "app.models.network_benchmark",
        "app.models.recall_signal",
        "app.models.instrument_registry",
        "app.models.baseline_library",
        "app.models.external_connector",
        "app.models.patient_safety",
        "app.models.integrations",
        "app.models.quality_intelligence",
        "app.models.digital_quality_twin",
        "app.models.global_intelligence",
    ]:
        try:
            importlib.import_module(model_path)
        except Exception:
            pass


def _create_audit_logs_fallback(engine):
    """
    Fallback in case audit_logs was not created by create_all().
    Uses dialect-appropriate syntax for SQLite and PostgreSQL.
    """
    dialect = engine.dialect.name
    if dialect == "postgresql":
        id_col = "id SERIAL PRIMARY KEY"
        datetime_type = "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
    else:
        id_col = "id INTEGER PRIMARY KEY AUTOINCREMENT"
        datetime_type = "DATETIME"

    create_sql = f"""
    CREATE TABLE IF NOT EXISTS audit_logs (
        {id_col},
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
        created_at {datetime_type}
    )
    """

    with engine.begin() as connection:
        connection.execute(text(create_sql))


@pytest.fixture(autouse=True)
def ensure_test_database_tables():
    base, engine = _load_database_objects()
    base.metadata.create_all(bind=engine)
    _create_audit_logs_fallback(engine)
    _seed_enterprise_finding(engine)
    yield


def _seed_enterprise_finding(engine) -> None:
    """Ensure at least one EnterpriseFinding row (id=1) exists for governance packet tests."""
    try:
        from app.models.enterprise_quality import EnterpriseFinding
        from sqlalchemy.orm import Session

        with Session(engine) as db:
            if db.get(EnterpriseFinding, 1) is None:
                db.add(EnterpriseFinding(
                    id=1,
                    tenant_id="default-tenant",
                    finding_category="Quality Control",
                    finding_description="Seeded test finding",
                    severity="low",
                    confidence_score=0.0,
                    human_confirmed=False,
                ))
                db.commit()
    except Exception:
        pass
