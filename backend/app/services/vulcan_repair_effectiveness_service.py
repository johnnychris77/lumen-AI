"""Project Vulcan, Section 5: Repair Effectiveness Intelligence.

Composes the real `RepairRequest` row (`app.models.or_connect`, tracks repair
date/vendor/type/status/return dates/failure_category) with the real
`InspectionFinding` rows before and after the repair to classify repair
outcome. `RepairRequest` has no zone column of its own, so the affected zone
is derived honestly from the findings on the inspection that triggered the
repair -- never fabricated.

Never claims a vendor performed a bad repair -- outcomes describe what the
evidence shows (recurrence/new defect/effective), not vendor fault.
"""
from __future__ import annotations

from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import REPAIR_REPLACED, REPAIR_RETURNED, RepairRequest
from app.models.vulcan_reliability import (
    REPAIR_OUTCOME_EFFECTIVE,
    REPAIR_OUTCOME_FAILURE_RECURRED,
    REPAIR_OUTCOME_NEW_DEFECT_DETECTED,
    REPAIR_OUTCOME_PARTIALLY_EFFECTIVE,
    REPAIR_OUTCOME_UNABLE_TO_DETERMINE,
)
from app.services.vulcan_progression_service import _inspections_for_identity


def _findings_for_inspection(db, inspection_id: int) -> list[InspectionFinding]:
    return db.query(InspectionFinding).filter(InspectionFinding.inspection_id == inspection_id).all()


def _pre_repair_zone(db, repair: RepairRequest) -> tuple[str, list[InspectionFinding]]:
    pre_findings = _findings_for_inspection(db, repair.inspection_id)
    if not pre_findings:
        return "", []
    worst = max(pre_findings, key=lambda f: f.severity_index)
    return worst.zone, pre_findings


def classify_repair_outcome(db, tenant_id: str, repair: RepairRequest) -> dict:
    """Section 5: classify one repair's real-world outcome from evidence."""
    zone, pre_findings = _pre_repair_zone(db, repair)
    pre_types = {f.finding_type for f in pre_findings}

    if repair.status not in (REPAIR_RETURNED, REPAIR_REPLACED):
        return {
            "repair_request_id": repair.id,
            "instrument_identity": repair.instrument_identity,
            "anatomy_zone": zone,
            "repair_outcome": REPAIR_OUTCOME_UNABLE_TO_DETERMINE,
            "time_to_recurrence_days": None,
            "evidence": {"reason": "repair not yet returned/replaced"},
        }

    return_date = repair.actual_return_date or repair.expected_return_date
    inspections = _inspections_for_identity(db, tenant_id, repair.instrument_identity)
    post_repair_inspections = [
        i for i in inspections if return_date and i.created_at and i.created_at > return_date
    ]

    if not post_repair_inspections:
        return {
            "repair_request_id": repair.id,
            "instrument_identity": repair.instrument_identity,
            "anatomy_zone": zone,
            "repair_outcome": REPAIR_OUTCOME_UNABLE_TO_DETERMINE,
            "time_to_recurrence_days": None,
            "evidence": {"reason": "no post-repair inspection on record yet"},
        }

    first_recurrence_at = None
    outcome = REPAIR_OUTCOME_EFFECTIVE
    for insp in post_repair_inspections:
        post_findings = _findings_for_inspection(db, insp.id)
        same_zone = [f for f in post_findings if zone and f.zone == zone]
        if not same_zone:
            continue
        first_recurrence_at = insp.created_at
        recurring_types = {f.finding_type for f in same_zone}
        max_severity = max((f.severity_index for f in same_zone), default=0)
        pre_max_severity = max((f.severity_index for f in pre_findings), default=0)
        if recurring_types - pre_types:
            outcome = REPAIR_OUTCOME_NEW_DEFECT_DETECTED
        elif max_severity >= pre_max_severity and max_severity >= 1:
            outcome = REPAIR_OUTCOME_FAILURE_RECURRED
        elif max_severity >= 1:
            outcome = REPAIR_OUTCOME_PARTIALLY_EFFECTIVE
        break

    time_to_recurrence_days = None
    if first_recurrence_at and return_date:
        time_to_recurrence_days = max(0, (first_recurrence_at - return_date).days)

    return {
        "repair_request_id": repair.id,
        "instrument_identity": repair.instrument_identity,
        "anatomy_zone": zone,
        "repair_outcome": outcome,
        "time_to_recurrence_days": time_to_recurrence_days,
        "evidence": {
            "pre_repair_finding_types": sorted(pre_types),
            "post_repair_inspections_reviewed": len(post_repair_inspections),
            "vendor_name": repair.vendor_name,
            "repair_type": repair.repair_type,
            "failure_category": repair.failure_category,
        },
    }


def repair_history_for_instrument(db, tenant_id: str, instrument_identity: str) -> list[dict]:
    repairs = (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.instrument_identity == instrument_identity)
        .order_by(RepairRequest.created_at.asc())
        .all()
    )
    return [classify_repair_outcome(db, tenant_id, r) for r in repairs]
