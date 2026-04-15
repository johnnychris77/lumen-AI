from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.governance_sla import sla_dashboard
from app.implementation_readiness import readiness_summary
from app.release_governance_dashboard import dashboard_summary


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _since(days: int) -> datetime:
    return _now() - timedelta(days=days)


def _compact(value, limit: int = 4000) -> str:
    return json.dumps(value, default=str)[:limit]


def _status(score: int) -> str:
    if score >= 80:
        return "healthy"
    if score >= 60:
        return "watch"
    return "at_risk"


def build_customer_health_summary(db: Session, tenant_id: str, tenant_name: str, days: int = 30) -> dict:
    usage_events = (
        db.query(models.UsageEvent)
        .filter(
            models.UsageEvent.tenant_id == tenant_id,
            models.UsageEvent.created_at >= _since(days),
        )
        .all()
    )

    leadership_packets = (
        db.query(models.LeadershipPacket)
        .filter(
            models.LeadershipPacket.tenant_id == tenant_id,
            models.LeadershipPacket.created_at >= _since(days),
        )
        .all()
    )

    report_runs = (
        db.query(models.ReportRun)
        .filter(
            models.ReportRun.tenant_id == tenant_id,
            models.ReportRun.created_at >= _since(days),
        )
        .all()
    )

    notification_templates = (
        db.query(models.NotificationTemplate)
        .filter(models.NotificationTemplate.tenant_id == tenant_id)
        .count()
    )

    distribution_lists = (
        db.query(models.DistributionList)
        .filter(models.DistributionList.tenant_id == tenant_id)
        .count()
    )

    readiness = readiness_summary(db, tenant_id, tenant_name)
    release = dashboard_summary(db, tenant_id, tenant_name)
    sla = sla_dashboard(db, tenant_id, tenant_name)

    usage_count = len(usage_events)
    packet_count = len(leadership_packets)
    report_run_count = len(report_runs)
    readiness_score = int(round(readiness.get("readiness_score", 0)))
    go_live_ready = bool(readiness.get("go_live_ready", False))
    release_exception_count = int(release.get("exception_count", 0))
    open_sla_count = int(sla.get("open_count", 0))

    usage_score = min(100, usage_count * 5)
    adoption_score = min(100, (packet_count * 15) + (report_run_count * 5) + (notification_templates * 5) + (distribution_lists * 10))
    governance_score = max(0, 100 - min(60, release_exception_count * 10) - min(40, open_sla_count * 10))

    if not go_live_ready:
        governance_score = max(0, governance_score - 15)

    overall = int(round((usage_score * 0.35) + (adoption_score * 0.30) + (governance_score * 0.35)))
    overall = max(0, min(100, overall))

    risk_flags = []
    if usage_count < 5:
        risk_flags.append("low_usage")
    if packet_count == 0:
        risk_flags.append("no_leadership_packets")
    if report_run_count == 0:
        risk_flags.append("no_saved_report_runs")
    if not go_live_ready:
        risk_flags.append("go_live_not_ready")
    if release_exception_count > 0:
        risk_flags.append("release_exceptions_open")
    if open_sla_count > 0:
        risk_flags.append("sla_events_open")
    if distribution_lists == 0:
        risk_flags.append("distribution_lists_not_configured")
    if notification_templates == 0:
        risk_flags.append("notification_templates_not_configured")

    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "days": days,
        "health_score": overall,
        "health_status": _status(overall),
        "usage_score": usage_score,
        "governance_score": governance_score,
        "adoption_score": adoption_score,
        "risk_flags": risk_flags,
        "summary": {
            "usage_event_count": usage_count,
            "leadership_packet_count": packet_count,
            "report_run_count": report_run_count,
            "notification_template_count": notification_templates,
            "distribution_list_count": distribution_lists,
            "go_live_ready": go_live_ready,
            "readiness_score": readiness_score,
            "release_exception_count": release_exception_count,
            "open_sla_count": open_sla_count,
        },
    }


def create_health_snapshot(db: Session, tenant_id: str, tenant_name: str, days: int = 30):
    summary = build_customer_health_summary(db, tenant_id, tenant_name, days)

    row = models.CustomerHealthSnapshot(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        health_score=summary["health_score"],
        health_status=summary["health_status"],
        usage_score=summary["usage_score"],
        governance_score=summary["governance_score"],
        adoption_score=summary["adoption_score"],
        risk_flags_json=_compact(summary["risk_flags"]),
        summary_json=_compact(summary["summary"]),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, summary


def latest_snapshot(db: Session, tenant_id: str):
    return (
        db.query(models.CustomerHealthSnapshot)
        .filter(models.CustomerHealthSnapshot.tenant_id == tenant_id)
        .order_by(models.CustomerHealthSnapshot.id.desc())
        .first()
    )


def recommendations(summary: dict) -> list[str]:
    recs = []
    flags = set(summary.get("risk_flags", []))

    if "low_usage" in flags:
        recs.append("Drive weekly usage by running saved reports, scorecards, and packet workflows.")
    if "no_leadership_packets" in flags:
        recs.append("Generate at least one leadership packet to validate executive reporting workflows.")
    if "no_saved_report_runs" in flags:
        recs.append("Run scheduled or manual analytics reports to increase adoption and executive visibility.")
    if "go_live_not_ready" in flags:
        recs.append("Complete blocked implementation readiness items and finish go-live checkpoints.")
    if "release_exceptions_open" in flags:
        recs.append("Review the release governance exception queue and resolve held or blocked packets.")
    if "sla_events_open" in flags:
        recs.append("Resolve overdue SLA events and tune escalation policies if thresholds are too aggressive.")
    if "distribution_lists_not_configured" in flags:
        recs.append("Create executive distribution lists to support governed packet delivery.")
    if "notification_templates_not_configured" in flags:
        recs.append("Configure notification templates for dunning, approvals, alerts, and digests.")

    if not recs:
        recs.append("Maintain current operating cadence and continue monitoring governance and adoption trends.")

    return recs
