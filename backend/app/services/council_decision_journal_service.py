"""Project Council, Section 13: Decision Journal Integration.

Rather than building a second, parallel decision-journal schema, Council
composes a real `MaestroRecommendation` row (Maestro already owns the
leadership decision journal) representing the Council's synthesized
recommendation, then records the human decision through Maestro's own
`maestro_decision_journal_service.record_decision` -- the same leadership
learning dataset Maestro's Leadership Workspace already reads from.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.council_leadership import (
    CASE_CAPA_ESCALATION,
    CASE_EDUCATION_NEED,
    CASE_HIGH_RISK_INSPECTION,
    CASE_REPAIR_RECURRENCE,
    CASE_WORKFLOW_BOTTLENECK,
)
from app.models.maestro_orchestration import (
    RECOMMENDATION_ESCALATE_REPAIR_BACKLOG,
    RECOMMENDATION_GENERATE_CAPA_DRAFT,
    RECOMMENDATION_INSPECTION_PRIORITIES,
    RECOMMENDATION_QUALITY_INITIATIVES,
    RECOMMENDATION_SCHEDULE_COMPETENCY,
    MaestroRecommendation,
)
from app.services import council_dissent_service, council_orchestration_service, maestro_decision_journal_service
from app.services.council_specialist_assessment_service import latest_assessments_for_case

_CASE_TYPE_TO_MAESTRO_RECOMMENDATION_TYPE = {
    CASE_HIGH_RISK_INSPECTION: RECOMMENDATION_INSPECTION_PRIORITIES,
    CASE_WORKFLOW_BOTTLENECK: RECOMMENDATION_INSPECTION_PRIORITIES,
    CASE_EDUCATION_NEED: RECOMMENDATION_SCHEDULE_COMPETENCY,
    CASE_REPAIR_RECURRENCE: RECOMMENDATION_ESCALATE_REPAIR_BACKLOG,
    CASE_CAPA_ESCALATION: RECOMMENDATION_GENERATE_CAPA_DRAFT,
}


def _ensure_maestro_recommendation(db: Session, tenant_id: str, council_case_id: int) -> MaestroRecommendation:
    case = council_orchestration_service.get_case(db, tenant_id, council_case_id)
    if case is None:
        raise ValueError(f"Council Case {council_case_id} not found for this tenant")
    assessments = latest_assessments_for_case(db, tenant_id, council_case_id)
    dissent = council_dissent_service.dissent_for_case(db, tenant_id, council_case_id)

    row = MaestroRecommendation(
        tenant_id=tenant_id,
        recommendation_type=_CASE_TYPE_TO_MAESTRO_RECOMMENDATION_TYPE.get(case.case_type, RECOMMENDATION_QUALITY_INITIATIVES),
        subject=f"Council Case #{council_case_id}: {case.recommended_action or case.case_type}"[:300],
        rationale=(
            f"{case.consensus_status}. Participating specialists: {', '.join(json.loads(case.participating_specialists_json))}. "
            f"Dissent: {'; '.join(d['dissenting_specialist'] for d in dissent) or 'none'}."
        ),
        confidence="high" if case.consensus_status == "UNANIMOUS" else "moderate",
        specialists_consulted_json=json.dumps([a["specialist_key"] for a in assessments]),
        evidence_json=json.dumps({"council_case_id": council_case_id, "consensus_status": case.consensus_status}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def record_council_decision(
    db: Session, tenant_id: str, council_case_id: int, *, leader_decision: str, decided_by: str,
    decided_role: str = "", outcome: str = "", lessons_learned: str = "", new_status: str | None = None,
) -> dict:
    """Section 13: writes one Decision Journal entry that ties the
    Council Case, its specialist agreement/dissent, the human decision,
    and lessons learned into Maestro's existing leadership learning
    dataset."""
    if not leader_decision.strip():
        # Checked here, before _ensure_maestro_recommendation commits its
        # row, rather than relying solely on maestro_decision_journal_
        # service.record_decision's own check -- that check fires after
        # the MaestroRecommendation row is already committed, which would
        # otherwise leave a permanent orphan recommendation behind on
        # every rejected/empty submission.
        raise ValueError("leader_decision is required for an auditable journal entry")

    recommendation = _ensure_maestro_recommendation(db, tenant_id, council_case_id)
    entry = maestro_decision_journal_service.record_decision(
        db, tenant_id, recommendation.id, leader_decision=leader_decision, decided_by=decided_by,
        decided_role=decided_role, outcome=outcome, lessons_learned=lessons_learned, new_status=new_status,
    )
    result = maestro_decision_journal_service.to_dict(entry)
    result["council_case_id"] = council_case_id
    result["maestro_recommendation_id"] = recommendation.id
    return result
