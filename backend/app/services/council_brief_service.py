"""Project Council, Section 11: Council Brief Generator.

Role-specific briefs, all grounded in the same Council Case -- never a
separate narrative that could drift from what the Council actually found.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import council_orchestration_service
from app.services.council_dissent_service import dissent_for_case
from app.services.council_specialist_assessment_service import latest_assessments_for_case


def _case_or_raise(db: Session, tenant_id: str, council_case_id: int):
    case = council_orchestration_service.get_case(db, tenant_id, council_case_id)
    if case is None:
        raise ValueError(f"Council Case {council_case_id} not found for this tenant")
    return case


def supervisor_brief(db: Session, tenant_id: str, council_case_id: int) -> dict:
    case = _case_or_raise(db, tenant_id, council_case_id)
    dissent = dissent_for_case(db, tenant_id, council_case_id)
    return {
        "council_case_id": council_case_id,
        "brief_type": "supervisor",
        "immediate_issue": case.source_event or case.case_type,
        "evidence": council_orchestration_service.to_dict(case)["evidence_package"],
        "specialist_recommendation": case.recommended_action,
        "dissent": dissent,
        "required_next_action": case.recommended_action or "Await additional evidence before proceeding.",
    }


def manager_brief(db: Session, tenant_id: str, council_case_id: int) -> dict:
    case = _case_or_raise(db, tenant_id, council_case_id)
    assessments = latest_assessments_for_case(db, tenant_id, council_case_id)
    return {
        "council_case_id": council_case_id,
        "brief_type": "manager",
        "operational_impact": next((a["significance"] for a in assessments if a["specialist_key"] in ("maestro", "pulse", "aegis")), ""),
        "staffing_workflow_considerations": next((a["conclusion"] for a in assessments if a["specialist_key"] == "pulse"), ""),
        "quality_implications": next((a["conclusion"] for a in assessments if a["specialist_key"] == "apollo"), ""),
        "recommended_owner": case.required_human_approver,
    }


def executive_brief(db: Session, tenant_id: str, council_case_id: int) -> dict:
    case = _case_or_raise(db, tenant_id, council_case_id)
    assessments = latest_assessments_for_case(db, tenant_id, council_case_id)
    return {
        "council_case_id": council_case_id,
        "brief_type": "executive",
        "enterprise_significance": next((a["significance"] for a in assessments if a["specialist_key"] in ("phoenix", "maestro")), ""),
        "risk": case.risk_level or next((a["conclusion"] for a in assessments if a["specialist_key"] == "sentinelx"), ""),
        "trend": next((a["conclusion"] for a in assessments if a["specialist_key"] == "aegis"), ""),
        "resource_impact": next((a["conclusion"] for a in assessments if a["specialist_key"] == "pulse"), ""),
        "recommended_strategic_action": case.recommended_action,
    }
