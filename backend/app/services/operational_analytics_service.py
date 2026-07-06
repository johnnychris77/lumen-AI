"""v1.7 — Operational Analytics (Deliverable 11)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.services.sla_monitoring_service import sla_monitoring
from app.services.technician_workload_service import technician_workload
from app.services.work_queue_service import build_work_queue


def operational_analytics(db: Session, tenant_id: str, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    throughput = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.created_at >= since)
        .count()
    )

    workload = technician_workload(db, tenant_id)
    queue = build_work_queue(db, tenant_id)
    sla = sla_monitoring(db, tenant_id)

    productivity = sorted(
        (
            {"technician": t["technician"], "completed_inspections": t["completed_inspections"]}
            for t in workload["technicians"]
        ),
        key=lambda t: t["completed_inspections"], reverse=True,
    )

    waits = [i["minutes_waiting"] for i in queue["pending_inspections"] if i["minutes_waiting"] is not None]
    queue_aging_minutes_avg = round(sum(waits) / len(waits), 1) if waits else None
    queue_aging_minutes_max = max(waits) if waits else None

    workloads = [t["workload"] for t in workload["technicians"]]
    workload_balance = {
        "min": min(workloads) if workloads else None,
        "max": max(workloads) if workloads else None,
        "spread": (max(workloads) - min(workloads)) if workloads else None,
    }

    return {
        "period_days": days,
        "inspection_throughput": throughput,
        "technician_productivity": productivity,
        "queue_aging_minutes_avg": queue_aging_minutes_avg,
        "queue_aging_minutes_max": queue_aging_minutes_max,
        "average_turnaround_minutes": sla["average_overall_turnaround_minutes"],
        "high_risk_workload": len(queue["high_risk_inspections"]),
        "workload_balance": workload_balance,
        "human_review_required": True,
    }
