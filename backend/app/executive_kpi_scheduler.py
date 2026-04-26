from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from app.db import session as db_session
from app.executive_kpi_snapshots import (
    capture_executive_kpi_snapshot,
    executive_kpi_trends,
)


_scheduler: BackgroundScheduler | None = None
_last_run_summary: dict[str, Any] = {
    "status": "not_started",
    "checked_at": None,
    "snapshot_id": None,
    "error": None,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_db_session():
    if hasattr(db_session, "SessionLocal"):
        return db_session.SessionLocal()
    raise RuntimeError("No SessionLocal provider found in app.db.session")


def _movement_sentence(label: str, metric: dict[str, Any], risk_direction: str = "higher_is_worse") -> str:
    latest = int(metric.get("latest") or 0)
    previous = int(metric.get("previous") or 0)
    delta = int(metric.get("delta") or 0)

    if delta == 0:
        return f"{label} remained unchanged at {latest}."

    direction = "increased" if delta > 0 else "decreased"
    magnitude = abs(delta)

    if risk_direction == "higher_is_worse":
        interpretation = "This is unfavorable and should be reviewed." if delta > 0 else "This is favorable movement."
    else:
        interpretation = "This is favorable movement." if delta > 0 else "This is unfavorable and should be reviewed."

    return f"{label} {direction} from {previous} to {latest} ({magnitude} change). {interpretation}"


def generate_executive_kpi_trend_narrative(db) -> dict[str, Any]:
    trends = executive_kpi_trends(db, limit=12)
    movement = trends.get("movement") or {}

    if not trends.get("latest"):
        return {
            "status": "insufficient_data",
            "executive_summary": "No KPI snapshots are available yet. Capture at least one snapshot to establish a baseline.",
            "movement_narratives": [],
            "board_narrative": "Executive KPI trend narrative is unavailable because no KPI snapshot has been captured.",
            "recommended_actions": ["Capture a baseline KPI snapshot."],
        }

    if not trends.get("previous"):
        latest = trends["latest"]
        return {
            "status": "baseline_only",
            "executive_summary": "One KPI snapshot is available. Trend movement will be available after the next snapshot.",
            "movement_narratives": [],
            "board_narrative": (
                "Executive KPI baseline has been captured. "
                f"Current critical tenants: {latest.get('tenant_critical', 0)}. "
                f"Open remediations: {latest.get('remediation_open', 0)}. "
                f"Open escalations: {latest.get('escalation_open', 0)}. "
                f"Leadership decisions required: {latest.get('leadership_decisions_required', 0)}."
            ),
            "recommended_actions": ["Capture a follow-up KPI snapshot after workflow changes or at the next operating cadence."],
        }

    key_labels = {
        "tenant_critical": "Critical tenants",
        "tenant_at_risk": "At-risk tenants",
        "qbr_overdue": "QBR overdue accounts",
        "governance_exceptions": "Governance exceptions",
        "remediation_open": "Open remediation actions",
        "remediation_overdue": "Overdue remediation actions",
        "escalation_open": "Open executive escalations",
        "escalation_critical": "Critical executive escalations",
        "leadership_decisions_required": "Leadership decisions required",
        "delivery_retry_pending": "Retry-pending deliveries",
        "portfolio_exports": "Portfolio exports",
        "governance_packet_exports": "Governance packet exports",
        "artifact_count": "Generated artifacts",
    }

    higher_is_better = {"portfolio_exports", "governance_packet_exports", "artifact_count"}

    movement_narratives = []
    unfavorable = []
    favorable = []

    for key, label in key_labels.items():
        if key not in movement:
            continue

        risk_direction = "higher_is_better" if key in higher_is_better else "higher_is_worse"
        sentence = _movement_sentence(label, movement[key], risk_direction=risk_direction)
        movement_narratives.append({"metric": key, "label": label, "narrative": sentence, **movement[key]})

        delta = int(movement[key].get("delta") or 0)
        if key not in higher_is_better and delta > 0:
            unfavorable.append(label)
        elif key not in higher_is_better and delta < 0:
            favorable.append(label)
        elif key in higher_is_better and delta > 0:
            favorable.append(label)
        elif key in higher_is_better and delta < 0:
            unfavorable.append(label)

    executive_summary = (
        f"KPI trend review includes {trends.get('snapshot_count', 0)} captured snapshot(s). "
        f"Favorable movement was observed in {len(favorable)} metric(s). "
        f"Unfavorable movement was observed in {len(unfavorable)} metric(s)."
    )

    recommended_actions = [
        "Review unfavorable movement metrics during the next executive operating cadence.",
        "Assign owners for critical tenant, overdue remediation, and escalation growth.",
        "Use the trend movement table to confirm whether governance actions are improving risk posture.",
    ]

    if unfavorable:
        recommended_actions.insert(0, f"Prioritize review of: {', '.join(unfavorable[:5])}.")

    board_narrative = executive_summary + "\n\n" + "\n".join([item["narrative"] for item in movement_narratives[:8]])

    return {
        "status": "ready",
        "executive_summary": executive_summary,
        "movement_narratives": movement_narratives,
        "board_narrative": board_narrative,
        "favorable_metrics": favorable,
        "unfavorable_metrics": unfavorable,
        "recommended_actions": recommended_actions,
    }


def run_kpi_snapshot_now() -> dict[str, Any]:
    global _last_run_summary

    db = _new_db_session()
    try:
        snapshot = capture_executive_kpi_snapshot(
            db,
            snapshot_label="Automated Executive KPI Snapshot",
        )

        narrative = generate_executive_kpi_trend_narrative(db)

        _last_run_summary = {
            "status": "completed",
            "checked_at": _now_iso(),
            "snapshot_id": snapshot.get("id"),
            "error": None,
        }

        return {
            "status": "completed",
            "snapshot": snapshot,
            "trend_narrative": narrative,
        }

    except Exception as exc:
        _last_run_summary = {
            "status": "failed",
            "checked_at": _now_iso(),
            "snapshot_id": None,
            "error": repr(exc),
        }
        raise

    finally:
        db.close()


def start_executive_kpi_scheduler() -> dict[str, Any]:
    global _scheduler

    if _scheduler and _scheduler.running:
        return executive_kpi_scheduler_status()

    interval_hours = int(os.getenv("EXECUTIVE_KPI_SCHEDULER_HOURS", "24"))

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_kpi_snapshot_now,
        "interval",
        hours=interval_hours,
        id="executive_kpi_snapshot_runner",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()

    return executive_kpi_scheduler_status()


def shutdown_executive_kpi_scheduler() -> None:
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def executive_kpi_scheduler_status() -> dict[str, Any]:
    return {
        "running": bool(_scheduler and _scheduler.running),
        "jobs": [
            {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in (_scheduler.get_jobs() if _scheduler else [])
        ],
        "last_run_summary": _last_run_summary,
    }
