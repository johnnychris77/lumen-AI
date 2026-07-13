"""Project Maestro, Sections 3 & 5: Leadership Recommendation Engine.

Section 3 ("specific") recommendations are generated one-per-priority-item,
directly citing the `MaestroPriorityItem` that triggered them (e.g. "Move
supervisor to review <facility>.", "Schedule <domain> competency for
<scope>.", "Generate CAPA draft: <title>."). Section 5 ("strategic")
recommendations are a periodic, higher-level digest derived from the
Operational Health Index and the full priority list rather than any single
item. Every recommendation is advisory only -- `human_review_required` is
always `True`, and nothing here calls `capa_suggestion_service.
create_capa_from_suggestion` or `forge_approval_service` directly; those
remain explicit, separate human-triggered actions.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.maestro_orchestration import (
    PRIORITY_HIGHEST_PRIORITY_CAPA,
    PRIORITY_HIGHEST_PRIORITY_EXECUTIVE_ISSUE,
    PRIORITY_HIGHEST_PRIORITY_INSPECTION,
    PRIORITY_HIGHEST_PRIORITY_REPAIR,
    PRIORITY_HIGHEST_RISK_EQUIPMENT,
    PRIORITY_HIGHEST_RISK_FACILITY,
    PRIORITY_HIGHEST_RISK_INSTRUMENT,
    PRIORITY_HIGHEST_RISK_TECHNICIAN_EDUCATION_NEED,
    PRIORITY_HIGHEST_RISK_WORKFLOW,
    RECOMMENDATION_EDUCATION_PRIORITIES,
    RECOMMENDATION_ESCALATE_REPAIR_BACKLOG,
    RECOMMENDATION_EQUIPMENT_UTILIZATION,
    RECOMMENDATION_GENERATE_CAPA_DRAFT,
    RECOMMENDATION_INSPECTION_PRIORITIES,
    RECOMMENDATION_MOVE_SUPERVISOR,
    RECOMMENDATION_PUBLISH_BASELINE,
    RECOMMENDATION_QUALITY_INITIATIVES,
    RECOMMENDATION_RESOURCE_ALLOCATION,
    RECOMMENDATION_REVIEW_CORROSION_TREND,
    RECOMMENDATION_SCHEDULE_COMPETENCY,
    RECOMMENDATION_STAFFING_CHANGES,
    TIMELINE_QUARTER,
    TIMELINE_THIS_WEEK,
    TIMELINE_TODAY,
    MaestroPriorityItem,
    MaestroRecommendation,
)
from app.models.veritas_evidence import VeritasEvidenceConflict
from app.services import maestro_priority_engine_service
from app.services.sage_knowledge_gap_service import list_gaps

_CORROSION_FAILURE_CATEGORIES = {"corrosion", "rust", "pitting"}

# Baseline-governance-relevant conflict types (Veritas Section 9) that a
# supervisor resolves by publishing an updated baseline.
_BASELINE_CONFLICT_TYPES = {
    "multiple_active_approved_baselines",
    "baseline_superseded_after_inspection",
}


def _to_dict(row: MaestroRecommendation) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "priority_item_id": row.priority_item_id,
        "recommendation_type": row.recommendation_type,
        "subject": row.subject,
        "rationale": row.rationale,
        "confidence": row.confidence,
        "specialists_consulted": json.loads(row.specialists_consulted_json or "[]"),
        "evidence": json.loads(row.evidence_json or "{}"),
        "timeline_horizon": row.timeline_horizon,
        "status": row.status,
        "human_review_required": row.human_review_required,
        "agent_version": row.agent_version,
    }


def _persist(
    db: Session, tenant_id: str, *, priority_item_id: int | None, recommendation_type: str, subject: str,
    rationale: str, specialists: list[str], evidence: dict, timeline_horizon: str = TIMELINE_TODAY,
    confidence: str = "moderate",
) -> MaestroRecommendation:
    row = MaestroRecommendation(
        tenant_id=tenant_id, priority_item_id=priority_item_id, recommendation_type=recommendation_type,
        subject=subject[:300], rationale=rationale, confidence=confidence,
        specialists_consulted_json=json.dumps(specialists), evidence_json=json.dumps(evidence),
        timeline_horizon=timeline_horizon,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


_SPECIALIST_BY_SOURCE = {
    "sentinelx": ["sentinelx"],
    "sage": ["sage"],
    "vulcan": ["vulcan"],
    "capa_suggestion_service": ["capa_suggestion_service"],
    "or_connect": ["or_connect"],
    "executive_risk_signal": ["executive_risk_signal"],
}


def _specific_recommendation_for_item(db: Session, tenant_id: str, item) -> MaestroRecommendation | None:
    evidence = json.loads(item.evidence_json or "{}")
    specialists = _SPECIALIST_BY_SOURCE.get(item.source_specialist, [item.source_specialist])

    if item.category == PRIORITY_HIGHEST_RISK_FACILITY:
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_MOVE_SUPERVISOR,
            subject=f"Move supervisor to {item.subject}.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    if item.category == PRIORITY_HIGHEST_RISK_INSTRUMENT:
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_MOVE_SUPERVISOR,
            subject=f"Move supervisor to review {item.subject}.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    if item.category == PRIORITY_HIGHEST_RISK_WORKFLOW:
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_INSPECTION_PRIORITIES,
            subject="Review process-variation workflow controls.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    if item.category == PRIORITY_HIGHEST_RISK_TECHNICIAN_EDUCATION_NEED:
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_SCHEDULE_COMPETENCY,
            subject=f"Schedule {item.subject} competency.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    if item.category == PRIORITY_HIGHEST_RISK_EQUIPMENT:
        failure_category = (evidence.get("reliability_category") or "").lower()
        if any(term in failure_category for term in _CORROSION_FAILURE_CATEGORIES):
            return _persist(
                db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_REVIEW_CORROSION_TREND,
                subject=f"Review {item.subject} corrosion trend.",
                rationale=item.rationale, specialists=specialists, evidence=evidence,
            )
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_EQUIPMENT_UTILIZATION,
            subject=f"Review utilization for {item.subject}.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    if item.category == PRIORITY_HIGHEST_PRIORITY_CAPA:
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_GENERATE_CAPA_DRAFT,
            subject="Generate CAPA draft.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    if item.category == PRIORITY_HIGHEST_PRIORITY_INSPECTION:
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_INSPECTION_PRIORITIES,
            subject=f"Prioritize {item.subject}.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    if item.category == PRIORITY_HIGHEST_PRIORITY_REPAIR:
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_ESCALATE_REPAIR_BACKLOG,
            subject="Escalate repair backlog.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    if item.category == PRIORITY_HIGHEST_PRIORITY_EXECUTIVE_ISSUE:
        return _persist(
            db, tenant_id, priority_item_id=item.id, recommendation_type=RECOMMENDATION_QUALITY_INITIATIVES,
            subject=f"Address executive risk: {item.subject}.",
            rationale=item.rationale, specialists=specialists, evidence=evidence,
        )
    return None


def _publish_baseline_recommendation(db: Session, tenant_id: str) -> MaestroRecommendation | None:
    conflict = (
        db.query(VeritasEvidenceConflict)
        .filter(
            VeritasEvidenceConflict.tenant_id == tenant_id,
            VeritasEvidenceConflict.conflict_type.in_(_BASELINE_CONFLICT_TYPES),
            VeritasEvidenceConflict.resolved.is_(False),
        )
        .order_by(VeritasEvidenceConflict.created_at.desc())
        .first()
    )
    if conflict is None:
        return None
    return _persist(
        db, tenant_id, priority_item_id=None, recommendation_type=RECOMMENDATION_PUBLISH_BASELINE,
        subject="Publish updated baseline.",
        rationale=conflict.recommended_resolution or f"Unresolved baseline conflict: {conflict.conflict_type}.",
        specialists=["veritas"],
        evidence={"conflict_type": conflict.conflict_type, "severity": conflict.severity, "conflict_id": conflict.id},
    )


def generate_recommendations(
    db: Session, tenant_id: str, priority_items: list[MaestroPriorityItem] | None = None,
) -> list[MaestroRecommendation]:
    """Section 3: converts each real priority item (plus any pending
    Veritas baseline conflict) into one specific, evidence-linked
    leadership recommendation. Runs the Priority Engine itself only if
    `priority_items` isn't already supplied by the caller -- callers that
    already have a fresh batch (e.g. `run_daily_orchestration`) must pass
    it in rather than triggering a second, duplicate Priority Engine run."""
    if priority_items is None:
        priority_items = maestro_priority_engine_service.compute_priorities(db, tenant_id)

    recommendations: list[MaestroRecommendation] = []
    for item in priority_items:
        rec = _specific_recommendation_for_item(db, tenant_id, item)
        if rec is not None:
            recommendations.append(rec)

    baseline_rec = _publish_baseline_recommendation(db, tenant_id)
    if baseline_rec is not None:
        recommendations.append(baseline_rec)

    return recommendations


def generate_strategic_recommendations(db: Session, tenant_id: str) -> list[MaestroRecommendation]:
    """Section 5: a periodic, higher-level digest across the six strategic
    categories, derived from the Operational Health Index and the current
    priority list rather than any single item."""
    from app.services.maestro_health_index_service import compute_operational_health

    health = compute_operational_health(db, tenant_id)
    priority_items = maestro_priority_engine_service.latest_priorities(db, tenant_id) or [
        maestro_priority_engine_service.to_dict(r) for r in maestro_priority_engine_service.compute_priorities(db, tenant_id)
    ]

    recommendations: list[MaestroRecommendation] = []

    if health.equipment_score is not None and health.equipment_score < 70:
        recommendations.append(_persist(
            db, tenant_id, priority_item_id=None, recommendation_type=RECOMMENDATION_RESOURCE_ALLOCATION,
            subject="Reallocate maintenance resources toward declining equipment reliability.",
            rationale=f"Equipment health score is {health.equipment_score}, below the 70 review threshold.",
            specialists=["vulcan", "phoenix"], evidence={"equipment_score": health.equipment_score},
            timeline_horizon=TIMELINE_THIS_WEEK,
        ))

    repair_items = [p for p in priority_items if p["category"] == "highest_priority_repair"]
    if repair_items:
        recommendations.append(_persist(
            db, tenant_id, priority_item_id=repair_items[0]["id"], recommendation_type=RECOMMENDATION_STAFFING_CHANGES,
            subject="Review repair-vendor staffing capacity.",
            rationale=repair_items[0]["rationale"], specialists=["or_connect"],
            evidence=repair_items[0]["evidence"], timeline_horizon=TIMELINE_THIS_WEEK,
        ))

    open_gaps = list_gaps(db, tenant_id, status="open")
    if open_gaps:
        recommendations.append(_persist(
            db, tenant_id, priority_item_id=None, recommendation_type=RECOMMENDATION_EDUCATION_PRIORITIES,
            subject=f"Prioritize education plans for {len(open_gaps)} open competency gap(s).",
            rationale="Aggregated across all currently open Sage knowledge gaps for this tenant.",
            specialists=["sage"], evidence={"open_gap_count": len(open_gaps)}, timeline_horizon=TIMELINE_QUARTER,
        ))

    if health.quality_score is not None and health.quality_score < 70:
        recommendations.append(_persist(
            db, tenant_id, priority_item_id=None, recommendation_type=RECOMMENDATION_QUALITY_INITIATIVES,
            subject="Launch a quality improvement initiative.",
            rationale=f"Quality health score is {health.quality_score}, below the 70 review threshold.",
            specialists=["phoenix"], evidence={"quality_score": health.quality_score}, timeline_horizon=TIMELINE_QUARTER,
        ))

    return recommendations


def to_dict(row: MaestroRecommendation) -> dict:
    return _to_dict(row)


def list_recommendations(
    db: Session, tenant_id: str, *, status: str = "", timeline_horizon: str = "",
) -> list[dict]:
    q = db.query(MaestroRecommendation).filter(MaestroRecommendation.tenant_id == tenant_id)
    if status:
        q = q.filter(MaestroRecommendation.status == status)
    if timeline_horizon:
        q = q.filter(MaestroRecommendation.timeline_horizon == timeline_horizon)
    return [_to_dict(r) for r in q.order_by(MaestroRecommendation.created_at.desc()).all()]


def update_status(db: Session, tenant_id: str, recommendation_id: int, status: str) -> MaestroRecommendation | None:
    row = (
        db.query(MaestroRecommendation)
        .filter(MaestroRecommendation.tenant_id == tenant_id, MaestroRecommendation.id == recommendation_id)
        .first()
    )
    if row is None:
        return None
    row.status = status
    db.commit()
    db.refresh(row)
    return row
