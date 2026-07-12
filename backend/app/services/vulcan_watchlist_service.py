"""Project Vulcan, Section 10: Reliability Watchlists.

Every watchlist is a live query over `VulcanReliabilityAssessment` (and
`RepairRequest` for repeat-repair) -- zero new tables. Each entry carries the
assessment's own evidence/reasoning fields so every watchlist row is
explainable and auditable, per the brief's explicit requirement.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.or_connect import RepairRequest
from app.models.vulcan_reliability import (
    DISPOSITION_MANUFACTURER_EVALUATION,
    DISPOSITION_RETIREMENT_CANDIDATE,
    FAIL_CRACK,
    FAIL_DAMAGED_DRILL_FLUTE,
    FAIL_DAMAGED_HINGE,
    FAIL_DAMAGED_O_RING,
    FAIL_LOOSE_JOINT,
    FAIL_MISALIGNMENT,
    FAIL_RUST,
    FAILURE_TAXONOMY,
    PROGRESSION_RAPIDLY_WORSENING,
    PROGRESSION_SLOWLY_WORSENING,
    RELIABILITY_REMOVE_FROM_SERVICE_CANDIDATE,
    TAXONOMY_GROUP_CLEANING,
    TAXONOMY_GROUP_INSULATION,
    VulcanReliabilityAssessment,
)
from app.services.vulcan_reliability_agent_service import to_dict

_CORROSION_LEAF = "corrosion"
_STRUCTURAL_LEAVES = (FAIL_CRACK, FAIL_MISALIGNMENT, FAIL_LOOSE_JOINT, FAIL_DAMAGED_HINGE)


def _latest_per_instrument(db: Session, tenant_id: str) -> list[VulcanReliabilityAssessment]:
    rows = (
        db.query(VulcanReliabilityAssessment)
        .filter(VulcanReliabilityAssessment.tenant_id == tenant_id)
        .order_by(VulcanReliabilityAssessment.created_at.asc())
        .all()
    )
    latest: dict[str, VulcanReliabilityAssessment] = {}
    for row in rows:
        latest[row.instrument_identity] = row
    return list(latest.values())


def recurring_corrosion(db: Session, tenant_id: str) -> list[dict]:
    return [to_dict(r) for r in _latest_per_instrument(db, tenant_id) if r.failure_category == _CORROSION_LEAF and r.recurrence_count >= 2]


def recurring_rust(db: Session, tenant_id: str) -> list[dict]:
    return [to_dict(r) for r in _latest_per_instrument(db, tenant_id) if r.failure_category == FAIL_RUST and r.recurrence_count >= 2]


def repeated_cleaning_failure(db: Session, tenant_id: str) -> list[dict]:
    cleaning_leaves = set(FAILURE_TAXONOMY.get(TAXONOMY_GROUP_CLEANING, []))
    return [to_dict(r) for r in _latest_per_instrument(db, tenant_id) if r.failure_category in cleaning_leaves and r.recurrence_count >= 2]


def repeat_repair(db: Session, tenant_id: str) -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for r in db.query(RepairRequest).filter(RepairRequest.tenant_id == tenant_id):
        counts[r.instrument_identity] += 1
    repeat_identities = {identity for identity, count in counts.items() if count >= 2}
    return [to_dict(r) for r in _latest_per_instrument(db, tenant_id) if r.instrument_identity in repeat_identities]


def structural_defect_progression(db: Session, tenant_id: str) -> list[dict]:
    return [
        to_dict(r) for r in _latest_per_instrument(db, tenant_id)
        if r.failure_category in _STRUCTURAL_LEAVES
        and r.progression in (PROGRESSION_RAPIDLY_WORSENING, PROGRESSION_SLOWLY_WORSENING)
    ]


def damaged_o_rings(db: Session, tenant_id: str) -> list[dict]:
    return [to_dict(r) for r in _latest_per_instrument(db, tenant_id) if r.failure_category == FAIL_DAMAGED_O_RING]


def insulation_failures(db: Session, tenant_id: str) -> list[dict]:
    insulation_leaves = set(FAILURE_TAXONOMY.get(TAXONOMY_GROUP_INSULATION, []))
    return [to_dict(r) for r in _latest_per_instrument(db, tenant_id) if r.failure_category in insulation_leaves]


def drill_flute_failures(db: Session, tenant_id: str) -> list[dict]:
    return [
        to_dict(r) for r in _latest_per_instrument(db, tenant_id)
        if r.failure_category == FAIL_DAMAGED_DRILL_FLUTE or r.anatomy_zone == "flutes"
    ]


def box_lock_failures(db: Session, tenant_id: str) -> list[dict]:
    return [to_dict(r) for r in _latest_per_instrument(db, tenant_id) if r.anatomy_zone == "box lock"]


def instruments_awaiting_manufacturer_review(db: Session, tenant_id: str) -> list[dict]:
    return [to_dict(r) for r in _latest_per_instrument(db, tenant_id) if r.recommended_disposition == DISPOSITION_MANUFACTURER_EVALUATION]


def retirement_candidates(db: Session, tenant_id: str) -> list[dict]:
    return [
        to_dict(r) for r in _latest_per_instrument(db, tenant_id)
        if r.recommended_disposition == DISPOSITION_RETIREMENT_CANDIDATE
        or r.reliability_category == RELIABILITY_REMOVE_FROM_SERVICE_CANDIDATE
    ]


WATCHLISTS = {
    "recurring_corrosion": recurring_corrosion,
    "recurring_rust": recurring_rust,
    "repeated_cleaning_failure": repeated_cleaning_failure,
    "repeat_repair": repeat_repair,
    "structural_defect_progression": structural_defect_progression,
    "damaged_o_rings": damaged_o_rings,
    "insulation_failures": insulation_failures,
    "drill_flute_failures": drill_flute_failures,
    "box_lock_failures": box_lock_failures,
    "instruments_awaiting_manufacturer_review": instruments_awaiting_manufacturer_review,
    "retirement_candidates": retirement_candidates,
}


def run_watchlist(db: Session, tenant_id: str, name: str) -> list[dict] | None:
    fn = WATCHLISTS.get(name)
    return fn(db, tenant_id) if fn else None
