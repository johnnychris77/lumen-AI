"""Project Council, Section 6: Dissent Registry.

Every specialist not in the consensus majority gets a dissent record --
dissent is always preserved and displayed prominently, never hidden from
the final report (Sections 6, 16).
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.council_leadership import SAFETY_VETO_SPECIALISTS, CouncilDissentRecord


def _to_dict(row: CouncilDissentRecord) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "council_case_id": row.council_case_id,
        "dissenting_specialist": row.dissenting_specialist,
        "disputed_conclusion": row.disputed_conclusion,
        "evidence_supporting_dissent": row.evidence_supporting_dissent,
        "risk_if_ignored": row.risk_if_ignored,
        "additional_evidence_required": row.additional_evidence_required,
        "proposed_alternative_action": row.proposed_alternative_action,
        "escalation_level": row.escalation_level,
    }


def record_dissent(
    db: Session, tenant_id: str, council_case_id: int, *, dissenting_assessment: dict, majority_position: str,
) -> CouncilDissentRecord:
    specialist_key = dissenting_assessment["specialist_key"]
    escalation_level = (
        "safety_critical"
        if specialist_key in SAFETY_VETO_SPECIALISTS and dissenting_assessment["urgency"] == "urgent"
        else "standard"
    )
    row = CouncilDissentRecord(
        tenant_id=tenant_id,
        council_case_id=council_case_id,
        dissenting_specialist=specialist_key,
        disputed_conclusion=majority_position,
        evidence_supporting_dissent=json.dumps(dissenting_assessment.get("evidence_used", {})),
        risk_if_ignored=dissenting_assessment.get("significance", ""),
        additional_evidence_required=dissenting_assessment.get("evidence_limitations", ""),
        proposed_alternative_action=dissenting_assessment.get("recommended_action", ""),
        escalation_level=escalation_level,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def record_dissent_records(
    db: Session, tenant_id: str, council_case_id: int, *, assessments: list[dict], consensus_result: dict,
) -> list[CouncilDissentRecord]:
    dissenting_keys = set(consensus_result.get("dissenting_specialists", []))
    if not dissenting_keys:
        return []
    majority_position = consensus_result.get("majority_position", "")
    rows = []
    for assessment in assessments:
        if assessment["specialist_key"] in dissenting_keys:
            rows.append(record_dissent(
                db, tenant_id, council_case_id, dissenting_assessment=assessment, majority_position=majority_position,
            ))
    return rows


def dissent_for_case(db: Session, tenant_id: str, council_case_id: int) -> list[dict]:
    rows = (
        db.query(CouncilDissentRecord)
        .filter(CouncilDissentRecord.tenant_id == tenant_id, CouncilDissentRecord.council_case_id == council_case_id)
        .order_by(CouncilDissentRecord.created_at.asc())
        .all()
    )
    return [_to_dict(r) for r in rows]
