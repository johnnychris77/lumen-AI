"""Project Council, Section 19: Reports.

Reuses Veritas's already-generic export helpers
(`veritas_reports_service.build_report_pdf_bytes` / `build_report_csv_bytes`
/ `build_report_xlsx_bytes`) rather than introducing a second PDF/CSV/Excel
implementation -- every report here is just `{title, content}` fed through
that shared renderer.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    council_brief_service,
    council_decision_options_service,
    council_dissent_service,
    council_orchestration_service,
    council_performance_service,
    council_team_registry_service,
)
from app.services.council_outcome_service import outcome_reviews_for_case
from app.services.council_specialist_assessment_service import assessments_for_case
from app.services.veritas_reports_service import build_report_csv_bytes, build_report_pdf_bytes, build_report_xlsx_bytes


def council_decision_report(db: Session, tenant_id: str, council_case_id: int) -> dict:
    case = council_orchestration_service.get_case(db, tenant_id, council_case_id)
    content = council_orchestration_service.to_dict(case) if case else {}
    content["decision_options"] = council_decision_options_service.options_for_case(db, tenant_id, council_case_id)
    return {"title": "Council Decision Report", "content": content}


def specialist_assessment_package(db: Session, tenant_id: str, council_case_id: int) -> dict:
    return {"title": "Specialist Assessment Package", "content": {"assessments": assessments_for_case(db, tenant_id, council_case_id)}}


def dissent_report(db: Session, tenant_id: str, council_case_id: int) -> dict:
    return {"title": "Dissent Report", "content": {"dissent": council_dissent_service.dissent_for_case(db, tenant_id, council_case_id)}}


def decision_options_analysis(db: Session, tenant_id: str, council_case_id: int) -> dict:
    return {"title": "Decision Options Analysis", "content": {"options": council_decision_options_service.options_for_case(db, tenant_id, council_case_id)}}


def leadership_brief_report(db: Session, tenant_id: str, council_case_id: int, brief_type: str) -> dict:
    resolver = {
        "supervisor": council_brief_service.supervisor_brief,
        "manager": council_brief_service.manager_brief,
        "executive": council_brief_service.executive_brief,
    }.get(brief_type)
    if resolver is None:
        raise ValueError(f"Unknown brief_type '{brief_type}'")
    return {"title": f"Leadership Brief ({brief_type.title()})", "content": resolver(db, tenant_id, council_case_id)}


def outcome_effectiveness_report(db: Session, tenant_id: str, council_case_id: int) -> dict:
    return {"title": "Outcome Effectiveness Report", "content": {"outcome_reviews": outcome_reviews_for_case(db, tenant_id, council_case_id)}}


def council_governance_report(db: Session, tenant_id: str) -> dict:
    return {"title": "Council Governance Report", "content": {"teams": council_team_registry_service.list_teams(db, tenant_id)}}


def ai_leadership_performance_report(db: Session, tenant_id: str) -> dict:
    return {"title": "AI Leadership Performance Report", "content": council_performance_service.specialist_performance_summary(db, tenant_id)}


_REPORT_BUILDERS = {
    "decision": council_decision_report,
    "assessments": specialist_assessment_package,
    "dissent": dissent_report,
    "options": decision_options_analysis,
    "outcome": outcome_effectiveness_report,
}


def export_case_report(db: Session, tenant_id: str, council_case_id: int, report_type: str, export_format: str) -> bytes:
    builder = _REPORT_BUILDERS.get(report_type)
    if builder is None:
        raise ValueError(f"Unknown report_type '{report_type}'")
    doc = builder(db, tenant_id, council_case_id)
    return _render(doc, export_format)


def export_governance_report(db: Session, tenant_id: str, export_format: str) -> bytes:
    return _render(council_governance_report(db, tenant_id), export_format)


def export_performance_report(db: Session, tenant_id: str, export_format: str) -> bytes:
    return _render(ai_leadership_performance_report(db, tenant_id), export_format)


def _render(doc: dict, export_format: str) -> bytes:
    if export_format == "pdf":
        return build_report_pdf_bytes(doc["title"], doc["content"])
    if export_format == "csv":
        return build_report_csv_bytes(doc["content"])
    if export_format == "xlsx":
        return build_report_xlsx_bytes(doc["title"], doc["content"])
    raise ValueError(f"Unsupported export format '{export_format}'")
