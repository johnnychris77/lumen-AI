from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.retention import get_retention_policy


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cutoff(days: int) -> datetime:
    return _now() - timedelta(days=int(days))


def _log_event(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    artifact_type: str,
    artifact_id: str,
    action: str,
    status: str,
    reason: str,
    legal_hold_blocked: bool,
):
    row = models.RetentionEvent(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        artifact_type=artifact_type,
        artifact_id=str(artifact_id or ""),
        action=action,
        status=status,
        reason=reason[:2000],
        legal_hold_blocked=bool(legal_hold_blocked),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _distinct_tenants(db: Session) -> list[tuple[str, str]]:
    rows = db.query(models.Inspection.tenant_id, models.Inspection.tenant_name).distinct().all()
    return [(r[0], r[1]) for r in rows]


def enforce_retention_once(db: Session) -> dict:
    summary = {
        "evaluated_at": _now().isoformat(),
        "tenants": [],
        "totals": {
            "inspections_deleted": 0,
            "audit_logs_deleted": 0,
            "digest_deliveries_deleted": 0,
            "retention_blocks": 0,
            "failures": 0,
            "events_logged": 0,
        },
    }

    for tenant_id, tenant_name in _distinct_tenants(db):
        tenant_result = {
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "inspections_deleted": 0,
            "audit_logs_deleted": 0,
            "digest_deliveries_deleted": 0,
            "retention_blocks": 0,
            "failures": 0,
        }

        artifact_specs = [
            ("inspection", models.Inspection, "created_at"),
            ("audit_log", models.AuditLog, "created_at"),
            ("digest_delivery", models.DigestDelivery, "created_at"),
        ]

        for artifact_type, model_cls, created_field in artifact_specs:
            try:
                policy = get_retention_policy(db, tenant_id, tenant_name, artifact_type)

                if policy["legal_hold_enabled"]:
                    _log_event(
                        db,
                        tenant_id=tenant_id,
                        tenant_name=tenant_name,
                        artifact_type=artifact_type,
                        artifact_id="*",
                        action="retention_skip",
                        status="blocked",
                        reason="Legal hold enabled; deletion blocked",
                        legal_hold_blocked=True,
                    )
                    tenant_result["retention_blocks"] += 1
                    summary["totals"]["retention_blocks"] += 1
                    summary["totals"]["events_logged"] += 1
                    continue

                cutoff_dt = _cutoff(policy["retention_days"])
                created_col = getattr(model_cls, created_field)
                tenant_col = getattr(model_cls, "tenant_id", None)

                q = db.query(model_cls).filter(created_col < cutoff_dt)
                if tenant_col is not None:
                    q = q.filter(tenant_col == tenant_id)

                rows = q.all()

                deleted_count = 0
                for row in rows:
                    artifact_id = getattr(row, "id", "")
                    try:
                        db.delete(row)
                        db.commit()
                        deleted_count += 1
                        _log_event(
                            db,
                            tenant_id=tenant_id,
                            tenant_name=tenant_name,
                            artifact_type=artifact_type,
                            artifact_id=str(artifact_id),
                            action="retention_delete",
                            status="success",
                            reason=f"Deleted per retention policy ({policy['retention_days']} days)",
                            legal_hold_blocked=False,
                        )
                        summary["totals"]["events_logged"] += 1
                    except Exception as e:
                        db.rollback()
                        _log_event(
                            db,
                            tenant_id=tenant_id,
                            tenant_name=tenant_name,
                            artifact_type=artifact_type,
                            artifact_id=str(artifact_id),
                            action="retention_delete",
                            status="failed",
                            reason=str(e),
                            legal_hold_blocked=False,
                        )
                        tenant_result["failures"] += 1
                        summary["totals"]["failures"] += 1
                        summary["totals"]["events_logged"] += 1

                if artifact_type == "inspection":
                    tenant_result["inspections_deleted"] += deleted_count
                    summary["totals"]["inspections_deleted"] += deleted_count
                elif artifact_type == "audit_log":
                    tenant_result["audit_logs_deleted"] += deleted_count
                    summary["totals"]["audit_logs_deleted"] += deleted_count
                elif artifact_type == "digest_delivery":
                    tenant_result["digest_deliveries_deleted"] += deleted_count
                    summary["totals"]["digest_deliveries_deleted"] += deleted_count

            except Exception as e:
                db.rollback()
                _log_event(
                    db,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                    artifact_type=artifact_type,
                    artifact_id="*",
                    action="retention_enforcement",
                    status="failed",
                    reason=str(e),
                    legal_hold_blocked=False,
                )
                tenant_result["failures"] += 1
                summary["totals"]["failures"] += 1
                summary["totals"]["events_logged"] += 1

        summary["tenants"].append(tenant_result)

    return summary


def build_retention_exception_report(db: Session, limit: int = 200) -> dict:
    rows = (
        db.query(models.RetentionEvent)
        .filter(
            (models.RetentionEvent.status == "blocked") |
            (models.RetentionEvent.status == "failed") |
            (models.RetentionEvent.legal_hold_blocked == True)
        )
        .order_by(models.RetentionEvent.id.desc())
        .limit(limit)
        .all()
    )

    items = [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "tenant_name": r.tenant_name,
            "artifact_type": r.artifact_type,
            "artifact_id": r.artifact_id,
            "action": r.action,
            "status": r.status,
            "reason": r.reason,
            "legal_hold_blocked": r.legal_hold_blocked,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    grouped = defaultdict(int)
    for item in items:
        grouped[f"{item['tenant_id']}::{item['artifact_type']}::{item['status']}"] += 1

    summary = sorted(
        [{"scope": k, "count": v} for k, v in grouped.items()],
        key=lambda x: x["count"],
        reverse=True,
    )

    return {
        "generated_at": _now().isoformat(),
        "summary": summary,
        "items": items,
    }
