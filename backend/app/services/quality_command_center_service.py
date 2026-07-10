"""v2.9 — LumenAI Quality (Project Guardian), Sections 9-10: Executive
Quality Dashboard + Quality Learning Loop.

Aggregates the other Guardian engines for `/quality-command-center` rather
than re-deriving their logic, and defines what a "confirmed" quality event
actually updates — honestly scoped to real write paths (Clinical Memory)
and read-time aggregations that naturally reflect new data on next read
(trend analytics), rather than fabricating writes to systems that don't
persist mutable state for this purpose.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.baseline_library import BaselineLibraryEntry
from app.models.or_connect import VendorTray
from app.models.quality_guardian import DISCLAIMER, EventCorrelation, QualityEvent
from app.services import capa_lifecycle_service, competency_intelligence_service, first_pass_yield_service
from app.services.clinical_case_library_service import is_significant, save_or_update_case
from app.services.competency_service import technician_quality_dashboard
from app.services.quality_event_service import _get_event
from app.services.root_cause_service import root_cause_trends


def quality_command_center_summary(db: Session, tenant_id: str, *, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    events = (
        db.query(QualityEvent)
        .filter(QualityEvent.tenant_id == tenant_id, QualityEvent.created_at >= since)
        .all()
    )
    events_by_severity: dict[str, int] = {}
    findings_counter: dict[str, int] = {}
    for e in events:
        events_by_severity[e.severity] = events_by_severity.get(e.severity, 0) + 1
        if e.finding_type:
            findings_counter[e.finding_type] = findings_counter.get(e.finding_type, 0) + 1
    recurring_findings = sorted(
        [{"finding_type": k, "count": v} for k, v in findings_counter.items()],
        key=lambda x: x["count"], reverse=True,
    )[:10]

    capa_lifecycle = capa_lifecycle_service.lifecycle_summary(tenant_id)
    causes = root_cause_trends(db, tenant_id)
    fpy = first_pass_yield_service.compute_all_scopes(db, tenant_id)

    opportunities = competency_intelligence_service.list_opportunities(db, tenant_id)
    scored = [o["effectiveness_score"] for o in opportunities if o["effectiveness_score"] is not None]
    education_impact_avg = round(sum(scored) / len(scored), 1) if scored else None

    technician_trends = technician_quality_dashboard(db, tenant_id)

    vendor_trays = (
        db.query(VendorTray)
        .filter(VendorTray.tenant_id == tenant_id, VendorTray.created_at >= since, VendorTray.vendor_name != "")
        .all()
    )
    vendor_trends: dict[str, dict[str, int]] = {}
    for t in vendor_trays:
        v = vendor_trends.setdefault(t.vendor_name, {"total": 0, "received": 0})
        v["total"] += 1
        if t.status in ("received", "returned"):
            v["received"] += 1

    manufacturer_rows = db.query(BaselineLibraryEntry).all()
    manufacturer_trends: dict[str, dict[str, int]] = {}
    for m in manufacturer_rows:
        entry = manufacturer_trends.setdefault(m.manufacturer_name, {"total": 0, "approved": 0})
        entry["total"] += 1
        if m.approval_status == "approved":
            entry["approved"] += 1

    return {
        "window_days": days,
        "quality_events": {"total": len(events), "by_severity": events_by_severity},
        "recurring_findings": recurring_findings,
        "capas": capa_lifecycle,
        "root_causes": causes,
        "first_pass_yield": fpy,
        "education_impact_avg_pct": education_impact_avg,
        "technician_trends": technician_trends,
        "vendor_trends": vendor_trends,
        "manufacturer_trends": manufacturer_trends,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def apply_learning_loop(db: Session, tenant_id: str, event_id: int) -> dict:
    """Section 10 — what a confirmed quality event actually updates."""
    event = _get_event(db, tenant_id, event_id)
    if not event.confirmed:
        raise ValueError(f"Quality event {event_id} has not been confirmed yet — confirm it first.")

    inspection_corr = (
        db.query(EventCorrelation)
        .filter(
            EventCorrelation.tenant_id == tenant_id, EventCorrelation.event_id == event_id,
            EventCorrelation.target_type == "inspection", EventCorrelation.target_id != "",
        )
        .first()
    )

    clinical_memory_updated = False
    case_id = None
    if inspection_corr is not None:
        insp = db.query(models.Inspection).filter(models.Inspection.id == int(inspection_corr.target_id)).first()
        if insp is not None and is_significant(
            risk_tier=event.classification_risk_level or "medium",
            is_critical_finding=(event.classification_risk_level == "critical"),
            has_override=False, finding_type=event.finding_type or "",
        ):
            case = save_or_update_case(
                db, tenant_id, insp, finding_type=event.finding_type or "unknown",
                clinical_reasoning=event.narrative, outcome="or_confirmed_quality_event",
            )
            db.commit()
            db.refresh(case)
            clinical_memory_updated = True
            case_id = case.id

    return {
        "event_id": event_id,
        "clinical_memory_updated": clinical_memory_updated,
        "clinical_case_id": case_id,
        "note": (
            "Knowledge Graph, Reasoning Engine, Education Library, and Trend Analytics are computed "
            "live from underlying inspection/finding/competency data — they reflect this confirmed "
            "event automatically on next read, with no separate write step required. Clinical Memory "
            "(the ClinicalCase library) is the one system with its own persisted state, updated above "
            "when the correlated inspection qualifies as a significant case."
        ),
        "disclaimer": DISCLAIMER,
    }
