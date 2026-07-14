import importlib
import os
from pathlib import Path

import pytest

# Enable dev-token auth for all tests. Must be set before any app module is
# imported because deps.py reads these env vars at module load time.
os.environ.setdefault("ENABLE_DEV_AUTH", "true")
os.environ.setdefault("DEV_AUTH_TOKEN", "dev-token")
os.environ.setdefault("DEV_SPD_MANAGER_TOKEN", "manager-token")
os.environ.setdefault("DEV_OPERATOR_TOKEN", "operator-token")
os.environ.setdefault("DEV_VENDOR_TOKEN", "vendor-token")
os.environ.setdefault("DEV_VIEWER_TOKEN", "viewer-token")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

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
        "app.models.consent_record",
        "app.models.supervisor_review",
        "app.models.clinical_decision_ledger",
        "app.models.cios_event",
        "app.models.inspection_image_tag",
        "app.models.simulation_engine",
        "app.models.or_connect",
        "app.models.quality_guardian",
        "app.models.sentinel_orchestration",
        "app.models.atlas_enterprise",
        "app.models.nexus_integration",
        "app.models.predictive_insight",
        "app.models.federated_horizon",
        "app.models.industry_collaboration",
        "app.models.platform_core",
        "app.models.workflow_forge",
        "app.models.pulse_operations",
        "app.models.catalyst_copilot",
        "app.models.orbit_readiness",
        "app.models.vanguard_intelligence",
        "app.models.apollo_quality",
        "app.models.athena_knowledge",
        "app.models.phoenix_intelligence",
        "app.models.infinity_platform",
        "app.models.olympus_network",
        "app.models.guardianx_assurance",
        "app.models.genesis_ai_intelligence_cloud",
        "app.models.nova_agent_platform",
        "app.models.vulcan_reliability",
        "app.models.sage_education",
        "app.models.veritas_evidence",
        "app.models.sentinelx_risk",
        "app.models.maestro_orchestration",
        "app.models.council_leadership",
        "app.models.governed_action",
        "app.models.oracle_discovery",
        # The following were audited and added because they were previously
        # missing from this list entirely -- they only worked by accident,
        # via incidental import ordering elsewhere in the test session (see
        # the Council/Maestro post-implementation review). Deliberately
        # excluded: "app.models.tenant_membership", a dead, never-imported
        # duplicate of the real `TenantMembership` in `app/db/models.py`
        # that maps a *different* schema onto the same `tenant_memberships`
        # table -- importing it would register a conflicting table
        # definition, not fix a gap.
        "app.models.account_review_delivery",
        "app.models.account_review_export",
        "app.models.account_review_packet",
        "app.models.admin_credential",
        "app.models.automation_rule",
        "app.models.automation_run",
        "app.models.capture_device",
        "app.models.competency_event",
        "app.models.continuous_improvement",
        "app.models.customer_health_snapshot",
        "app.models.customer_success_playbook",
        "app.models.digest_delivery",
        "app.models.digest_subscription",
        "app.models.disposition_override",
        "app.models.distribution_list",
        "app.models.distribution_recipient",
        "app.models.executive_scorecard",
        "app.models.feature_flag",
        "app.models.generated_briefing",
        "app.models.go_live_checkpoint",
        "app.models.governance_approval",
        "app.models.governance_rollback",
        "app.models.implementation_readiness_item",
        "app.models.inspection_finding",
        "app.models.dataset_governance",
        "app.models.instrument_knowledge",
        "app.models.invoice_line_item",
        "app.models.knowledge",
        "app.models.mentor_coaching_review",
        "app.models.mobile",
        "app.models.model_registry",
        "app.models.notification_template",
        "app.models.packet_release_history",
        "app.models.pilot_config",
        "app.models.pilot_error_log",
        "app.models.portfolio_briefing",
        "app.models.renewal_risk_case",
        "app.models.report_run",
        "app.models.retained_image",
        "app.models.retention_event",
        "app.models.root_cause",
        "app.models.saved_report",
        "app.models.scheduled_account_review",
        "app.models.scheduled_leadership_packet",
        "app.models.shadow_prediction",
        "app.models.subscription_change_event",
        "app.models.tenant_branding",
        "app.models.tenant_entitlement",
        "app.models.tenant_onboarding",
        "app.models.tenant_quota",
        "app.models.tenant_subscription",
        "app.models.usage_event",
        "app.models.user_role_assignment",
        "app.models.vendor_baseline_audit",
        "app.models.workflow",
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
    _seed_hipaa_baa(engine)
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


def _seed_hipaa_baa(engine) -> None:
    """Ensure TenantSubscriptionP14 row for default-tenant has hipaa_baa_signed_at set.

    The integrations route blocks BAA-required system connections unless a
    subscription with hipaa_baa_signed_at exists for the request tenant.
    Tests that use default-tenant need this seeded or they get 400.
    """
    try:
        from datetime import datetime, timezone
        from app.models.tenant_subscription_p14 import TenantSubscriptionP14
        from sqlalchemy.orm import Session

        with Session(engine) as db:
            sub = db.query(TenantSubscriptionP14).filter_by(
                tenant_id="default-tenant"
            ).first()
            if sub is None:
                db.add(TenantSubscriptionP14(
                    tenant_id="default-tenant",
                    hipaa_baa_signed_at=datetime.now(timezone.utc),
                ))
                db.commit()
            elif sub.hipaa_baa_signed_at is None:
                sub.hipaa_baa_signed_at = datetime.now(timezone.utc)
                db.commit()
    except Exception:
        pass
