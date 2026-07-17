"""Project Foundation (GPAE) — platform persistence monitoring.

Extends the existing probes (``/health`` liveness, ``/ready`` DB-only
readiness, ``/metrics`` counters in ``app.main``) with a deep check across
the persistence surfaces Foundation Section 14 names: database, object
storage, audit logging, model registry/artifact integrity, baseline
resolution tables, and the governed object registry.

Alerting honesty: ``dispatch_platform_alert`` logs the alert and, when an
SMTP destination is configured (``SMTP_HOST``/``ALERT_EMAIL_TO``), emails
it. When no destination is configured — true of every current
development environment — the alert is still recorded in the audit trail
with ``delivery="no_destination_configured"``; it is never silently
dropped and never falsely reported as delivered.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

COMPONENT_OK = "ok"
COMPONENT_FAILED = "failed"


def _check(fn, db: Session) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        detail = fn() or {}
        return {
            "status": COMPONENT_OK,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            **detail,
        }
    except Exception as exc:
        # A failed statement aborts the transaction on PostgreSQL; without
        # this rollback every later component check (and the alert write)
        # would fail with InFailedSqlTransaction.
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "status": COMPONENT_FAILED,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


def deep_health_check(db: Session) -> dict[str, Any]:
    """Check every GPAE persistence surface. Never raises — failures are
    reported per-component and roll up into overall_status."""

    def _database():
        db.execute(text("SELECT 1"))
        return {}

    def _alembic_version():
        # Absence is a real finding, not an error: create_all-managed dev/test
        # databases have no alembic_version table at all.
        try:
            row = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        except Exception:
            db.rollback()
            return {"version": "not_stamped"}
        return {"version": row[0] if row else "not_stamped"}

    def _object_storage():
        from app.services.object_storage import storage_health_check

        result = storage_health_check()
        if not result.get("read_write_verified"):
            raise RuntimeError(f"storage read/write not verified: {result}")
        return {"backend": result.get("backend", "")}

    def _audit_logging():
        from app.models.audit_log import AuditLog

        db.query(AuditLog.id).limit(1).all()
        return {}

    def _model_registry():
        from app.models.model_registry import ModelRegistryEntry

        total = db.query(ModelRegistryEntry).count()
        return {"registered_models": total}

    def _baseline_resolution():
        from app.models.baseline_image_library import BaselineImageLink

        db.query(BaselineImageLink.id).limit(1).all()
        return {}

    def _governed_objects():
        from app.models.governed_object import GovernedObject

        active = db.query(GovernedObject).count()
        return {"registered_objects": active}

    components = {
        "database": _check(_database, db),
        "alembic_version": _check(_alembic_version, db),
        "object_storage": _check(_object_storage, db),
        "audit_logging": _check(_audit_logging, db),
        "model_registry": _check(_model_registry, db),
        "baseline_resolution": _check(_baseline_resolution, db),
        "governed_objects": _check(_governed_objects, db),
    }

    failed = sorted(name for name, c in components.items() if c["status"] == COMPONENT_FAILED)
    return {
        "overall_status": "ok" if not failed else "degraded",
        "failed_components": failed,
        "components": components,
    }


def dispatch_platform_alert(
    db: Session,
    *,
    severity: str,
    component: str,
    message: str,
) -> dict[str, Any]:
    """Record a platform alert and deliver it if a destination exists.

    Returns the delivery outcome truthfully: ``delivered`` only when an
    actual send succeeded, otherwise ``no_destination_configured`` or
    ``delivery_failed``.
    """
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    smtp_host = os.getenv("SMTP_HOST", "")
    alert_to = os.getenv("ALERT_EMAIL_TO", "")

    delivery = "no_destination_configured"
    delivery_error = ""
    if smtp_host and alert_to:
        try:
            _send_alert_email(subject=f"[LumenAI {severity}] {component}", body=message, to=alert_to)
            delivery = "delivered"
        except Exception as exc:
            delivery = "delivery_failed"
            delivery_error = f"{type(exc).__name__}: {exc}"

    logger.error("PLATFORM ALERT [%s] %s: %s (delivery=%s)", severity, component, message, delivery)
    record_enterprise_audit_event(
        db,
        action_type="platform_alert_raised",
        resource_type="platform_monitoring",
        resource_id=component,
        status="failure" if delivery == "delivery_failed" else "success",
        compliance_flag=True,
        details={
            "severity": severity,
            "message": message,
            "delivery": delivery,
            "delivery_error": delivery_error,
        },
    )
    return {"severity": severity, "component": component, "delivery": delivery}


def _send_alert_email(*, subject: str, body: str, to: str) -> None:
    import smtplib
    from email.message import EmailMessage

    from app.config import get_settings

    settings = get_settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def run_monitoring_sweep(db: Session) -> dict[str, Any]:
    """One monitoring pass: deep check + an alert per failed component."""
    report = deep_health_check(db)
    alerts = [
        dispatch_platform_alert(
            db,
            severity="SEV-2",
            component=name,
            message=f"GPAE deep health check failed for {name}: "
            f"{report['components'][name].get('error', 'unknown error')}",
        )
        for name in report["failed_components"]
    ]
    report["alerts_raised"] = alerts
    return report
