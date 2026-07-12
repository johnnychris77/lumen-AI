"""Project Council, Section 17: Specialist Performance Review.

Aggregate, non-punitive performance signal computed entirely on the fly
from `CouncilSpecialistAssessment` + `CouncilDissentRecord` +
`CouncilOutcomeReview` -- never a separate, independently-drifting
scoreboard table. This data is read-only reporting: nothing in this
module feeds back into `council_consensus_service.classify_consensus`,
so a specialist's historical performance can never automatically
suppress a valid current safety dissent (Section 16).
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.council_leadership import (
    CouncilCase,
    CouncilDissentRecord,
    CouncilOutcomeReview,
    CouncilSpecialistAssessment,
)


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def specialist_performance_summary(db: Session, tenant_id: str) -> dict:
    assessments = (
        db.query(CouncilSpecialistAssessment)
        .filter(CouncilSpecialistAssessment.tenant_id == tenant_id)
        .all()
    )
    dissents = db.query(CouncilDissentRecord).filter(CouncilDissentRecord.tenant_id == tenant_id).all()
    cases_by_id = {c.id: c for c in db.query(CouncilCase).filter(CouncilCase.tenant_id == tenant_id).all()}
    outcomes_by_case: dict[int, list[bool | None]] = defaultdict(list)
    for o in db.query(CouncilOutcomeReview).filter(CouncilOutcomeReview.tenant_id == tenant_id).all():
        outcomes_by_case[o.council_case_id].append(o.dissent_valid)

    by_specialist: dict[str, dict] = {}

    def bucket(specialist_key: str) -> dict:
        return by_specialist.setdefault(specialist_key, {
            "total_assessments": 0,
            "confidence_distribution": {"low": 0, "moderate": 0, "high": 0},
            "abstention_count": 0,
            "agreement_with_final_recommendation": 0,
            "resolved_case_count": 0,
            "dissent_count": 0,
            "dissent_validated_count": 0,
            "dissent_evaluated_count": 0,
        })

    for a in assessments:
        b = bucket(a.specialist_key)
        b["total_assessments"] += 1
        b["confidence_distribution"][a.confidence] = b["confidence_distribution"].get(a.confidence, 0) + 1
        if a.conclusion.startswith("insufficient_data"):
            b["abstention_count"] += 1

        case = cases_by_id.get(a.council_case_id)
        if case is not None and case.recommended_action:
            b["resolved_case_count"] += 1
            if _normalize(a.recommended_action) == _normalize(case.recommended_action):
                b["agreement_with_final_recommendation"] += 1

    for d in dissents:
        b = bucket(d.dissenting_specialist)
        b["dissent_count"] += 1
        for dissent_valid in outcomes_by_case.get(d.council_case_id, []):
            if dissent_valid is not None:
                b["dissent_evaluated_count"] += 1
                if dissent_valid:
                    b["dissent_validated_count"] += 1

    for specialist_key, b in by_specialist.items():
        b["agreement_rate"] = (
            round(b["agreement_with_final_recommendation"] / b["resolved_case_count"], 2) if b["resolved_case_count"] else None
        )
        b["dissent_accuracy"] = (
            round(b["dissent_validated_count"] / b["dissent_evaluated_count"], 2) if b["dissent_evaluated_count"] else None
        )

    return {
        "by_specialist": by_specialist,
        "note": (
            "Performance is aggregate and non-punitive; it is never used to automatically suppress a "
            "specialist's current safety or evidence dissent."
        ),
    }
