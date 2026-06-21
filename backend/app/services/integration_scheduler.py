"""Nightly integration import scheduler — pulls from all active ExternalSystemConnections."""
from datetime import datetime, timedelta


def _run_nightly_imports(db_factory):
    """Run imports for all active connections. Called by APScheduler."""
    import uuid
    from app.models.integrations import ExternalSystemConnection, IntegrationImportRun
    from app.services.integration_correlation_service import _get_connector

    db = db_factory()
    try:
        connections = db.query(ExternalSystemConnection).filter(
            ExternalSystemConnection.connection_status == "active"
        ).all()

        for conn in connections:
            run = IntegrationImportRun(
                import_id=str(uuid.uuid4()),
                tenant_id=conn.tenant_id,
                connection_id=conn.id,
                system_name=conn.system_name,
                import_type="scheduled",
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(run)
            db.commit()

            try:
                import json
                config = json.loads(conn.config_json or "{}")
                connector = _get_connector(conn.system_name, conn.tenant_id, conn.facility_id or "", config)
                since = datetime.utcnow() - timedelta(days=1)
                result = connector.run_import(since_timestamp=since)

                run.status = "completed"
                run.records_imported = result.get("imported", 0)
                run.records_failed = result.get("failed", 0)
                run.error_summary = str(result.get("errors", [])) if result.get("errors") else None
                conn.last_import_at = datetime.utcnow()
                conn.total_records_imported = (conn.total_records_imported or 0) + result.get("imported", 0)
                if result.get("failed", 0) > 0:
                    conn.consecutive_errors = (conn.consecutive_errors or 0) + 1
                else:
                    conn.consecutive_errors = 0
            except Exception as e:
                run.status = "failed"
                run.error_summary = str(e)
                conn.consecutive_errors = (conn.consecutive_errors or 0) + 1
            finally:
                run.completed_at = datetime.utcnow()
                db.commit()
    finally:
        db.close()


def register_integration_scheduler(scheduler, db_factory):
    """Register nightly import job — 01:00 UTC daily."""
    scheduler.add_job(
        _run_nightly_imports,
        "cron",
        hour=1,
        minute=0,
        args=[db_factory],
        id="nightly_integration_imports",
        replace_existing=True,
    )
