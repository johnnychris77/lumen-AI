"""v4.2 — Project Pulse, Section 4: Live Operational KPIs.

Every KPI is computed fresh from real rows each time it is requested —
none are cached/pre-aggregated, so "continuously update" / "refresh
automatically" simply means the frontend polls this endpoint; there is
no separate background refresh job to keep in sync. Reuses
`insight_operational_forecast_service._OPEN_REPAIR_STATUSES` and
Sentinel's canonical enterprise risk score rather than re-deriving them.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.knowledge import KnowledgeArticle
from app.models.or_connect import REPAIR_IN_PROGRESS, REPAIR_PENDING, RepairRequest
from app.services import digital_twin_engine, sentinel_dashboard_service

_LOOKBACK_HOURS = 24
_HIGH_SEVERITY_THRESHOLD = 3
_OPEN_REPAIR_STATUSES = {REPAIR_PENDING, REPAIR_IN_PROGRESS}


def live_kpis(db: Session, tenant_id: str) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=_LOOKBACK_HOURS)

    inspections_recent = db.query(Inspection).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).all()
    throughput = len(inspections_recent)

    queue_length = db.query(Inspection.id).filter(Inspection.tenant_id == tenant_id, Inspection.score_status == "pending").count()
    supervisor_backlog = db.query(Inspection.id).filter(
        Inspection.tenant_id == tenant_id, Inspection.supervisor_review_required.is_(True), Inspection.qa_review_status == "pending",
    ).count()

    reviewed = [i for i in inspections_recent if i.qa_reviewed_at is not None]
    avg_review_time_minutes = None
    if reviewed:
        deltas = [(i.qa_reviewed_at - i.created_at).total_seconds() / 60 for i in reviewed]
        avg_review_time_minutes = round(sum(deltas) / len(deltas), 1)

    confidences = [i.ai_confidence for i in inspections_recent if i.ai_confidence is not None]
    ai_confidence_avg = round(sum(confidences) / len(confidences), 3) if confidences else None

    coverages = [i.coverage_pct for i in inspections_recent if i.coverage_pct is not None]
    coverage_avg = round(sum(coverages) / len(coverages), 1) if coverages else None

    high_risk_findings = db.query(InspectionFinding.id).filter(
        InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since,
        InspectionFinding.severity_index >= _HIGH_SEVERITY_THRESHOLD,
    ).count()

    repair_queue_length = db.query(RepairRequest.id).filter(
        RepairRequest.tenant_id == tenant_id, RepairRequest.status.in_(_OPEN_REPAIR_STATUSES),
    ).count()

    knowledge_contributions_recent = db.query(KnowledgeArticle.id).filter(
        KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.created_at >= since,
    ).count()

    health_snapshot = sentinel_dashboard_service.run_sentinel_health_snapshot(db, tenant_id)
    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, "", db)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lookback_hours": _LOOKBACK_HOURS,
        "inspection_throughput": throughput,
        "ai_analysis_queue_length": queue_length,
        "supervisor_backlog": supervisor_backlog,
        "avg_review_time_minutes": avg_review_time_minutes,
        "ai_confidence_avg": ai_confidence_avg,
        "coverage_pct_avg": coverage_avg,
        "high_risk_findings_count": high_risk_findings,
        "repair_queue_length": repair_queue_length,
        "knowledge_contributions_recent": knowledge_contributions_recent,
        "digital_twin_health_pct": twin_dashboard.twin_state.utilization_pct,
        "enterprise_risk_score": health_snapshot.get("enterprise_risk_score"),
        "human_review_required": True,
    }
