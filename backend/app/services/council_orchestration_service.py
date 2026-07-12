"""Project Council, Section 1: Council Orchestration Engine.

Selects the appropriate leadership team for an issue, distributes a
shared evidence package, collects independent specialist assessments,
compares conclusions, classifies consensus, records dissent, generates
decision options, and routes the recommendation to the correct human
authority. Everything here composes the other Council services rather
than reimplementing them.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.council_leadership import (
    APPROVAL_TIER_BY_ROLE_NAME,
    APPROVER_SUPERVISOR,
    CASE_STATUS_AWAITING_DECISION,
    CASE_STATUS_AWAITING_EVIDENCE,
    CASE_STATUS_OPEN,
    CASE_STATUS_RESOLVED,
    CASE_TYPE_DEFAULT_TEAM,
    CONSENSUS_INSUFFICIENT_EVIDENCE,
    CONSENSUS_SAFETY_DISSENT,
    CouncilCase,
)
from app.services import (
    council_consensus_service,
    council_decision_options_service,
    council_dissent_service,
    council_specialist_assessment_service,
    council_team_registry_service,
)


def select_specialists_for_case(db: Session, tenant_id: str, case_type: str) -> tuple[str, list[str]]:
    """Section 1: pick the appropriate leadership team + its required
    specialists for a case type."""
    council_team_registry_service.ensure_default_teams(db, tenant_id)
    team_key = CASE_TYPE_DEFAULT_TEAM.get(case_type)
    if team_key is None:
        raise ValueError(f"Unknown Council case type: {case_type}")
    team_config = council_team_registry_service.get_team_config(db, tenant_id, team_key)
    required = json.loads(team_config.required_specialists_json)
    return team_key, required


def open_case(
    db: Session, tenant_id: str, *, case_type: str, source_event: str = "", inspection_ids: list[int] | None = None,
    instrument_ids: list[str] | None = None, digital_twin_refs: list[str] | None = None,
    evidence_package: dict | None = None, risk_level: str = "", urgency: str = "routine",
    requested_decision: str = "", facility_id: str = "",
) -> CouncilCase:
    """Section 3: creates the typed Council Case and assigns its
    leadership team -- agents have not yet assessed anything at this
    point (independence is preserved)."""
    for field_name, value in (
        ("inspection_ids", inspection_ids), ("instrument_ids", instrument_ids), ("digital_twin_refs", digital_twin_refs),
    ):
        if value is not None and not isinstance(value, list):
            raise ValueError(f"{field_name} must be a list if provided, got {type(value).__name__}")
    if evidence_package is not None and not isinstance(evidence_package, dict):
        raise ValueError(f"evidence_package must be an object if provided, got {type(evidence_package).__name__}")

    team_key, required_specialists = select_specialists_for_case(db, tenant_id, case_type)

    row = CouncilCase(
        tenant_id=tenant_id,
        facility_id=facility_id,
        case_type=case_type,
        source_event=source_event,
        inspection_ids_json=json.dumps(inspection_ids or []),
        instrument_ids_json=json.dumps(instrument_ids or []),
        digital_twin_refs_json=json.dumps(digital_twin_refs or []),
        evidence_package_json=json.dumps(evidence_package or {}),
        risk_level=risk_level,
        urgency=urgency,
        requested_decision=requested_decision,
        team_key=team_key,
        participating_specialists_json=json.dumps(required_specialists),
        status=CASE_STATUS_OPEN,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def convene(db: Session, tenant_id: str, council_case_id: int) -> CouncilCase:
    """Runs the full Council cycle for a case: independent assessments,
    consensus classification, dissent recording, and decision-option
    generation. Safe to call more than once while the case is still open
    -- each call runs a fresh round of independent assessments
    (specialists never see each other's prior-round conclusions when
    forming a new one). Once a human decision has resolved the case, it
    can no longer be silently re-convened -- doing so would overwrite an
    already-decided case's status with no new decision on record and no
    audit trail of the reopening."""
    case = db.query(CouncilCase).filter(CouncilCase.tenant_id == tenant_id, CouncilCase.id == council_case_id).first()
    if case is None:
        raise ValueError(f"Council Case {council_case_id} not found for this tenant")
    if case.status == CASE_STATUS_RESOLVED:
        raise ValueError(
            f"Council Case {council_case_id} is already resolved with a recorded human decision; "
            "it cannot be re-convened without an explicit reopen action",
        )

    required_specialists = json.loads(case.participating_specialists_json)
    council_specialist_assessment_service.run_independent_assessments(db, tenant_id, case, required_specialists)
    assessments = council_specialist_assessment_service.latest_assessments_for_case(db, tenant_id, council_case_id)

    consensus_result = council_consensus_service.classify_consensus(assessments, required_specialists)
    council_dissent_service.record_dissent_records(
        db, tenant_id, council_case_id, assessments=assessments, consensus_result=consensus_result,
    )
    council_decision_options_service.generate_decision_options(db, tenant_id, council_case_id, assessments)

    max_tier = max(
        (APPROVAL_TIER_BY_ROLE_NAME.get(a["human_role_required"], 1) for a in assessments), default=1,
    )
    required_approver = next((k for k, v in APPROVAL_TIER_BY_ROLE_NAME.items() if v == max_tier), APPROVER_SUPERVISOR)

    case.consensus_status = consensus_result["status"]
    case.recommended_action = consensus_result["majority_position"] or ""
    case.required_human_approver = required_approver
    case.required_approval_tier = max_tier
    case.status = (
        CASE_STATUS_AWAITING_EVIDENCE
        if consensus_result["status"] in (CONSENSUS_INSUFFICIENT_EVIDENCE, CONSENSUS_SAFETY_DISSENT)
        else CASE_STATUS_AWAITING_DECISION
    )
    db.commit()
    db.refresh(case)
    return case


def to_dict(row: CouncilCase) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "facility_id": row.facility_id,
        "case_type": row.case_type,
        "source_event": row.source_event,
        "inspection_ids": json.loads(row.inspection_ids_json or "[]"),
        "instrument_ids": json.loads(row.instrument_ids_json or "[]"),
        "digital_twin_refs": json.loads(row.digital_twin_refs_json or "[]"),
        "evidence_package": json.loads(row.evidence_package_json or "{}"),
        "risk_level": row.risk_level,
        "urgency": row.urgency,
        "requested_decision": row.requested_decision,
        "team_key": row.team_key,
        "participating_specialists": json.loads(row.participating_specialists_json or "[]"),
        "consensus_status": row.consensus_status,
        "recommended_action": row.recommended_action,
        "required_human_approver": row.required_human_approver,
        "required_approval_tier": row.required_approval_tier,
        "status": row.status,
        "human_review_required": row.human_review_required,
        "agent_version": row.agent_version,
        "disclaimer": row.disclaimer,
    }


def get_case(db: Session, tenant_id: str, council_case_id: int) -> CouncilCase | None:
    return db.query(CouncilCase).filter(CouncilCase.tenant_id == tenant_id, CouncilCase.id == council_case_id).first()


def list_cases(db: Session, tenant_id: str, *, status: str = "", case_type: str = "") -> list[dict]:
    q = db.query(CouncilCase).filter(CouncilCase.tenant_id == tenant_id)
    if status:
        q = q.filter(CouncilCase.status == status)
    if case_type:
        q = q.filter(CouncilCase.case_type == case_type)
    return [to_dict(r) for r in q.order_by(CouncilCase.created_at.desc()).all()]
