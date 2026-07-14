"""Advisor — Phase 7 §5: Workflow Impact Analysis.

Reuses existing, already-reviewed computations rather than re-deriving
them: ``sla_monitoring_service.sla_monitoring()`` for inspection/review/
turnaround durations, ``technician_workload_service.technician_workload()``
for per-technician load, and ``quality_dashboard_service.dashboard_summary()``
for override rate and repeat-inspection (reclean) rate. This module adds
only what genuinely didn't exist before Advisor: adoption (of the
recommendation itself, from real ``AdvisoryRecommendationInteraction``
rows), workflow interruptions (a rejection forcing a detour), and a
training-requirements signal derived from real reject/modify rates.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.db import models
from app.models.advisory_pilot import AdvisoryRecommendationInteraction
from app.services import quality_dashboard_service, sla_monitoring_service, technician_workload_service

_HIGH_REJECT_RATE_THRESHOLD = 0.3


def adoption_rate(db: Session, tenant_id: str, *, model_id: str | None = None) -> dict[str, Any]:
    """Fraction of has-image inspections that actually got an advisory
    interaction recorded — real tool usage, not a fabricated engagement
    number. Scoped to ``model_id`` when given, since adoption is a
    property of one candidate model's own rollout, not a blanket
    all-time, all-models tenant metric that would otherwise mix in
    interactions from a different pilot."""
    total_eligible = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.has_image.is_(True))
        .count()
    )
    interacted_q = (
        db.query(AdvisoryRecommendationInteraction.inspection_id)
        .filter(AdvisoryRecommendationInteraction.tenant_id == tenant_id)
    )
    if model_id:
        interacted_q = interacted_q.filter(AdvisoryRecommendationInteraction.model_id == model_id)
    interacted_inspections = interacted_q.distinct().count()
    return {
        "total_eligible_inspections": total_eligible,
        "inspections_with_interaction": interacted_inspections,
        "adoption_rate": round(interacted_inspections / total_eligible, 4) if total_eligible else None,
    }


def acceptance_and_override_rates(interactions: list[AdvisoryRecommendationInteraction]) -> dict[str, Any]:
    total = len(interactions)
    accepted = sum(1 for i in interactions if i.decision == "accepted")
    modified = sum(1 for i in interactions if i.decision == "modified")
    rejected = sum(1 for i in interactions if i.decision == "rejected")
    return {
        "total_interactions": total,
        "accepted": accepted,
        "modified": modified,
        "rejected": rejected,
        "acceptance_rate": round(accepted / total, 4) if total else None,
        "override_rate": round((modified + rejected) / total, 4) if total else None,
    }


def workflow_interruptions(interactions: list[AdvisoryRecommendationInteraction]) -> dict[str, Any]:
    """A rejected recommendation forces a detour back to supervisor review
    — a real, countable interruption signal."""
    rejections = [i for i in interactions if i.decision == "rejected"]
    return {
        "interruption_count": len(rejections),
        "interruption_rate": round(len(rejections) / len(interactions), 4) if interactions else None,
    }


def training_requirements(interactions: list[AdvisoryRecommendationInteraction]) -> list[dict[str, Any]]:
    """Flag technicians whose own reject rate is high — a real, derived
    signal that more training/onboarding may help, never a guess about a
    specific individual's competency beyond what their own decisions show."""
    by_user: dict[str, list[AdvisoryRecommendationInteraction]] = defaultdict(list)
    for i in interactions:
        if i.decided_by:
            by_user[i.decided_by].append(i)

    flagged = []
    for user, rows in by_user.items():
        rejected = sum(1 for r in rows if r.decision == "rejected")
        reject_rate = rejected / len(rows) if rows else 0.0
        if reject_rate >= _HIGH_REJECT_RATE_THRESHOLD:
            flagged.append({
                "user": user, "n": len(rows), "reject_rate": round(reject_rate, 4),
                "recommendation": "Consider additional onboarding/training on interpreting AI recommendations.",
            })
    return sorted(flagged, key=lambda f: f["reject_rate"], reverse=True)


def impact_summary(
    db: Session, tenant_id: str, interactions: list[AdvisoryRecommendationInteraction], *, model_id: str | None = None,
) -> dict[str, Any]:
    """§5 — the full workflow impact analysis payload."""
    return {
        "turnaround": sla_monitoring_service.sla_monitoring(db, tenant_id),
        "technician_workload": technician_workload_service.technician_workload(db, tenant_id),
        "quality_dashboard": quality_dashboard_service.dashboard_summary(db, tenant_id),
        "adoption": adoption_rate(db, tenant_id, model_id=model_id),
        "acceptance_and_override": acceptance_and_override_rates(interactions),
        "workflow_interruptions": workflow_interruptions(interactions),
        "training_requirements": training_requirements(interactions),
        "human_review_required": True,
    }
