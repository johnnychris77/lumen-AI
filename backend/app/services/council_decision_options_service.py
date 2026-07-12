"""Project Council, Section 7: Decision Options and Tradeoff Analysis.

Builds one `CouncilDecisionOption` per distinct recommended action across
the Council's assessments -- each option's evidence and tradeoffs trace
back to the specific specialists who proposed it. `financial_impact` is
only ever populated from a real figure elsewhere in the platform; since no
such figure exists for these options today, it is always left blank
rather than fabricated (per the brief's explicit instruction).
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.council_leadership import APPROVAL_TIER_BY_ROLE_NAME, APPROVER_SUPERVISOR, CouncilDecisionOption

_OPTION_LABELS = [chr(ord("A") + i) for i in range(26)]

_CONFIDENCE_RANK = {"low": 0, "moderate": 1, "high": 2}
_URGENT_TO_RISK = {"urgent": "high", "routine": "moderate"}


def _to_dict(row: CouncilDecisionOption) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "council_case_id": row.council_case_id,
        "option_label": row.option_label,
        "option_title": row.option_title,
        "benefits": row.benefits,
        "risks": row.risks,
        "clinical_risk": row.clinical_risk,
        "operational_impact": row.operational_impact,
        "financial_impact": row.financial_impact,
        "evidence_strength": row.evidence_strength,
        "reversibility": row.reversibility,
        "required_authority": row.required_authority,
        "expected_time_to_resolution": row.expected_time_to_resolution,
    }


def _reversibility_for(option_title: str) -> str:
    lowered = option_title.lower()
    if "remove" in lowered or "discard" in lowered or "retire" in lowered:
        return "irreversible"
    return "reversible"


def _time_to_resolution_for(option_title: str) -> str:
    lowered = option_title.lower()
    if "manufacturer" in lowered:
        return "1-2 weeks (external turnaround)"
    if "repair" in lowered or "hold" in lowered:
        return "Several days"
    return "Same day"


def generate_decision_options(db: Session, tenant_id: str, council_case_id: int, assessments: list[dict]) -> list[CouncilDecisionOption]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for a in assessments:
        action = a.get("recommended_action", "").strip()
        if action:
            grouped[action].append(a)

    if not grouped:
        return []

    rows = []
    for index, (option_title, supporters) in enumerate(grouped.items()):
        benefits = "; ".join(sorted({s["significance"] for s in supporters if s["significance"]})) or "Addresses the concern raised by the recommending specialist(s)."
        risks = "; ".join(sorted({s["evidence_limitations"] for s in supporters if s["evidence_limitations"]})) or "Does not address concerns raised by dissenting specialist(s), if any."

        urgencies = [s["urgency"] for s in supporters]
        clinical_risk = _URGENT_TO_RISK["urgent"] if "urgent" in urgencies else "low"

        confidences = [_CONFIDENCE_RANK.get(s["confidence"], 1) for s in supporters]
        avg_confidence = sum(confidences) / len(confidences)
        evidence_strength = "high" if avg_confidence >= 1.5 else "moderate" if avg_confidence >= 0.75 else "low"

        max_tier = max(APPROVAL_TIER_BY_ROLE_NAME.get(s["human_role_required"], 1) for s in supporters)
        required_authority = next((k for k, v in APPROVAL_TIER_BY_ROLE_NAME.items() if v == max_tier), APPROVER_SUPERVISOR)

        row = CouncilDecisionOption(
            tenant_id=tenant_id,
            council_case_id=council_case_id,
            option_label=_OPTION_LABELS[index] if index < len(_OPTION_LABELS) else str(index),
            option_title=option_title,
            benefits=benefits,
            risks=risks,
            clinical_risk=clinical_risk,
            operational_impact=f"Proposed by: {', '.join(s['specialist_key'] for s in supporters)}.",
            financial_impact="",
            evidence_strength=evidence_strength,
            reversibility=_reversibility_for(option_title),
            required_authority=required_authority,
            expected_time_to_resolution=_time_to_resolution_for(option_title),
        )
        db.add(row)
        rows.append(row)

    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def options_for_case(db: Session, tenant_id: str, council_case_id: int) -> list[dict]:
    rows = (
        db.query(CouncilDecisionOption)
        .filter(CouncilDecisionOption.tenant_id == tenant_id, CouncilDecisionOption.council_case_id == council_case_id)
        .order_by(CouncilDecisionOption.option_label.asc())
        .all()
    )
    return [_to_dict(r) for r in rows]
