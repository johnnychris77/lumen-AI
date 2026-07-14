"""Section 9 — Policy Simulation.

Before a threshold change becomes active, simulate it against historical
inspections. This module is strictly read-only: it never writes to
`Inspection` or `LumenDecisionRecord` rows, and it never activates a policy
— publication remains a separate, explicit governance step
(`baseline_decision_policy_service.activate_policy`).

Simulation replays each historical `LumenDecisionRecord`'s already-recorded
observation category and baseline similarity against a *candidate* set of
thresholds, and compares the resulting review requirement against what was
actually recorded at the time.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.lumen_decision_engine import LumenDecisionRecord
from app.services.observation_taxonomy import CONTAMINATION_LIKE_CATEGORIES


def _would_require_review(observation_category: str | None, baseline_similarity: float | None, candidate: dict[str, Any]) -> bool:
    if observation_category in CONTAMINATION_LIKE_CATEGORIES:
        # Section 4 — a candidate threshold change can never cancel a
        # contamination-like observation's own recleaning recommendation;
        # simulation must reflect that, not launder it away.
        return False
    if baseline_similarity is None:
        return True
    return baseline_similarity < candidate.get("technician_review_threshold", 0.70)


def simulate_policy(
    db: Session,
    *,
    tenant_id: str,
    candidate: dict[str, Any],
    instrument_family: str = "",
    anatomy_zone: str = "",
    facility: str = "",
) -> dict[str, Any]:
    query = db.query(LumenDecisionRecord).filter(LumenDecisionRecord.tenant_id == tenant_id)
    if instrument_family:
        query = query.filter(LumenDecisionRecord.instrument_family == instrument_family)
    if anatomy_zone:
        query = query.filter(LumenDecisionRecord.anatomy_zone == anatomy_zone)
    if facility:
        query = query.filter(LumenDecisionRecord.facility_name == facility)

    records = query.all()

    total_affected = 0
    previously_continued_now_review = 0
    previously_reviewed_now_technician_managed = 0
    probable_contamination_cases = 0
    instrument_family_impact: dict[str, int] = {}
    anatomy_zone_impact: dict[str, int] = {}
    facility_impact: dict[str, int] = {}

    for rec in records:
        was_reviewed = bool(rec.supervisor_required)
        now_reviewed = _would_require_review(rec.observation_category, rec.baseline_similarity, candidate)

        if rec.observation_category in CONTAMINATION_LIKE_CATEGORIES:
            probable_contamination_cases += 1

        if was_reviewed != now_reviewed:
            total_affected += 1
            if not was_reviewed and now_reviewed:
                previously_continued_now_review += 1
            elif was_reviewed and not now_reviewed:
                previously_reviewed_now_technician_managed += 1
            instrument_family_impact[rec.instrument_family or "unknown"] = (
                instrument_family_impact.get(rec.instrument_family or "unknown", 0) + 1
            )
            anatomy_zone_impact[rec.anatomy_zone or "unknown"] = (
                anatomy_zone_impact.get(rec.anatomy_zone or "unknown", 0) + 1
            )
            facility_impact[rec.facility_name or "unknown"] = (
                facility_impact.get(rec.facility_name or "unknown", 0) + 1
            )

    supervisor_workload_delta = previously_continued_now_review - previously_reviewed_now_technician_managed

    return {
        "inspections_evaluated": len(records),
        "inspections_affected": total_affected,
        "previously_continued_now_requires_review": previously_continued_now_review,
        "previously_reviewed_now_technician_managed": previously_reviewed_now_technician_managed,
        "probable_contamination_cases": probable_contamination_cases,
        "false_escalation_estimate": None if not records else round(
            previously_continued_now_review / max(len(records), 1), 3,
        ),
        "supervisor_workload_delta": supervisor_workload_delta,
        "instrument_family_impact": instrument_family_impact,
        "anatomy_zone_impact": anatomy_zone_impact,
        "facility_impact": facility_impact,
        "modifies_historical_records": False,
        "requires_authorized_publication": True,
    }
