"""Phase 23 §9 — Enterprise Health Dashboard aggregation (/cios-dashboard).

Every figure here is computed live from real rows or from the honest,
already-established Phase 20/21/22 aggregate functions — nothing is
fabricated, and a metric is `None` rather than a misleading default when
there isn't enough data yet.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.registry import get_registry
from app.cios.governance import governance_snapshot
from app.db import models
from app.models.digital_quality_twin import QualityTwinState
from app.models.supervisor_review import SupervisorReview
from app.services.inspection_coverage import compute_coverage
from app.services.knowledge_graph_service import enterprise_knowledge_analytics, learning_confidence
from app.services.pre_sterilization_command_center_service import (
    _annotate,
    _reviewed_ids,
    clinical_inspection_readiness,
)


def _average_inspection_time_minutes(inspections: list, reviews_by_inspection: dict) -> float | None:
    durations = []
    for insp in inspections:
        review = reviews_by_inspection.get(insp.id)
        if review is None or insp.created_at is None or review.created_at is None:
            continue
        delta = review.created_at - insp.created_at
        durations.append(delta.total_seconds() / 60)
    return round(sum(durations) / len(durations), 1) if durations else None


def _coverage_rate(inspections: list) -> float | None:
    imaged = [i for i in inspections if i.has_image]
    if not imaged:
        return None
    complete = 0
    for insp in imaged:
        try:
            inspected = json.loads(insp.inspected_zones_json or "null")
        except (TypeError, ValueError):
            inspected = None
        coverage = compute_coverage(insp.instrument_type, inspected)
        if coverage["quality"] in ("complete", "acceptable"):
            complete += 1
    return round(complete / len(imaged), 4)


def build_dashboard(db: Session, tenant_id: str) -> dict:
    inspections = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id)
        .order_by(models.Inspection.created_at.desc())
        .limit(5000)
        .all()
    )
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    reviews_by_inspection = {}
    for r in reviews:
        existing = reviews_by_inspection.get(r.inspection_id)
        if existing is None or r.created_at > existing.created_at:
            reviews_by_inspection[r.inspection_id] = r

    reviewed_ids = _reviewed_ids(db, tenant_id)
    annotated = _annotate(inspections, reviewed_ids)
    readiness = clinical_inspection_readiness(annotated)

    scored = [i for i in inspections if i.score_status == "scored" and i.confidence]
    ai_confidence = round(sum(i.confidence for i in scored) / len(scored), 2) if scored else None

    confidence = learning_confidence(db, tenant_id)
    analytics = enterprise_knowledge_analytics(db, tenant_id)

    registry = get_registry()
    degraded = [a["name"] for a in registry if a["health"] != "ok"]

    twin_count = db.query(QualityTwinState.id).filter(QualityTwinState.tenant_id == tenant_id).count()

    readiness_rate = readiness["readiness_rate"]
    coverage_rate = _coverage_rate(inspections)
    knowledge_confidence = confidence["knowledge_confidence"]
    risk_components = [c for c in (readiness_rate, coverage_rate, knowledge_confidence) if c is not None]
    enterprise_risk_index = round((1 - sum(risk_components) / len(risk_components)) * 100, 1) if risk_components else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_health": {
            "overall_status": "ok" if not degraded else "degraded",
            "degraded_agents": degraded,
            "agent_count": len(registry),
        },
        "inspection_throughput": len(inspections),
        "average_inspection_time_minutes": _average_inspection_time_minutes(inspections, reviews_by_inspection),
        "coverage_rate": coverage_rate,
        "supervisor_agreement_rate": knowledge_confidence,
        "ai_confidence": ai_confidence,
        "governance_versions": governance_snapshot(),
        "digital_twin_health": {
            "available": twin_count > 0,
            "snapshot_count": twin_count,
        },
        "most_common_findings": analytics["most_common_findings_by_manufacturer"],
        "most_common_zones": analytics["most_missed_anatomy_zones"],
        "enterprise_risk_index": enterprise_risk_index,
        "readiness_rate": readiness_rate,
        "human_review_required": True,
        "note": "Enterprise Risk Index is a composite indicator (readiness rate, coverage rate, supervisor agreement) — not a validated clinical risk score.",
    }
