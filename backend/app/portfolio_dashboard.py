from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.customer_health import build_customer_health_summary
from app.customer_operations_hub import tenant_status_summary
from app.customer_success import renewal_risk_summary
from app.db import models
from app.implementation_readiness import readiness_summary
from app.release_governance_dashboard import dashboard_summary as release_dashboard_summary


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tenant_pairs(db: Session) -> list[tuple[str, str]]:
    pairs = (
        db.query(models.TenantSubscription.tenant_id, models.TenantSubscription.tenant_name)
        .distinct()
        .all()
    )
    if pairs:
        return [(x[0], x[1]) for x in pairs if x[0]]

    fallback = (
        db.query(models.Inspection.tenant_id, models.Inspection.tenant_name)
        .distinct()
        .all()
    )
    return [(x[0], x[1]) for x in fallback if x[0]]


def _portfolio_status_bucket(status: str) -> str:
    if status in {"healthy"}:
        return "healthy"
    if status in {"watch"}:
        return "watch"
    if status in {"at_risk", "implementation_in_progress"}:
        return "at_risk"
    return "unknown"


def portfolio_summary(db: Session) -> dict:
    tenants = _tenant_pairs(db)
    account_rows = []
    counts = Counter()

    for tenant_id, tenant_name in tenants:
        health = build_customer_health_summary(db, tenant_id, tenant_name, 30)
        readiness = readiness_summary(db, tenant_id, tenant_name)
        governance = release_dashboard_summary(db, tenant_id, tenant_name)
        renewal = renewal_risk_summary(db, tenant_id, tenant_name)
        ops = tenant_status_summary(db, tenant_id, tenant_name)

        bucket = _portfolio_status_bucket(ops.get("operating_status", "unknown"))
        counts[bucket] += 1

        account_rows.append({
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "operating_status": ops.get("operating_status", "unknown"),
            "health_score": health.get("health_score", 0),
            "health_status": health.get("health_status", "unknown"),
            "go_live_ready": readiness.get("go_live_ready", False),
            "readiness_score": readiness.get("readiness_score", 0),
            "blocked_count": readiness.get("blocked_count", 0),
            "governance_exception_count": governance.get("exception_count", 0),
            "open_renewal_cases": renewal.get("open_case_count", 0),
            "risk_flags": health.get("risk_flags", []),
            "top_recommendations": ops.get("top_recommendations", []),
        })

    account_rows = sorted(
        account_rows,
        key=lambda x: (
            0 if x["operating_status"] in {"at_risk", "implementation_in_progress"} else 1,
            x["health_score"],
            -x["governance_exception_count"],
            -x["open_renewal_cases"],
        )
    )

    return {
        "generated_at": _now(),
        "tenant_count": len(account_rows),
        "status_counts": dict(counts),
        "accounts": account_rows,
        "top_risk_accounts": account_rows[:10],
    }


def qbr_rollup(db: Session) -> dict:
    rows = (
        db.query(models.AccountReviewPacket)
        .order_by(models.AccountReviewPacket.id.desc())
        .all()
    )

    exports = (
        db.query(models.AccountReviewExport)
        .order_by(models.AccountReviewExport.id.desc())
        .all()
    )

    scheduled = (
        db.query(models.ScheduledAccountReview)
        .order_by(models.ScheduledAccountReview.id.desc())
        .all()
    )

    deliveries = (
        db.query(models.AccountReviewDelivery)
        .order_by(models.AccountReviewDelivery.id.desc())
        .all()
    )

    export_by_review = {x.account_review_id: x for x in exports}
    delivery_by_schedule = {}
    for row in deliveries:
        if row.schedule_id not in delivery_by_schedule:
            delivery_by_schedule[row.schedule_id] = row

    review_rows = []
    for row in rows:
        exp = export_by_review.get(row.id)
        review_rows.append({
            "account_review_id": row.id,
            "tenant_id": row.tenant_id,
            "tenant_name": row.tenant_name,
            "review_type": row.review_type,
            "period_label": row.period_label,
            "title": row.title,
            "has_export": bool(exp),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })

    schedule_rows = []
    for row in scheduled:
        last_delivery = delivery_by_schedule.get(row.id)
        schedule_rows.append({
            "schedule_id": row.id,
            "tenant_id": row.tenant_id,
            "tenant_name": row.tenant_name,
            "name": row.name,
            "review_type": row.review_type,
            "schedule_cron": row.schedule_cron,
            "delivery_channel": row.delivery_channel,
            "is_enabled": row.is_enabled,
            "last_delivery_status": last_delivery.delivery_status if last_delivery else "not_sent",
            "last_delivery_at": last_delivery.created_at.isoformat() if last_delivery and last_delivery.created_at else None,
        })

    return {
        "generated_at": _now(),
        "review_count": len(review_rows),
        "export_count": len(exports),
        "scheduled_count": len(schedule_rows),
        "delivery_count": len(deliveries),
        "latest_reviews": review_rows[:50],
        "scheduled_reviews": schedule_rows[:50],
    }


def executive_portfolio_dashboard(db: Session) -> dict:
    portfolio = portfolio_summary(db)
    qbr = qbr_rollup(db)

    return {
        "generated_at": _now(),
        "portfolio": portfolio,
        "qbr_rollup": qbr,
    }
