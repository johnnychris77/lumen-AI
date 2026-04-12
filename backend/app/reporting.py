from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db import models


def _safe_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def _compact(value: Any) -> str:
    return json.dumps(value, default=str)[:4000]


def _parse_days(filter_json: dict) -> int:
    try:
        return max(1, int(filter_json.get("days", 30)))
    except Exception:
        return 30


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _inspection_rows(db: Session, tenant_id: str, days: int):
    q = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            models.Inspection.created_at >= _since(days),
        )
        .order_by(models.Inspection.id.desc())
    )
    return q.all()


def _audit_rows(db: Session, tenant_id: str, days: int):
    q = (
        db.query(models.AuditLog)
        .filter(
            models.AuditLog.tenant_id == tenant_id,
            models.AuditLog.created_at >= _since(days),
        )
        .order_by(models.AuditLog.id.desc())
    )
    return q.all()


def _usage_rows(db: Session, tenant_id: str, days: int):
    q = (
        db.query(models.UsageEvent)
        .filter(
            models.UsageEvent.tenant_id == tenant_id,
            models.UsageEvent.created_at >= _since(days),
        )
        .order_by(models.UsageEvent.id.desc())
    )
    return q.all()


def _payment_rows(db: Session, tenant_id: str, days: int):
    q = (
        db.query(models.PaymentEvent)
        .filter(
            models.PaymentEvent.tenant_id == tenant_id,
            models.PaymentEvent.created_at >= _since(days),
        )
        .order_by(models.PaymentEvent.id.desc())
    )
    return q.all()


def _match_common_filters(row: Any, filters: dict) -> bool:
    site_name = filters.get("site_name")
    vendor_name = filters.get("vendor_name")
    detected_issue = filters.get("detected_issue")
    min_risk_score = filters.get("min_risk_score")
    max_risk_score = filters.get("max_risk_score")

    if site_name and getattr(row, "site_name", None) != site_name:
        return False
    if vendor_name and getattr(row, "vendor_name", None) != vendor_name:
        return False
    if detected_issue and getattr(row, "detected_issue", None) != detected_issue:
        return False

    risk = getattr(row, "risk_score", None)
    if min_risk_score is not None and risk is not None and float(risk) < float(min_risk_score):
        return False
    if max_risk_score is not None and risk is not None and float(risk) > float(max_risk_score):
        return False

    return True


def run_report(db: Session, tenant_id: str, tenant_name: str, report_type: str, filters: dict) -> dict:
    days = _parse_days(filters)

    if report_type == "inspection_volume_risk_trends":
        rows = [r for r in _inspection_rows(db, tenant_id, days) if _match_common_filters(r, filters)]
        by_day = defaultdict(lambda: {"count": 0, "high_risk_count": 0})
        for row in rows:
            day = row.created_at.date().isoformat() if row.created_at else "unknown"
            by_day[day]["count"] += 1
            if int(row.risk_score or 0) >= 80:
                by_day[day]["high_risk_count"] += 1

        return {
            "report_type": report_type,
            "days": days,
            "summary": {
                "inspection_count": len(rows),
                "high_risk_count": sum(1 for r in rows if int(r.risk_score or 0) >= 80),
            },
            "series": [{"date": k, **v} for k, v in sorted(by_day.items())],
        }

    if report_type == "issue_mix_by_vendor_site":
        rows = [r for r in _inspection_rows(db, tenant_id, days) if _match_common_filters(r, filters)]
        mix = defaultdict(int)
        for row in rows:
            key = f"{row.vendor_name or 'unknown'}::{row.site_name or 'unknown'}::{row.detected_issue or 'unknown'}"
            mix[key] += 1

        return {
            "report_type": report_type,
            "days": days,
            "summary": {"inspection_count": len(rows)},
            "items": [{"bucket": k, "count": v} for k, v in sorted(mix.items(), key=lambda x: x[1], reverse=True)],
        }

    if report_type == "governance_activity_summary":
        rows = _audit_rows(db, tenant_id, days)
        mix = defaultdict(int)
        for row in rows:
            mix[row.action_type or "unknown"] += 1

        return {
            "report_type": report_type,
            "days": days,
            "summary": {"audit_count": len(rows)},
            "items": [{"action_type": k, "count": v} for k, v in sorted(mix.items(), key=lambda x: x[1], reverse=True)],
        }

    if report_type == "billing_usage_summary":
        usage = _usage_rows(db, tenant_id, days)
        payments = _payment_rows(db, tenant_id, days)

        usage_mix = defaultdict(int)
        for row in usage:
            usage_mix[row.event_type or "unknown"] += int(row.quantity or 0)

        payment_mix = defaultdict(int)
        for row in payments:
            payment_mix[row.status or "unknown"] += int(row.amount_cents or 0)

        return {
            "report_type": report_type,
            "days": days,
            "summary": {
                "usage_events": len(usage),
                "payment_events": len(payments),
            },
            "usage_items": [{"event_type": k, "quantity": v} for k, v in sorted(usage_mix.items())],
            "payment_items": [{"status": k, "amount_cents": v} for k, v in sorted(payment_mix.items())],
        }

    if report_type == "dunning_subscription_health":
        payments = _payment_rows(db, tenant_id, days)
        subs = (
            db.query(models.TenantSubscription)
            .filter(models.TenantSubscription.tenant_id == tenant_id)
            .order_by(models.TenantSubscription.id.desc())
            .all()
        )

        return {
            "report_type": report_type,
            "days": days,
            "summary": {
                "payment_events": len(payments),
                "subscriptions": len(subs),
            },
            "subscriptions": [
                {
                    "plan_name": s.plan_name,
                    "status": s.status,
                    "last_payment_status": s.last_payment_status,
                    "dunning_status": s.dunning_status,
                    "suspension_status": s.suspension_status,
                    "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                }
                for s in subs
            ],
        }

    return {
        "report_type": report_type,
        "days": days,
        "summary": {"message": f"Unsupported report_type: {report_type}"},
    }


def record_report_run(
    db: Session,
    *,
    tenant_id: str,
    tenant_name: str,
    report_id: int,
    report_type: str,
    filters: dict,
    result: dict,
    status: str = "completed",
    delivery_status: str = "not_sent",
):
    row = models.ReportRun(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        report_id=report_id,
        report_type=report_type,
        status=status,
        filter_json=_compact(filters),
        result_json=_compact(result),
        delivery_status=delivery_status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
